import json
import os
import re
from amplpy import AMPL, modules
import argparse
from math import floor
from itertools import product
from dotenv import load_dotenv
load_dotenv()

uuid = os.getenv("AMPL_LICENSE_UUID")
if uuid:
    modules.activate(uuid)
    ampl = AMPL()

# ----------------------------------------------------------------------------
# Getting user parameters
# ----------------------------------------------------------------------------
available_solvers = modules.installed()[1:]  # Skip the first element which is 'ampl'
automatic = False

parser = argparse.ArgumentParser(description="Script to read two parameters")

def check_N_range(value):
    ivalue = int(value)
    if ivalue < 0:
        raise argparse.ArgumentTypeError(f"{value} is < 0")
    return ivalue

def check_solver_range(value):
    ivalue = int(value)
    if ivalue < 0 or ivalue > len(available_solvers) - 1:
        raise argparse.ArgumentTypeError(f"{value} is not in range 0–{len(modules.installed()) - 2}")
    return ivalue

def get_solvers_help():
    help_text = ""
    for i, solver in enumerate(available_solvers):  # Skip the first element which is 'ampl'  
        help_text += f"{i}: {solver}, "
    return help_text[:-2] 

parser.add_argument('N', type=check_N_range, nargs="?", help="N")
parser.add_argument('solver', type=check_solver_range, nargs="?", help=get_solvers_help())
parser.add_argument('-a', '--automatic', action='store_true', help="Run all N and solver combinations automatically")
parser.add_argument("-o", "--optimise", action="store_true", help="Turn on optimisation mode")
parser.add_argument('-cp', '--can-pair',action='store_true',help="Enable canonical pairing")
parser.add_argument('-sb', '--symm_break',action='store_true',help="Enable symmetry breaking on the weeks")
parser.add_argument('-cplex_br', '--cplex_barr',action='store_true',help="Use barrier algorithm for cplex")

args = parser.parse_args()

optimise = args.optimise # true if the -o/--optimise flag is passed
can_pair = args.can_pair
symm_break = args.symm_break
cplex_barr = args.cplex_barr

all_combinations = []
if args.automatic:
    # user typed:  python mip_model.py -a
    if args.N is not None or args.solver is not None:
        parser.error("-a/--automatic cannot be combined with N or solver.")
    automatic = True
else:
    # user typed:  python mip_model.py N solver
    if args.N is None or args.solver is None:
        parser.error("Positional arguments N and solver are required unless -a/--automatic is used.")
    automatic = False



# ----------------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------------
def get_solution_matrix():
    solution_dict = ampl.get_solution(flat=False, zeros=False)
    weeks = len(ampl.get_set("WEEKS").get_values().to_list())
    periods = len(ampl.get_set("PERIODS").get_values().to_list())
    sol_matrix = [[[] for _ in range(weeks)] for _ in range(periods)]

    # Populate matrix from x dict
    for (i, j, p, w), val in solution_dict["x"].items():
        if val > 0.5:  # assuming binary, with float rounding
            sol_matrix[p - 1][w - 1] = [i, j]
    return sol_matrix

def print_solution(sol_matrix):
    for row in sol_matrix:
        print(row)

def parse_timing_from_output(output):
    timing_data = {}
    
    timing_patterns = {
        'Setup time': r'Setup time = ([\d.]+)s',
        'Solver time': r'Solver time = ([\d.]+)s', 
        'Output time': r'Output time = ([\d.]+)s',
        'Total time': r'Total time = ([\d.]+)s'
    }
    
    for key, pattern in timing_patterns.items():
        match = re.search(pattern, output)
        if match:
            timing_data[key] = float(match.group(1))
    
    return timing_data

def get_sol_suffix(comb: dict, solver):
    suffix = ""
    
    if comb['can_pair']:
        suffix += "_canPair"
    if comb['symm_break']:
        suffix += "_symmBreak"
    if solver == 'cplex' and comb['cplex_barr']:
        suffix += "_barrier"
    if comb['optimise']:
        suffix += "_OPT"
    if not comb['optimise']:
        suffix += "_DEC"
    
    return suffix


def create_solution_json(solver, sol_matrix, output, solve_result, comb):
    optimal = solve_result in ("solved", "infeasible")
    obj = 'None'
    if comb['optimise']:
        obj = ampl.get_objective('TotalImbalance').value() if solve_result not in ("limit", "infeasible", "?") else 'None'
    time = 0
    if solve_result in ("solved", "solved?", "infeasible"):
        time = floor(parse_timing_from_output(output)['Total time'])
    elif solve_result in ("limit", "?"):
        time = 300
    print("time= ", time)

    approach = get_sol_suffix(comb, solver)
    key_name = solver +  approach
    
    solution_result = {
        key_name: {
            "sol": sol_matrix,
            "time": time, # total time (presolving + solving),
            "optimal": optimal, # a Boolean true iff the instance is solved for the decision version, or solved to optimality for the optimization version,
            "obj": obj # objective function value
        }
    }

    #print('RESULT:', solution_result)
    return solution_result


