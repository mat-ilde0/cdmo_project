#!/usr/bin/env bash
set -eo pipefail

# This script sequentially runs all four stages with -a (automatic) mode.

PY=python   # adjust if your container uses a different python command

echo "=== Running MIP stage ==="
$PY source/MIP/mip_model.py -a

echo "=== Running SAT stage ==="
$PY source/SAT/SAT_STS.py -a

echo "=== Running SMT stage ==="
$PY source/SMT/SMT_STS.py -a

echo "=== Running CP stage ==="
$PY source/CP/CP_STS.py -a