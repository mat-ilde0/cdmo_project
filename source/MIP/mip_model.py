import json
import os
import pandas as pd
import re
from amplpy import AMPL, modules
import argparse
from math import floor
from dotenv import load_dotenv
load_dotenv()

# execute from the root folder by running: python source/MIP/mip_model.py <N> <solver>
# run with: python source/MIP/mip_model.py -h to see help

uuid = os.getenv("AMPL_LICENSE_UUID")
if uuid:
    ampl = AMPL()

available_solvers = modules.installed()[1:]  # Skip the first element which is 'ampl'

# loading instance data from the parameter passed
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
    return help_text[:-2]  # Remove the last comma and space

parser.add_argument('N', type=check_N_range, help="N")
parser.add_argument('solver', type=check_solver_range, help=get_solvers_help())

args = parser.parse_args()

ampl.eval(f"param N := {args.N};")

# LOADING THE MODEL
ampl.eval("""
    set TEAMS = 1..N;
    set WEEKS = 1..N-1;
    set PERIODS = 1..N/2;

    var x {i in TEAMS, j in TEAMS, p in PERIODS, w in WEEKS} binary >= 0, <= 1;
    var home_games {i in TEAMS} integer >= 0, <= card(TEAMS);
    var away_games {i in TEAMS} integer >= 0, <= card(TEAMS);
    
    # Variables to capture absolute difference
    var home_away_diff {i in TEAMS} >= 0;

    minimize TotalImbalance: sum {i in TEAMS} home_away_diff[i];
          
    param game_value {i in TEAMS, j in TEAMS} := (i-1) * card(TEAMS) + j;
""")

# Constraints to define the absolute difference
ampl.eval("""
    subject to HomeGames {i in TEAMS}:
        home_games[i] = sum {j in TEAMS, p in PERIODS, w in WEEKS} x[i,j,p,w];
        
    subject to AwayGames {i in TEAMS}:
        away_games[i] = sum {j in TEAMS, p in PERIODS, w in WEEKS} x[j,i,p,w];
          
    subject to HomeAwayDiff1 {i in TEAMS}:
        home_away_diff[i] >= home_games[i] - away_games[i];

    subject to HomeAwayDiff2 {i in TEAMS}:
        home_away_diff[i] >= away_games[i] - home_games[i];
""")

#print(ampl.get_parameter("game_value").get_values().to_list())

# ampl.eval("""
# subject to NoTeamPlaysItself {i in TEAMS, p in PERIODS, w in WEEKS}:
#     x[i,i,p,w] = 0;
# """)

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

# CONSTR 4: in every period there is at the most one match
ampl.eval("""
subject to OneMatchPerPeriodWeek {p in PERIODS, w in WEEKS}:
    sum {i in TEAMS, j in TEAMS: i != j} x[i,j,p,w] = 1;
""")

# CONSTR 5 (symmetry breaking): lexicographical week ordering
# ampl.eval("""
# subject to LexicographicalWeekOrdering {w in WEEKS: w < card(WEEKS)}:
#     sum {p in PERIODS, i in TEAMS, j in TEAMS: i!=j} (game_value[i,j] * x[i,j,p,w]) <=
#     sum {p in PERIODS, i in TEAMS, j in TEAMS: i!=j} (game_value[i,j] * x[i,j,p,w+1]);
# """)

# ampl.eval("""
# subject to LexicographicalPeriodOrdering {p in PERIODS: p < card(PERIODS)}:
#     sum {w in WEEKS, i in TEAMS, j in TEAMS: i!=j} (game_value[i,j] * x[i,j,p,w]) <=
#     sum {w in WEEKS, i in TEAMS, j in TEAMS: i!=j} (game_value[i,j] * x[i,j,p+1,w]);
# """)
time_limit = 10
solver = available_solvers[args.solver]
mp_options_str = f'lim:time={time_limit} report_times=1 tech:timing=2'# outlev=1' 
if solver != 'cbc': mp_options_str += 'tech:threads=1'
print(mp_options_str)

# SETTING OPTIONS
ampl.option["solver"] = solver
ampl.option['mp_options'] = mp_options_str
ampl.option["presolve"] = 90
#ampl.option["show_stats"] = 1

instance = ampl.get_parameter("N").getValues().to_list()[0]
print("\nSOLVING Instance N = {} using {}".format(instance, solver))
output = ampl.solve(verbose=True, return_output=True)
print("AMPL solve output:", output)

# solver_time = ampl.get_value('_total_solve_time')
# print(f"Solver time: {solver_time:.3f} seconds")

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

def create_solution_json(sol_matrix, output):
    optimal = ampl.solve_result == "solved"
    obj = ampl.get_objective('TotalImbalance')
    time = floor(parse_timing_from_output(output)['Total time']) if optimal else 300
    
    solution_result = {
        solver: {
            "sol": sol_matrix if sol_matrix is not None else {},
            "time": time, # total time (presolving + solving),
            "optimal": optimal, # a Boolean true iff the instance is solved for the decision version, or solved to optimality for the optimization version,
            "obj": obj.value() # objective function value
        }
    }

    print('RESULT:', solution_result)
    return solution_result

sol_matrix = {}
if ampl.solve_result == "solved":
    sol_matrix = get_solution_matrix()

# sol = ampl.get_solution(flat=False, zeros=False)
# print(f"AMPL solve result: \n\n x: {sol['x']} \n\nhome_games:  {sol['home_games']} \n\n away_games: {sol['away_games']} \n\n home_away_diff: {sol['home_away_diff']}")

filename = f"res/MIP/{instance}.json"
data = {}
if os.path.exists(filename):
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except Exception:
        pass  

# Update and write
data.update(create_solution_json(sol_matrix, output))
with open(filename, 'w') as f:
    json.dump(data, f, indent=4)
print(f"JSON file '{filename}' updated successfully.")