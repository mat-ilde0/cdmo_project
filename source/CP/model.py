#!/usr/bin/env python3
import argparse, time, math, json, re
from pathlib import Path
from datetime import timedelta
from minizinc import Model, Solver, Instance

TIME_LIMIT_MS = 300_000
TIME_LIMIT_S  = TIME_LIMIT_MS // 1000

def merge_into_json(json_file: Path, key: str, value: dict):
    json_file.parent.mkdir(parents=True, exist_ok=True)
    if json_file.exists():
        existing = json.loads(json_file.read_text())
    else:
        existing = {}
    existing[key] = value
    text = json.dumps(existing, separators=(',', ':'), indent=2)
    def _collapse(m: re.Match) -> str:
        nums = re.sub(r'\s+', '', m.group(1))
        return f'[{nums}]'
    text = re.sub(r'\[\s*([\d\.\-eE\+]+(?:\s*,\s*[\d\.\-eE\+]+)*)\s*\]', _collapse, text)
    json_file.write_text(text + "\n")

# ─────────── CONFIGURATION FOR “ALL” MODE ───────────
# for satisfaction (decision) runs, all even n from 6 to 16
ALL_SAT_N = list(range(6, 17, 2))
# for optimization runs, all even n from 6 to 14
ALL_OPT_N = list(range(6, 15, 2))

# which solvers to try
ALL_SOLVERS    = ["chuffed", "gecode", "ortools"]
# combinations of the two boolean flags
ALL_HEURISTICS = [False, True]
ALL_SYMBREAK   = [False, True]
# ────────────────────────────────────────────────────

BASE_MODEL = r"""
include "globals.mzn";

bool: sb;      % flag for symmetry breaking

int: n;
set of int: TEAMS = 1..n;
set of int: WEEKS = 1..n-1;
set of int: SLOTS = 1..n div 2;

/* Variables */
array[TEAMS,WEEKS] of var TEAMS: O;
array[TEAMS,WEEKS] of var SLOTS: P;
enum HA = { Home, Away };
array[TEAMS,WEEKS] of var HA: H;

/* 1) Pairing symmetry */
constraint forall(t in TEAMS, w in WEEKS)(
  O[t,w] != t /\ O[O[t,w],w] = t
);
/* 2) Each pair once */
constraint forall(t in TEAMS)(
  all_different([O[t,w] | w in WEEKS])
);
/* 3) At most twice in same slot */
constraint forall(t in TEAMS, s in SLOTS)(
  sum(w in WEEKS)(bool2int(P[t,w]==s)) <= 2
);
/* 4) One match per week */
constraint forall(w in WEEKS)(
  all_different([O[t,w] | t in TEAMS])
);
/* 5) Exactly two per slot */
constraint forall(w in WEEKS, s in SLOTS)(
  sum(t in TEAMS)(bool2int(P[t,w]==s)) = 2
);
/* 6) Home/Away consistency */
constraint forall(w in WEEKS, t in TEAMS)(
  let { var TEAMS: u = O[t,w] } in
    (H[t,w]=Home /\ H[u,w]=Away)
  \/ (H[t,w]=Away /\ H[u,w]=Home)
);
/* 7) Slot↔Opponent channeling */
constraint forall(w in WEEKS, t in TEAMS, u in TEAMS where t<u)(
  (O[t,w]=u) <-> (P[t,w]=P[u,w])
);
/* 8) Perfect matching each week */
constraint forall(w in WEEKS)(
  inverse([O[t,w] | t in TEAMS], [O[t,w] | t in TEAMS])
);

%— only apply these three if sb=true
constraint sb -> forall(i in 1..n div 2)(
  O[i,1]=n+1-i /\ O[n+1-i,1]=i
  /\ H[i,1]=Home  /\ H[n+1-i,1]=Away
);
array[WEEKS] of var SLOTS: Seq1 = [P[1,w] | w in WEEKS];
array[WEEKS] of var SLOTS: Seq2 = [P[2,w] | w in WEEKS];
constraint sb -> lex_lesseq(Seq1,Seq2);
constraint sb -> (P[1,1]=1);

/* Channeling for output */
array[SLOTS,WEEKS] of var TEAMS: HomeTeam;
array[SLOTS,WEEKS] of var TEAMS: AwayTeam;
constraint forall(w in WEEKS, s in SLOTS)(
  exists(t in TEAMS)(P[t,w]=s /\ H[t,w]=Home  /\ HomeTeam[s,w]=t)
  /\
  exists(t in TEAMS)(P[t,w]=s /\ H[t,w]=Away  /\ AwayTeam[s,w]=t)
);
"""

