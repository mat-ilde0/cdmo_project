# trying a different approach to the MIP model, the one that uses p=(i,j)

import os
import pandas as pd
from amplpy import AMPL

license_path = os.getenv("AMPL_LICENSE_FILE")
if license_path is not None:
    ampl = AMPL()
    ampl.set_option("license", license_path)
else:
    print("AMPL_LICENSE_FILE not set!")
    ampl = AMPL()

ampl.eval("""
    param N := 8;

    set TEAMS = 1..N;
    set WEEKS = 1..N-1;
    set PERIODS = 1..N/2;
    set ROLES = 1..2;   # roles: 1 = home, 2 = away
          
    var x {p in PERIODS, w in WEEKS, r in ROLES} integer >= 0, <= N; # the team n playing in period p, week w, role r
    param game_value {i in TEAMS, j in TEAMS} := (i-1) * card(TEAMS) + j;
""")

print(ampl.get_parameter("game_value").get_values().to_list())

# CONSTR 1: every team plays every other team exactly once
# ampl.eval("""
#     subject to PlayOnlyOnce {i in TEAMS, j in TEAMS: i < j}:
#         sum {p in PERIODS, w in WEEKS} ((x[p, w, 1] == i and x[p, w, 2] = j) or (x[p, w, 1] = j and x[p, w, 2] = i)) = 1;
# """)

# CONSTR 1: every team plays every other team exactly once
ampl.eval("""
    subject to PlayOnlyOnceij {i in TEAMS, j in TEAMS: i<j}:
        sum {p in PERIODS, w in WEEKS} game_value[x[p, w, 1], x[p, w, 2]] = game_value[i, j];
""")

ampl.eval("""
    subject to PlayOnlyOnceji {i in TEAMS, j in TEAMS: i<j}:
        sum {p in PERIODS, w in WEEKS} game_value[x[p, w, 1], x[p, w, 2]] = game_value[j, i];
""")

# CONSTR 2: every team plays once a week
ampl.eval("""
    subject to OneGamePerWeek {i in TEAMS, w in WEEKS}:
        sum {p in PERIODS, r in ROLES} (x[p, w, r] = i) = 1;
""")

# CONSTR 3: every team plays at most twice per period
ampl.eval("""
    subject to TwoGamesPerPeriod {i in TEAMS, p in PERIODS}:
        sum {w in WEEKS, r in ROLES} (x[p, w, r] = i) <= 2;
""")

# CONSTR 4: in every period there is at most one match
# ampl.eval("""
#     subject to OneMatchPerPeriodWeek {p in PERIODS, w in WEEKS}:
#         sum {r in ROLES} (x[p, w, r]) <= 1;
# """)


ampl.option["solver"] = "highs"
ampl.option['mp_options'] = 'lim:time=300'
ampl.option["presolve"] = 100
ampl.option["show_stats"] = 1
ampl.option["times"] = 1

print("\nSOLVING...")
output = ampl.solve(verbose=False, return_output=True)
print("AMPL solve output:", output)

solver_time = ampl.get_value("_solve_elapsed_time")
print(f"Solver time: {solver_time:.3f} seconds")

print("\nAMPL solve result:", ampl.get_solution(flat=False, zeros=False))



