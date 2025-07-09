from z3 import *

def constraint_each_pair_once_smt(solver, M, n, W, P):
    for i in range(n):
        for j in range(i + 1, n):
            lits = [M[(i, j, w, p)] for w in range(W) for p in range(P)]
            solver.add(Sum([If(m, 1, 0) for m in lits]) == 1)

def constraint_one_match_per_slot_smt(solver, M, n, W, P):
    for w in range(W):
        for p in range(P):
            lits = [M[(i, j, w, p)] for i in range(n) for j in range(i + 1, n)]
            solver.add(Sum([If(m, 1, 0) for m in lits]) == 1)

def constraint_team_once_per_week_smt(solver, M, n, W, P):
    for t in range(n):
        for w in range(W):
            lits = []
            for o in range(n):
                if o == t:
                    continue
                i_, j_ = (t, o) if t < o else (o, t)
                for p in range(P):
                    lits.append(M[(i_, j_, w, p)])
            solver.add(Sum([If(m, 1, 0) for m in lits]) == 1)

def constraint_at_most_two_per_period_smt(solver, M, n, W, P):
    for t in range(n):
        for p in range(P):
            lits = []
            for o in range(n):
                if o == t:
                    continue
                i_, j_ = (t, o) if t < o else (o, t)
                for w in range(W):
                    lits.append(M[(i_, j_, w, p)])
            solver.add(Sum([If(m, 1, 0) for m in lits]) <= 2)

def constraint_symmetry_breaking(solver, M, n):
    solver.add(M[(0, 1, 0, 0)])
def simple_rowcol_lex(s, M, n, W, P):
    def weight(i, j):
        return i * n + j + 1

    p0 = 0
    week_codes = []
    for w in range(W):
        code = Sum([
            If(M[(i, j, w, p0)], weight(i, j), 0)
            for i in range(n) for j in range(i + 1, n)
        ])
        week_codes.append(code)

    for w in range(W - 1):
        s.add(week_codes[w] <= week_codes[w + 1])


def add_total_home_away_imbalance_expr(solver, M, n):
    matches_per_team = n - 1         

    home_vars = [[] for _ in range(n)]
    for (i, j, _, _), v in M.items():     # i < j
        home_vars[i].append(v)

    diffs = []
    for i in range(n):
        home_i = Sum([If(v, 1, 0) for v in home_vars[i]])
        d_i = Int(f"diff_{i}")
        solver.add(d_i >=  2*home_i - matches_per_team)
        solver.add(d_i >= -2*home_i + matches_per_team)
        diffs.append(d_i)

    total_imbalance = Int("total_imbalance")
    solver.add(total_imbalance == Sum(diffs))
    
    LB = n               
    UB = n * (n - 1)     
    solver.add(total_imbalance >= LB, total_imbalance <= UB)

    return total_imbalance