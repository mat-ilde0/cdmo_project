from z3 import *
from itertools import combinations


def at_least_one(vars_):
    return Or(vars_)

def at_most_one(vars_):
    return PbLe([(v, 1) for v in vars_], 1)

def exactly_one(vars_):
    return PbEq([(v, 1) for v in vars_], 1)



def constraint_each_pair_once(s, M, n, W, P):
    for i in range(n):
        for j in range(i + 1, n):
            s.add(exactly_one([M[(i, j, w, p)] for w in range(W) for p in range(P)]))

def constraint_one_match_per_slot(s, M, n, W, P):
    for w in range(W):
        for p in range(P):
            s.add(at_most_one([M[(i, j, w, p)]
                               for i in range(n) for j in range(i + 1, n)]))

def constraint_team_once_per_week(s, M, n, W, P):
    for t in range(n):
        for w in range(W):
            s.add(at_most_one([M[(min(t,o), max(t,o), w, p)]
                               for o in range(n) if o != t
                               for p in range(P)]))



def add_simple_symmetry(s, M):
    s.add(M[(0, 1, 0, 0)])

def at_most_two_per_period(s, M, n, W, P):
    for t in range(n):
        for p in range(P):
            lits = [(M[(min(t,o), max(t,o), w, p)], 1)
                    for o in range(n) if o != t
                    for w in range(W)]
            s.add(PbLe(lits, 2))
            

def at_most_two_per_period_optimized(s, M, n, W, P):
    for t in range(n):
        for p in range(P):
            vars_tp = [M[(min(t,o), max(t,o), w, p)]
                      for o in range(n) if o != t
                      for w in range(W)]
            s.add(PbLe([(v, 1) for v in vars_tp], 2))

        
def add_implied_constraints(s, M, n, W, P):
    # IMPLIED CONSTRAINT 1: Each team plays exactly once per week
    # This strengthens your current "at most once per week" constraint
    for t in range(n):
        for w in range(W):
            vars_tw = [M[(min(t,o), max(t,o), w, p)]
                      for o in range(n) if o != t
                      for p in range(P)]
            s.add(exactly_one(vars_tw))
    
    # IMPLIED CONSTRAINT 2: Each week has exactly n/2 matches per period
    # Since each period can have at most one match, and we have n/2 periods,
    # each period must have exactly 1 match
    for w in range(W):
        for p in range(P):
            vars_wp = [M[(i, j, w, p)]
                      for i in range(n) for j in range(i + 1, n)]
            s.add(exactly_one(vars_wp))

def simple_rowcol_lex(s, M, n, W, P):
    """
    • Orders periods (rows) using only the matches scheduled in **week 0**.
    • Orders weeks   (columns) using only the matches scheduled in **period 0**.

    Each row/column is encoded as a single integer 'code' = Σ weight(i,j) · lit .
    The constraint  code_row_p  ≤  code_row_{p+1}   breaks row permutations,
    and similarly for columns.  Much faster than comparing the full matrix.
    """
    def weight(i, j):            # unique positive weight for each pair (i,j)
        return i * n + j + 1     # monotone → preserves lex order

    # --- order periods (rows) ---------------------------------------------
    row_codes = []
    w0 = 0                       # use week 0 only
    for p in range(P):
        code = Sum([
            If(M[(i, j, w0, p)], weight(i, j), 0)
            for i in range(n) for j in range(i + 1, n)
        ])
        row_codes.append(code)
    for p in range(P - 1):
        s.add(row_codes[p] <= row_codes[p + 1])

    # --- order weeks (columns) --------------------------------------------
    col_codes = []
    p0 = 0                       # use period 0 only
    for w in range(W):
        code = Sum([
            If(M[(i, j, w, p0)], weight(i, j), 0)
            for i in range(n) for j in range(i + 1, n)
        ])
        col_codes.append(code)
    for w in range(W - 1):
        s.add(col_codes[w] <= col_codes[w + 1])
