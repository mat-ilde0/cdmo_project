from z3 import Or, Not, PbEq, PbLe, Bool
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



def at_most_two_per_period(s, M, n, W, P):
    for t in range(n):
        for p in range(P):
            lits = [(M[(min(t,o), max(t,o), w, p)], 1)
                    for o in range(n) if o != t
                    for w in range(W)]
            s.add(PbLe(lits, 2))



def add_simple_symmetry(s, M):
    s.add(M[(0, 1, 0, 0)]) 
    s.add(M[(0, 2, 1, 0)])  
    
def fix_first_round(solver, M, n, weeks, periods):
    # week 0, period p: squadra 2p in casa, 2p+1 fuori
    for p in range(periods):
        i = 2*p
        j = 2*p + 1
        solver.add(M[(i, j, 0, p)])
