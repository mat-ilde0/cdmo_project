import os, time, json, argparse, resource
from z3 import *
from constraints import * 
import gc
# ----------------------------------------------------------------------------
# Parameters and Variable Setup
# ----------------------------------------------------------------------------
def get_parameters(n):
    if n % 2:
        raise ValueError("N must be even")
    return n, n - 1, n // 2  # n teams, W weeks, P periods

def build_variables(n, W, P):
    return {
        (i, j, w, p): Bool(f"m_{i}_{j}_w{w}_p{p}")
        for i in range(n)
        for j in range(i + 1, n)
        for w in range(W)
        for p in range(P)
    }

# ----------------------------------------------------------------------------
# Extracting, Printing and Saving Solutions
# ----------------------------------------------------------------------------
def extract_solution(model, M, W, P):
    sol = [[None for _ in range(W)] for _ in range(P)]
    for (i, j, w, p), var in M.items():
        if is_true(model.evaluate(var)):
            sol[p][w] = [i + 1, j + 1]  # 1-based indexing
    return sol

def print_solution(sol_matrix):
    print("\n[Solution Matrix]")
    for row in sol_matrix:
        print(row)

def save_solution_json(n, status, runtime_s, sol):
    if status == 'sat':
        time_val, optimal = runtime_s, True
    elif status == 'unsat':
        time_val, optimal = runtime_s, True
    else:
        time_val, optimal = 300, False  # timeout

    entry = {
        "time": time_val,
        "optimal": optimal,
        "obj": None,
        "sol": sol
    }

    out_dir = "../../res/SMT"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"n{n}.json")

    data = {}
    if os.path.isfile(path):
        with open(path) as f:
            data = json.load(f)

    data["SMT_dec"] = entry
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✔ SMT_dec written to {path}")

# ----------------------------------------------------------------------------
# Timing Helper
# ----------------------------------------------------------------------------
def get_time_info(start_time):
    end_time = time.time()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "Total time": round(end_time - start_time, 3),
        "User CPU": round(usage.ru_utime, 3),
        "System CPU": round(usage.ru_stime, 3)
    }

# ----------------------------------------------------------------------------
# Core Solving Routine
# ----------------------------------------------------------------------------

def solve_instance(n):
    n, W, P = get_parameters(n)
    print(f"\n{'-'*80}\n[INFO] Solving STS-SMT for N = {n} teams\n{'-'*80}")

    M = build_variables(n, W, P)
    s = Solver()
    s.set(timeout=300_000, random_seed=42)

    # Constraints (PB-AMO, fair + symmetry)
    constraint_each_pair_once_smt        (s, M, n, W, P)
    constraint_one_match_per_slot_smt    (s, M, n, W, P)
    constraint_team_once_per_week_smt    (s, M, n, W, P)
    constraint_at_most_two_per_period_smt(s, M, n, W, P)
    simple_rowcol_lex                    (s, M, n, W, P)

    # Solve
    t0 = time.time()
    res = s.check()
    timing = get_time_info(t0)
    elapsed = int(timing["Total time"])

    print("[Timing]")
    for k, v in timing.items():
        print(f"{k}: {v}s")

    if res == sat:
        sol = extract_solution(s.model(), M, W, P)
        print_solution(sol)
        save_solution_json(n, 'sat', elapsed, sol)
    elif res == unsat:
        print(f"[RESULT] UNSAT in {elapsed}s")
        save_solution_json(n, 'unsat', elapsed, [])
    else:
        print(f"[RESULT] TIMEOUT after {elapsed}s")
        save_solution_json(n, 'timeout', elapsed, [])

    # Clean up memory
    del M, s
    gc.collect()


# ----------------------------------------------------------------------------
# CLI Argument Parsing
# ----------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="SMT (Z3) decision solver for the Sports Timetable Scheduling (STS) problem"
)
parser.add_argument('N', type=int, nargs='?',
                    help='even number of teams (single instance)')
parser.add_argument('-a', '--automatic', action='store_true',
                    help='solve N = 4,6,...,14 in batch')
parser.add_argument('-o', '--optimise', action='store_true',
                    help='[ignored] optimization handled by MIP script')
args = parser.parse_args()

if args.optimise:
    print('[INFO] -o/--optimise ignored: SMT model is decision-only.')

# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
if args.automatic:
    for n in range(4, 15, 2):
        solve_instance(n)
else:
    if args.N is None:
        parser.error("Positional N required unless -a is used.")
    solve_instance(args.N)
