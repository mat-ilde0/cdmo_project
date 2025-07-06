#!/usr/bin/env python3
"""
run_all_scripts.py

Sequentially executes the three analysis stages:
  1. MIP model
  2. SAT-based STS
  3. SMT-based STS

Usage:
  python run_all_scripts.py

Each command is echoed before execution, and its output (stdout+stderr)
is streamed live.
"""
import subprocess
import sys
from pathlib import Path

# List of commands to run (modify paths if needed)
commands = [
    [sys.executable, 'MIP/mip_model.py', '-a'],
    [sys.executable, 'SAT/SAT_STS.py', '-a'],
    [sys.executable, 'SMT/SMT_STS.py', '-a'],
    # TODO : add also CP
]


def run_command(cmd):
    """Run a command and stream its output."""
    print(f"\n$ {' '.join(cmd)}\n", flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout
    for line in proc.stdout:
        print(line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        print(f"Command {cmd[1]} exited with status {proc.returncode}", file=sys.stderr)
        # Optionally: sys.exit(proc.returncode)


def main():
    # Verify scripts exist
    for cmd in commands:
        script = Path(cmd[1])
        if not script.exists():
            print(f"Script not found: {script}", file=sys.stderr)
            sys.exit(1)

    for cmd in commands:
        run_command(cmd)


if __name__ == '__main__':
    main()