import json
import os
import pandas as pd
from amplpy import AMPL

license_path = os.getenv("AMPL_LICENSE_FILE")
if license_path is not None:
    ampl = AMPL()
    ampl.set_option("license", license_path)
    print("LICENSE: " + ampl.get_option("license"))
else:
    print("AMPL_LICENSE_FILE not set!")
    ampl = AMPL()

# loading instance data
# ampl.read_data("params.dat")   # reads the value of N, the only instance parameter

# loading the base model using AMPL.eval()
# print("Loading base model...")
ampl.eval("""
    param N := 6;

    set TEAMS = 1..N;
    set WEEKS = 1..N-1;
    set PERIODS = 1..N/2;

    var x {i in TEAMS, j in TEAMS, p in PERIODS, w in WEEKS} binary >= 0, <= 1;
    var home_games {i in TEAMS} integer >= 0, <= card(TEAMS);
    var away_games {i in TEAMS} integer >= 0, <= card(TEAMS);
    
    # Variables to capture absolute difference
    var home_away_diff {i in TEAMS} >= 0;

    #minimize TotalImbalance: sum {i in TEAMS} home_away_diff[i];
          
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

ampl.eval("""
subject to NoTeamPlaysItself {i in TEAMS, p in PERIODS, w in WEEKS}:
    x[i,i,p,w] = 0;
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


# setting options
ampl.option["solver"] = "gurobi"
ampl.option['mp_options'] = 'lim:time=300 report_times=1 outlev=1'# outlev=1'
ampl.option["presolve"] = 1
ampl.option["show_stats"] = 1
#ampl.option["times"] = 1

# ampl.eval("""
# ampl: display time_solver;  
#           """)


instance = ampl.get_parameter("N").getValues().to_list()[0]
print("\nSOLVING Instance N =", instance)
output = ampl.solve(verbose=True, return_output=True)
print("AMPL solve output:", output)

solver_time = ampl.get_value("_solve_elapsed_time")
print(f"Solver time: {solver_time:.3f} seconds")

# preprocessing_time = ampl.getValue('time_conversion')
# print(f"Preprocessing time: {preprocessing_time}")


def get_solution():
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

def create_solution_json(sol_matrix):
    solution_result = {
        "gurobi": {
            "sol": sol_matrix,
            # "time": # total time (presolving + solving),
            # "optimal": a Boolean true iff the instance is solved for the decision version, or solved to optimality for the optimization version,
            # "obj": objective function value
        }
    }
    return solution_result

if ampl.solve_result == "solved":
    sol = ampl.get_solution(flat=False, zeros=False)
    #print(f"AMPL solve result: \n\n x: {sol['x']} \n\nhome_games:  {sol['home_games']} \n\n away_games: {sol['away_games']} \n\n home_away_diff: {sol['home_away_diff']}")
    #print(sol["x"])

    print("\nSOLUTION:\n")
    print_solution(get_solution())

    filename = f"res/MIP/{instance}.json"
    try:
        # Open the file in write mode ('w')
        # Using 'indent=4' makes the JSON output human-readable with 4 space indentation
        with open(filename, 'w') as json_file:
            json.dump(create_solution_json(get_solution()), json_file, indent=4)
        print(f"JSON file '{filename}' created successfully.")
    except IOError as e:
        print(f"Error writing to file {filename}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")