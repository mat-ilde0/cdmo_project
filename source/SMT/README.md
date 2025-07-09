SMT_STS.py — Sports Tournament Scheduling with SMT (Z3)
========================================================

This Python script solves the Sports Tournament Scheduling (STS) problem 
using the Z3 solver with SMT (Satisfiability Modulo Theories), supporting both 
decision and optimization modes.

Problem Description
-------------------
You are given:
- An even number N of teams
- N−1 weeks
- N/2 periods per week

Constraints:
- Each pair of teams plays exactly once
- Each team plays once per week
- Each team plays at most twice in the same period
- (Optional) Minimize the total home-away imbalance across all teams

Output Format
-------------
Solutions are saved as JSON files to:
  res/SMT/n<N>.json

Example format:
{
  "SMT_dec": {
    "time": 54,
    "optimal": true,
    "obj": null,
    "sol": [
      [[2, 4], [5, 1], [3, 6], [3, 4], [6, 2]],
      [[5, 6], [2, 3], [4, 5], [6, 1], [1, 4]],
      [[1, 3], [4, 6], [2, 1], [5, 2], [3, 5]]
    ]
  }
}

If optimization is enabled (`--optimise`), the key becomes "SMT_opt" and includes
the minimized imbalance value in the "obj" field.

Features
--------
- Decision mode: returns SAT, UNSAT or TIMEOUT
- Optional optimization mode: minimizes total home-away imbalance

