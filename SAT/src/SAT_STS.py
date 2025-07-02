from z3 import *
import itertools
from constraints import * 
# Let's start by defining the parameters

n = 4
weeks = n - 1
periods = n//2

# Initializing Z3 Solver

solver = Solver()

# Boolean Variables

match_vars = {} # match_vars[i][j][w][p] = True if the team i plays against team j in week w period p

for i in range(n):
    for j in range(n):
        if i == j:
            continue
        for w in range(weeks):
            for p in range(periods):
                var_name = f"match_{i}_{j}_w{w}_p{p}"
                match_vars[(i, j, w, p)] = Bool(var_name)

sample_var = match_vars[(0, 1, 0, 0)]
print(f"Sample variable: {sample_var}")

# Solving

for i in range(n):
    for j in range(i + 1, n):
        vars_for_pair = [match_vars[(i, j, w, p)] for w in range(weeks) for p in range(periods)]
        exactly_one(solver, vars_for_pair)  # add the constraint here

# Constraint 2: At most one match per slot
add_at_most_one_match_per_slot(solver, match_vars, n, weeks, periods)

# Constraint 3: Each team plays at most once per week
add_team_once_per_week(solver, match_vars, n, weeks, periods)

result = solver.check()

# Solve the problem
if result == sat:
    model = solver.model()
    print("SOLUTION FOUND:\n")
    for key, var in match_vars.items():
        if is_true(model.evaluate(var)):
            i, j, w, p = key
            print(f"Week {w}, Period {p}: Team {i} vs Team {j}")
else:
    print("No solution found.")
