from itertools import combinations
from z3 import *

def at_least_one(bool_vars):
    return Or(bool_vars)

def at_most_one(bool_vars):
    return [Not(And(pair[0], pair[1])) for pair in combinations(bool_vars, 2)]

def exactly_one(solver, bool_vars):
    solver.add(at_least_one(bool_vars))
    solver.add(*at_most_one(bool_vars))

def add_at_most_one_match_per_slot(solver, match_vars, n, weeks, periods):
    for w in range(weeks):
        for p in range(periods):
            vars_in_slot = []
            for i in range(n):
                for j in range(i + 1, n):
                    vars_in_slot.append(match_vars[(i, j, w, p)])
            solver.add(*at_most_one(vars_in_slot))

def add_team_once_per_week(solver, match_vars, n, weeks, periods):
    for t in range(n):
        for w in range(weeks):
            vars_for_team_week = []
            for p in range(periods):
                for opp in range(n):
                    if opp == t:
                        continue
                    if t < opp:
                        vars_for_team_week.append(match_vars[(t, opp, w, p)])
                    else:
                        vars_for_team_week.append(match_vars[(opp, t, w, p)])
            solver.add(*at_most_one(vars_for_team_week))