# ----------------------------------------------------------------------------
# The model
# ----------------------------------------------------------------------------
def load_model(N:int, optimise: bool, symm_break: bool, can_pair: bool):
    ampl.eval(f"param N := {N};")
    ampl.eval("""
        set TEAMS = 1..N;
        set WEEKS = 1..N-1;
        set PERIODS = 1..N/2;

        var x {i in TEAMS, j in TEAMS, p in PERIODS, w in WEEKS: i != j} binary;
    """)

    if optimise: 
        ampl.eval("""
            var home_games {i in TEAMS} integer >= 0, <= card(TEAMS);
            var away_games {i in TEAMS} integer >= 0, <= card(TEAMS);
            
            # Variables to capture absolute difference
            var home_away_diff {i in TEAMS} >= 0;
        """)

        ampl.eval("""
            minimize TotalImbalance: sum {i in TEAMS} home_away_diff[i];
        """)

        # Constraints to define the absolute difference
        ampl.eval("""
            subject to HomeGames {i in TEAMS}:
                home_games[i] = sum {j in TEAMS, p in PERIODS, w in WEEKS: i != j} x[i,j,p,w];
                
            subject to AwayGames {i in TEAMS}:
                away_games[i] = sum {j in TEAMS, p in PERIODS, w in WEEKS: i != j} x[j,i,p,w];
                
            subject to HomeAwayDiff1 {i in TEAMS}:
                home_away_diff[i] >= home_games[i] - away_games[i];

            subject to HomeAwayDiff2 {i in TEAMS}:
                home_away_diff[i] >= away_games[i] - home_games[i];
        """)

    if symm_break:
        ampl.eval("""
            param game_value {i in TEAMS, j in TEAMS: i != j} := (i-1) * card(TEAMS) + j;
                  
            subject to LexicographicalWeekOrdering {w in WEEKS: w < card(WEEKS)}:
                sum {p in PERIODS, i in TEAMS, j in TEAMS: i!=j} (game_value[i,j] * x[i,j,p,w]) <=
                sum {p in PERIODS, i in TEAMS, j in TEAMS: i!=j} (game_value[i,j] * x[i,j,p,w+1]);
        """)

    # CONSTR 1: every team plays every other team exactly once
    ampl.eval("""
        subject to PlayOnlyOnce {i in TEAMS, j in TEAMS: i < j}:
            sum {w in WEEKS, p in PERIODS} (x[i,j,p,w] + x[j,i,p,w]) = 1;
    """)

    # CONSTR 2: every team plays exactly one game per week
    ampl.eval("""
        subject to OneGamePerWeek {i in TEAMS, w in WEEKS}:
            sum {j in TEAMS: i != j} sum {p in PERIODS} (x[i,j,p,w] + x[j,i,p,w]) = 1;
    """)

    # CONSTR 3: every team plays at most twice per period
    ampl.eval("""

    subject to TwoGamesPerPeriod {i in TEAMS, p in PERIODS}:
        sum {j in TEAMS: i != j} sum {w in WEEKS} (x[i,j,p,w] + x[j,i,p,w]) <= 2;
    """)

    # CONSTR 4: in every slot there is at the most one match
    ampl.eval("""
    subject to OneMatchPerSlot {p in PERIODS, w in WEEKS}:
        sum {i in TEAMS, j in TEAMS: i != j} x[i,j,p,w] = 1;
    """)

    if can_pair:
        # CONSTR: canonical pairing
        ampl.eval("""
        subject to CanonicalPairing {p in PERIODS}:
            x[p, N + 1 - p, p, 1] = 1;
        """)

# ----------------------------------------------------------------------------
# Solver set up 
# ----------------------------------------------------------------------------
time_limit = 300
opt_names = {
    'gurobi':'gurobi_options',
    'cplex': 'cplex_options',
    'highs': 'highs_options'
} 

def solve_instance(N: int, solver_idx: int, combination: dict) -> None:
    ampl.reset()                               # fresh model
    load_model(N, optimise=comb['optimise'], symm_break=comb['symm_break'], can_pair=['can_pair'])

    solver_name = available_solvers[solver_idx]

    mp_options_str = f'lim:time={time_limit} report_times=1 tech:timing=2 tech:threads=1 '
    ampl.option["solver"] = solver_name
    if solver_name == 'cplex' and combination['cplex_barr']: mp_options_str += 'alg:barrier'

    opt_name = opt_names[solver_name]
    ampl.option[opt_name] = mp_options_str

    print('\n' + '-'*90)
    print(f"SOLVING N = {N} with {solver_name + get_sol_suffix(comb, solver_name)}")
    print(f'- Solver\'s options: {ampl.get_option(opt_name)}')

    output = ampl.solve(verbose=True, return_output=True)
    solve_result = ampl.solve_result

    print(f'***{solve_result}***')
    print('-'*90 +'\n')

    # -------- save results exactly as you already do --------
    sol_matrix = {}
    if solve_result in ("solved", "solved?", "limit", "infeasible", "?"):
        if solve_result in ("limit", "infeasible", "?"):
            sol_matrix = []
        else:
            sol_matrix = get_solution_matrix()

        filename = f"res/MIP/{N}.json"
        data = {}
        if os.path.exists(filename):
            try:
                with open(filename) as f:
                    data = json.load(f)
            except Exception:
                pass
        data.update(create_solution_json(solver_name, sol_matrix, output, solve_result, comb))
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)


# ----------------------------------------------------------------------------
# Solving
# ----------------------------------------------------------------------------
if automatic:
    instances = range(4, 15, 2)               # 4,6,…,14
    for N in instances:
        for idx in range(len(available_solvers)):
            flags = ["optimise", "can_pair", "symm_break"]
            if available_solvers[idx] == 'cplex':
                flags.append('cplex_barr')
    
            all_combinations = []
            for values in product([False, True], repeat=len(flags)):
                combo = dict(zip(flags, values))
                all_combinations.append(combo)
            print(all_combinations)

            for comb in all_combinations:
                solve_instance(N, idx, comb)
else:
    comb = {
        'optimise': optimise,
        'can_pair': can_pair,
        'symm_break': symm_break,
        'cplex_barr': cplex_barr
    }
    solve_instance(args.N, args.solver, comb)
