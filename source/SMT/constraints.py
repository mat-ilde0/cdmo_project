from z3 import *

def constraint_each_pair_once_smt(solver, M, n, W, P):
    # Ogni coppia (i,j) gioca esattamente una volta
    for i in range(n):
        for j in range(i + 1, n):
            lits = [M[(i, j, w, p)] for w in range(W) for p in range(P)]
            solver.add(Sum([If(m, 1, 0) for m in lits]) == 1)

def constraint_one_match_per_slot_smt(solver, M, n, W, P):
    # In ogni slot (w,p) si gioca esattamente una partita
    for w in range(W):
        for p in range(P):
            lits = [M[(i, j, w, p)] for i in range(n) for j in range(i + 1, n)]
            solver.add(Sum([If(m, 1, 0) for m in lits]) == 1)

def constraint_team_once_per_week_smt(solver, M, n, W, P):
    # Ogni team gioca esattamente una volta per settimana
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
    # Ogni team gioca al massimo 2 volte per periodo (in tutte le settimane)
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
    # Fissa che team 0 e 1 giochino nello slot iniziale
    solver.add(M[(0, 1, 0, 0)])

def simple_rowcol_lex(s, M, n, W, P):
    """
    Ordina le righe (periodi) usando la settimana 0
    e le colonne (settimane) usando il periodo 0.
    """
    def weight(i, j):
        return i * n + j + 1

    # --- ordina righe (periodi) ---
    w0 = 0
    row_codes = []
    for p in range(P):
        code = Sum([
            If(M[(i, j, w0, p)], weight(i, j), 0)
            for i in range(n) for j in range(i + 1, n)
        ])
        row_codes.append(code)
    for p in range(P - 1):
        s.add(row_codes[p] <= row_codes[p + 1])

    # --- ordina colonne (settimane) ---
    p0 = 0
    col_codes = []
    for w in range(W):
        code = Sum([
            If(M[(i, j, w, p0)], weight(i, j), 0)
            for i in range(n) for j in range(i + 1, n)
        ])
        col_codes.append(code)
    for w in range(W - 1):
        s.add(col_codes[w] <= col_codes[w + 1])
