from z3 import *

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
            s.add(exactly_one([M[(i, j, w, p)]
                               for i in range(n) for j in range(i + 1, n)]))

def constraint_team_once_per_week(s, M, n, W, P):
    for t in range(n):
        for w in range(W):
            vars_tw = [M[(min(t,o), max(t,o), w, p)]
                       for o in range(n) if o != t
                       for p in range(P)]
            s.add(exactly_one(vars_tw))

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
    # IMPLIED CONSTRAINT 2: Each week has exactly n/2 matches per period
    # Since each period can have at most one match, and we have n/2 periods,
    # each period must have exactly 1 match
    for w in range(W):
        for p in range(P):
            vars_wp = [M[(i, j, w, p)]
                      for i in range(n) for j in range(i + 1, n)]
            s.add(exactly_one(vars_wp))

def simple_rowcol_lex(s, M, n, W, P):
    w = 0
    if P >= 2 and n >= 4:
        s.add(Or(Not(M[(0,1,w,0)]), M[(2,3,w,1)]))
        s.add(Or(Not(M[(0,2,w,0)]), M[(1,3,w,1)]))

    p = 0
    if W >= 2 and n >= 4:
        s.add(Or(Not(M[(0,1,0,p)]), M[(2,3,1,p)]))
        s.add(Or(Not(M[(0,2,0,p)]), M[(1,3,1,p)]))
