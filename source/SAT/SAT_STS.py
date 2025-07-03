import sys
import os
import time
import json
from constraints import *
from z3 import *

def get_parameters(n):
    if n % 2 != 0:
        raise ValueError("n must be even")
    return n, n - 1, n // 2

def build_variables(n, weeks, periods):
    M = {}
    for i in range(n):
        for j in range(i + 1, n):
            for w in range(weeks):
                for p in range(periods):
                    M[(i, j, w, p)] = Bool(f"m_{i}_{j}_w{w}_p{p}")
    return M

def extract_solution(model, M, weeks, periods):
    sol = [[None for _ in range(weeks)] for _ in range(periods)]
    for (i, j, w, p), var in M.items():
        if is_true(model.evaluate(var)):
            sol[p][w] = [i + 1, j + 1]  
    return sol

def save_solution(sol, n, runtime_ms):
    out_dir = "../../res/SAT"
    os.makedirs(out_dir, exist_ok=True)
    data = {
        "SAT": {
            "time": runtime_ms,
            "optimal": True,
            "obj": None,
            "sol": sol
        }
    }
    path = os.path.join(out_dir, f"n{n}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✔ Solution saved to {path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python sat_sts.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])
    print(f"Solving STS for n = {n} teams…")
    n, weeks, periods = get_parameters(n)

    # build variables
    match_vars = build_variables(n, weeks, periods)

    # setup solver and also the timeout
    solver = Solver()
    solver.set(timeout=300000, random_seed=42)
    solver.set("phase_selection", 0)
    solver.set("restart_strategy", 1)
    solver.set("restart_factor", 1.5)
    solver.set("case_split", 1)
    
    # add constraints
    # Each team plays exactly once per week (not just "at most")

    constraint_each_pair_once   (solver, match_vars, n, weeks, periods)
    constraint_one_match_per_slot(solver, match_vars, n, weeks, periods)
    constraint_team_once_per_week(solver, match_vars, n, weeks, periods)
    at_most_two_per_period_optimized(solver, match_vars, n, weeks, periods)
    
    add_simple_symmetry(solver, match_vars)
    add_implied_constraints(solver, match_vars, n, weeks, periods)
    # solve
    t0 = time.time()
    res = solver.check()
    elapsed_sec = time.time() - t0
    # handle result
    if res == sat:
        model = solver.model()
        sol = extract_solution(model, match_vars, weeks, periods)
        runtime_sec = int(elapsed_sec)
        print(f"SAT in {elapsed_sec:.2f}s")
        save_solution(sol, n, runtime_sec)
    elif res == unknown:
        runtime_sec = 300
        print(f"TIMEOUT after {elapsed_sec:.2f}s")
    else:
        print(f"Unsatisfiable after {elapsed_sec:.2f}s")

if __name__ == "__main__":
    main()
