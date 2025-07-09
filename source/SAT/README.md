SAT_STS.py — Sports Tournament Scheduling via SAT (Z3)
=======================================================

This Python script solves the Sports Tournament Scheduling (STS) problem 
using Z3 SAT solver in a decision setting.

Problem
----------
Given:
- An even number N of teams
- N-1 weeks
- N/2 periods per week

Each team must:
- Play every other team exactly once
- Play once per week
- Appear at most twice in the same period across the whole tournament

Example output format (for N=6):
Each match is a [home_team, away_team] pair, and matches are grouped
by period (rows) and weeks (columns):

[
  [[2, 4], [5, 1], [3, 6], [3, 4], [6, 2]],
  [[5, 6], [2, 3], [4, 5], [6, 1], [1, 4]],
  [[1, 3], [4, 6], [2, 1], [5, 2], [3, 5]]
]

Output
---------
Results are saved in:
  res/SAT/n<N>.json

The JSON contains:
- "time": total solving time (in seconds, floored)
- "optimal": whether a solution was found
- "obj": always null in SAT version
- "sol": the schedule matrix as described above
 How to Run
-------------
Requirements:
- Python 3.8+
- z3-solver (`pip install z3-solver`)

Single instance:
    python SAT_STS.py 6

Batch mode for N=4,6,...,14:
    python SAT_STS.py -a

Command-line Flags
---------------------
Positional:
  N                    Number of teams (must be even)

Optional:
  -a, --automatic      Solve all instances from N=4 to N=14 (even)
  -o, --optimise       Ignored in this script (used in MIP only)
  --no-sb              Disable symmetry breaking (not recommended)

📁 Project Structure
--------------------
- SAT_STS.py       => Main script
- constraints.py   => Encodes all model constraints
- res/SAT/         => Output folder for solutions (JSON format)
Notes
--------
- Timeout is fixed to 300 seconds.
- Symmetry-breaking constraints are ON by default.
- Supports CLI execution and works with Docker setups.
- Automatically creates missing folders.

Course
---------
Combinatorial Decision Making and Optimization (CDMO)
Academic Year: 2024/2025 – University of Bologna

