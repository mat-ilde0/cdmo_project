import os, time, json, argparse, resource, gc, random
from z3 import *
from constraints import *

# ----------------------------------------------------------------------------
# Parameters & variables
# ----------------------------------------------------------------------------
def get_parameters(n: int):
    if n % 2:
        raise ValueError("N must be even")
    return n, n - 1, n // 2       # teams, weeks, periods

def build_variables(n, W, P):
    return {(i, j, w, p): Bool(f"m_{i}_{j}_w{w}_p{p}")
            for i in range(n) for j in range(i + 1, n)
            for w in range(W) for p in range(P)}

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def extract_solution(model, M, W, P):
    sol = [[None for _ in range(W)] for _ in range(P)]
    for (i, j, w, p), v in M.items():
        if is_true(model.evaluate(v)):
            sol[p][w] = [i + 1, j + 1]
    return sol

def print_solution(sol_matrix):
    print("\n[Solution Matrix]")
    for row in sol_matrix:
        print(row)

def seconds_since(t0):
    return round(time.time() - t0, 3)

# ----------------------------------------------------------------------------
# JSON persistence
# ----------------------------------------------------------------------------
def save_solution_json(n, status, runtime_s, sol, *, optimise=False, obj_val=None):
    time_val = 300 if status == 'timeout' else runtime_s
    optimal = (status in ('sat','unsat'))
    entry = {"time": time_val, "optimal": optimal, "obj": obj_val if optimise else None, "sol": sol}
    out_dir = "../../res/SMT"; os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"n{n}.json")
    data = json.load(open(path)) if os.path.isfile(path) else {}
    key = "SMT_opt" if optimise else "SMT_dec"
    data[key] = entry
    json.dump(data, open(path, 'w'), indent=2)
    print(f"✔ {key} written to {path}")

# ----------------------------------------------------------------------------
# SMT-LIB2 export (check-sat only)
# ----------------------------------------------------------------------------
def export_to_smtlib2(solver, filename: str):
    smt_text = "(set-logic QF_LIA)\n" + solver.to_smt2()
    open(filename, 'w').write(smt_text)
    print(f"✔ SMT-LIB2 written to {filename}")

# ----------------------------------------------------------------------------
# Core solving routine
# ----------------------------------------------------------------------------
def solve_instance(n: int, args, *, optimise: bool = False):
    n, W, P = get_parameters(n)
    print(f"\n{'-'*80}\n[INFO] Solving STS-SMT | N = {n} | optimise = {optimise}\n{'-'*80}")
    M = build_variables(n, W, P)
    s = Solver(); s.set("timeout",300_000)
    if not optimise:
        seed = 42; s.set("random_seed",seed)
        print(f"[INFO] Decision mode seed = {seed}")
    # core constraints
    constraint_each_pair_once_smt(s,M,n,W,P)
    constraint_one_match_per_slot_smt(s,M,n,W,P)
    constraint_team_once_per_week_smt(s,M,n,W,P)
    constraint_at_most_two_per_period_smt(s,M,n,W,P)
    # symmetry-breaking if enabled
    if not args.no_sb:
        simple_rowcol_lex(s,M,n,W,P)
    # optional objective var
    if optimise:
        total_imbalance = add_total_home_away_imbalance_expr(s,M,n)
        LB = n
    # export smt2
    if args.export_smt2 and not optimise:
        export_to_smtlib2(s,f"n{n}.smt2")
    # decision
    if not optimise:
        t0 = time.time(); res = s.check(); elapsed = seconds_since(t0)
        timing = {"Total time":elapsed,
                  "User CPU":round(resource.getrusage(resource.RUSAGE_SELF).ru_utime,3),
                  "System CPU":round(resource.getrusage(resource.RUSAGE_SELF).ru_stime,3)}
        print("[Timing]"); [print(f"{k}: {v}s") for k,v in timing.items()]
        if res==sat:
            sol=extract_solution(s.model(),M,W,P); print_solution(sol)
            save_solution_json(n,'sat',elapsed,sol)
        elif res==unsat:
            print(f"[RESULT] UNSAT in {elapsed}s")
            save_solution_json(n,'unsat',elapsed,[])
        else:
            print(f"[RESULT] TIMEOUT after {elapsed}s")
            save_solution_json(n,'timeout',elapsed,[])
        return
    # optimisation
    print("[INFO] Phase 1: find any feasible schedule…")
    s.set("timeout",120_000 if n>=8 else 60_000)
    t0 = time.time(); res1 = s.check(); elapsed1 = seconds_since(t0)
    print(f"[Timing] Phase 1 solved in {elapsed1}s (res={res1})")
    if res1==unsat:
        save_solution_json(n,'unsat',elapsed1,[],optimise=True); return
    if res1!=sat:
        save_solution_json(n,'timeout',elapsed1,[],optimise=True); return
    best_model = s.model()
    best_val = int(best_model.evaluate(total_imbalance).as_long())
    print(f"[INFO] Initial model | imbalance = {best_val}")
    if best_val>LB:
        print("[INFO] Phase 2: decremental search…")
        per_iter=60_000 if n>=8 else 30_000
        for k in range(best_val-2,LB-1,-2):
            s.push(); s.add(total_imbalance <= k); s.set("timeout",per_iter)
            if s.check()==sat:
                best_model,best_val=s.model(),k
            s.pop()
    sol=extract_solution(best_model,M,W,P)
    total_elapsed=seconds_since(t0)
    print(f"[Timing] Total optimisation time: {total_elapsed}s")
    save_solution_json(n,'sat',total_elapsed,sol,optimise=True,obj_val=best_val)
    print(f"[RESULT] SMT | total_imbalance = {best_val}")

# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
parser=argparse.ArgumentParser(description="SMT (Z3) solver for Sports Tournament Scheduling – decision & optimisation")
parser.add_argument("N",type=int,nargs="?",help="even number of teams")
parser.add_argument("-a","--automatic",action="store_true",help="solve N=4,6,...,14 in batch")
parser.add_argument("-o","--optimise",action="store_true",help="minimise total home-away imbalance")
parser.add_argument("--export-smt2",action="store_true",help="export SMT-LIB2 file n{N}.smt2")
parser.add_argument("--no-sb",action="store_true",help="disable row/column symmetry breaking")
args=parser.parse_args()
if args.automatic:
    for n in range(4,15,2): solve_instance(n,args,optimise=args.optimise)
else:
    (solve_instance(args.N,args,optimise=args.optimise) if args.N else parser.error("Positional N required unless -a is used."))