OPT_PART = r"""
array[TEAMS] of var int: HA_diff = [
  sum(w in WEEKS)(bool2int(H[t,w]==Home))
  - sum(w in WEEKS)(bool2int(H[t,w]==Away))
  | t in TEAMS
];
array[TEAMS] of var 0..n: HA_abs = [abs(HA_diff[t]) | t in TEAMS];
var int: Obj = sum(t in TEAMS)(HA_abs[t]);
"""

def build_model(opt: bool, heur: bool) -> str:
    m = BASE_MODEL
    if opt:
        m += "\n" + OPT_PART + "\n"
    ann = ""
    if heur:
        ann = " :: int_search(" \
              "[O[t,w] | t in TEAMS, w in WEEKS] ++ " \
              "[P[t,w] | t in TEAMS, w in WEEKS] ++ " \
              "[H[t,w] | t in TEAMS, w in WEEKS]," \
              "first_fail,indomain_min)"
    m += f"solve{ann} {'minimize Obj;' if opt else 'satisfy;'}\n"
    return m

def run_and_collect(n:int, opt:bool, heur:bool, solver_tag:str, sb:bool):
    api_solver = "cp-sat" if solver_tag=="ortools" else solver_tag

    model = Model()
    model.add_string(build_model(opt, heur))
    solver = Solver.lookup(api_solver)
    inst = Instance(solver, model)
    inst["n"]  = n
    inst["sb"] = sb

    to = timedelta(seconds=TIME_LIMIT_S)
    t0 = time.time()
    res = inst.solve(timeout=to)
    t1 = time.time()

    elapsed = math.floor(t1 - t0)
    status  = str(res.status).upper()
    timed_out = "UNKNOWN" in status

    sol = []
    if not timed_out:
        try:
            H, A = res["HomeTeam"], res["AwayTeam"]
            sol = [[[H[s][w], A[s][w]] for w in range(len(H[0]))]
                   for s in range(len(H))]
        except:
            sol = []

    entry = {
      "sol": sol if sol and not timed_out else [],
      "time": TIME_LIMIT_S if timed_out else elapsed
    }

    if opt:
        entry["optimal"] = (not timed_out and status.startswith("OPTIMAL"))
        entry["obj"]     = res.objective if not timed_out else None
    else:
        entry["optimal"] = (not timed_out and bool(sol))
        entry["obj"]     = None

    return entry

def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("-n",    type=int,           help="even # teams (single-run mode)")
    group.add_argument("--all", action="store_true", help="run full sweep of configurations")

    p.add_argument("--opt",        action="store_true", help="run optimization version")
    p.add_argument("--heuristics", action="store_true", help="use first-fail heuristic")
    p.add_argument("--solver",
        choices=["chuffed","gecode","ortools"],
        help="solver to use (default: chuffed for sat, ortools for opt)")
    p.add_argument(
        "--no-symmetry-breaking",
        dest="sb",
        action="store_false",
        help="omit symmetry-breaking constraints (default: include them)"
    )
    p.set_defaults(sb=True)
    args = p.parse_args()

    # “All” mode sweep
    if args.all:
        for opt in (False, True):
            Ns = ALL_OPT_N if opt else ALL_SAT_N
            for n in Ns:
                for heur in ALL_HEURISTICS:
                    for solver_tag in ALL_SOLVERS:
                        for sb in ALL_SYMBREAK:
                            result = run_and_collect(n, opt, heur, solver_tag, sb)
                            mode   = "opt" if opt else "sat"
                            suffix = "_hf" if heur else ""
                            sb_suf = "" if sb else "_nosb"
                            key    = f"{solver_tag}_{mode}{suffix}{sb_suf}"
                            out = Path("res/CP") / f"{n}.json"
                            merge_into_json(out, key, result)
                            print(f"[INFO] merged {key} into {out}")
        return

    # Single-run mode: enforce even n
    if args.n % 2 != 0:
        raise SystemExit("n must be even")

    solver_tag = args.solver or ("ortools" if args.opt else "chuffed")
    result = run_and_collect(args.n, args.opt, args.heuristics, solver_tag, args.sb)

    mode   = "opt" if args.opt else "sat"
    suffix = "_hf" if args.heuristics else ""
    sb_suf = "" if args.sb else "_nosb"
    key    = f"{solver_tag}_{mode}{suffix}{sb_suf}"
    out = Path("res/CP") / f"{args.n}.json"
    merge_into_json(out, key, result)
    print(f"[INFO] merged {key} into {out}")

if __name__=="__main__":
    main()
