import os
import pandas as pd
from amplpy import AMPL

print("Running AMPL test...")

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
print("Loading base model...")
ampl.eval("""
    param N := 8;

    set TEAMS = 1..N;
    set WEEKS = 1..N-1;
    set PERIODS = 1..N/2;

    var x {i in TEAMS, j in TEAMS, p in PERIODS, w in WEEKS} binary;
""")

# CONSTR 1: every team plays every other team exactly once
print("Loading constr 1...")
ampl.eval("""
    subject to PlayOnlyOnce {i in TEAMS, j in TEAMS: i < j}:
        sum {w in WEEKS, p in PERIODS} (x[i,j,p,w] + x[j,i,p,w]) = 1;
""")

# CONSTR 2: every team plays exactly one game per week
print("Loading constr 2...")
ampl.eval("""

    subject to OneGamePerWeek {i in TEAMS, w in WEEKS}:
        sum {j in TEAMS: i != j} sum {p in PERIODS} (x[i,j,p,w] + x[j,i,p,w]) = 1;
""")

# CONSTR 3: every team plays at most twice per period
print("Loading constr 3...")
ampl.eval("""

subject to TwoGamesPerPeriod {i in TEAMS, p in PERIODS}:
    sum {j in TEAMS: i != j} sum {w in WEEKS} (x[i,j,p,w] + x[j,i,p,w]) <= 2;
""")

# CONSTR 4: in every period there is at the most one match
ampl.eval("""
subject to OneMatchPerPeriodWeek {p in PERIODS, w in WEEKS}:
    sum {i in TEAMS, j in TEAMS: i != j} x[i,j,p,w] = 1;
""")

# setting options
ampl.option["solver"] = "highs"
ampl.option['mp_options'] = 'lim:time=300'


print("\nSOLVING...")
ampl.solve(verbose=True, return_output=True)

solver_time = ampl.get_value("_solve_elapsed_time")
print(f"Solver time: {solver_time:.3f} seconds")

print("AMPL solve result:", ampl.get_solution(flat=False, zeros=False))
assert ampl.solve_result == "solved"

