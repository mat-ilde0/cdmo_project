import argparse
import subprocess
import sys
import json
import re
import math 
from pathlib import Path


def merge_into_json(json_file: Path, key: str, value: dict):
    """
    Merge `value` under `key` into the JSON at `json_file`, writing it back with
    newlines between each key:value pair but keeping numeric lists inline.
    """
    json_file.parent.mkdir(parents=True, exist_ok=True)

    if json_file.exists():
        existing = json.loads(json_file.read_text())
    else:
        existing = {}

    existing[key] = value

    text = json.dumps(existing, separators=(',', ':'), indent=2)

    def _collapse_numeric_list(m: re.Match) -> str:
        nums = m.group(1)
        nums = re.sub(r'\s+', '', nums)
        return f'[{nums}]'
    
    pattern = r'\[\s*([\d\.\-eE\+]+(?:\s*,\s*[\d\.\-eE\+]+)*)\s*\]'
    text = re.sub(pattern, _collapse_numeric_list, text)

    json_file.write_text(text + "\n")

def run_satisfaction_cli(model_path: str, data_path: str, solver: str, timeout: int) -> dict:
    # Build and invoke the MiniZinc command
    cmd = [
        "minizinc", model_path, data_path,
        "--solver", solver,
        "--time-limit", str(timeout),
        "--output-time"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    raw = proc.stdout or ""
    err = proc.stderr or ""
    timeout_s = timeout / 1000.0

    # 1) If MiniZinc really timed out, it emits exactly "=====UNKNOWN====="
    if "=====UNKNOWN=====" in raw:
        return {"sol": None, "time": timeout_s, "optimal": False}

    lines = [
        line
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith('%')
    ]
    if not lines:
        raise RuntimeError(f"No output from satisfaction model. stderr:\n{err}")

    text = "\n".join(lines)

    # Locate and extract the JSON blob
    start = text.find('{')
    end   = text.rfind('}')
    if start == -1 or end == -1:
        raise RuntimeError(f"Invalid output format from satisfaction model. Output:\n{text}")
    json_text = text[start:end+1]

    # Parse it
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON output: {e}\n{text}")

    # Pull out timing information
    m = re.search(r'time elapsed: ([0-9.]+) s', raw)
    time_val = float(m.group(1)) if m else 0.0
    optimal = time_val < timeout_s

    # Inject into the CP container (or top‐level if no "CP" key)
    container = data.get('CP', data)
    container['time']    = time_val if optimal else timeout_s
    container['optimal'] = optimal

    return data

def run_optimization_cli(model_path: str, data_path: str, solver: str, timeout: int) -> dict:
    cmd = [
        "minizinc", model_path, data_path,
        "--solver", solver,
        "--time-limit", str(timeout),
        "--output-time"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    raw = proc.stdout or ""
    err = proc.stderr or ""
    timeout_s = timeout / 1000.0

    # MiniZinc timeout
    if "=====UNKNOWN=====" in raw:
        return {"sol": None, "obj": None, "time": timeout_s, "optimal": False}

    # Strip comments/blanks
    lines = [l for l in raw.splitlines() if l.strip() and not l.strip().startswith('%')]
    if not lines:
        raise RuntimeError(f"No output from optimization model. stderr:\n{err}")
    text = "\n".join(lines)

    # Extract JSON blob
    start = text.find('{')
    end   = text.rfind('}')
    if start == -1 or end == -1:
        raise RuntimeError(f"Bad JSON from optimizer:\n{text}")
    json_text = text[start:end+1]

    # Parse it
    data = json.loads(json_text)

    # Pull out the CP container
    container = data.get('CP', data)

    # Extract solver time & optimal flag
    m = re.search(r'time elapsed: ([0-9.]+) s', raw)
    time_val = float(m.group(1)) if m else 0.0
    optimal = time_val < timeout_s
    container['time']    = time_val if optimal else timeout_s
    container['optimal'] = optimal

    # Normalize or default the objective
    if 'obj' in container:
        # model printed obj as a string "None" when no solution
        if isinstance(container['obj'], str) and container['obj'] == "None":
            container['obj'] = None
    else:
        container['obj'] = None

    return data



def run_batch(model_path: str,
              solver_tag: str,
              solver_name: str,
              out_dir: Path,
              timeout: int,
              model_type: str,
              max_n: int = None):

    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = out_dir / 'data'
    data_dir.mkdir(exist_ok=True)

    if model_type == 'satisfaction':
        ns = list(range(6, 17, 2))
    else:
        ns = list(range(6, 15, 2))

    # apply the gecode cutoff if requested
    if max_n is not None:
        ns = [n for n in ns if n <= max_n]

    # pick the right runner
    runner = run_satisfaction_cli if model_type == 'satisfaction' else run_optimization_cli

    for n in ns:
        # write the .dzn
        dzn = data_dir / f'n{n}.dzn'
        dzn.write_text(f'n = {n};')

        # run the model & get its JSON or flat dict
        result = runner(model_path, str(dzn), solver_tag, timeout)

        # pick the inner CP container if present
        container = result.get('CP', result)

        if model_type == 'optimization' and 'obj' not in container:
            container['obj'] = None

        # Floor the time before writing
        if 'time' in container:
            container['time'] = math.floor(container['time'])

        # merge into n.json
        json_file = out_dir / f'{n}.json'
        key = f'{solver_name}_{model_type}'
        merge_into_json(json_file, key, container)

        print(f"[INFO] merged {key} into {json_file}")


def run_single(model_path: str,
               solver: str,
               model_type: str,
               n: int,
               timeout: int,
               out_dir: Path):
    if n % 2 != 0:
        print(f"[ERROR] n must be even, got {n}", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = out_dir / 'data'
    data_dir.mkdir(exist_ok=True)

    # write the .dzn
    dzn = data_dir / f'n{n}.dzn'
    dzn.write_text(f'n = {n};')

    # run the appropriate CLI
    if model_type == 'satisfaction':
        result = run_satisfaction_cli(model_path, str(dzn), solver, timeout)
    else:
        result = run_optimization_cli(model_path, str(dzn), solver, timeout)

    # extract container
    container = result.get('CP', result)

    # floor the time if present
    if 'time' in container:
        container['time'] = math.floor(container['time'])

    # merge into the JSON file
    json_file = out_dir / f'{n}.json'
    key = f'{solver}_{model_type}'
    merge_into_json(json_file, key, container)

    print(f"[INFO] merged {key} into {json_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Run MiniZinc models and merge results into per-n JSON files."
    )
    sub = parser.add_subparsers(dest='mode', required=True)

    p_all = sub.add_parser('all', help='Batch-run both models for all n')
    p_all.add_argument('--sat-model', required=True, help='Path to satisfaction .mzn')
    p_all.add_argument('--opt-model', required=True, help='Path to optimization .mzn')
    p_all.add_argument('--output-dir', default='res/CP', help='Output directory')
    p_all.add_argument('--timeout', type=int, default=300000, help='Timeout in ms')
    p_all.add_argument(
        '--sat-solvers', nargs='+',
        choices=['chuffed', 'gecode'],
        default=['chuffed', 'gecode'],
        help='Solvers for satisfaction (default: chuffed and gecode)'
    )
    p_all.add_argument(
        '--opt-solvers', nargs='+',
        choices=['ortools', 'gecode'],
        default=['ortools', 'gecode'],
        help='Solvers for optimization (default: ortools→cp-sat and gecode)'
    )
    p_all.add_argument(
        '--gecode-max-sat', type=int, default=10,
        help='Max even n to run gecode on satisfaction (default: 10)'
    )
    p_all.add_argument(
        '--gecode-max-opt', type=int, default=6,
        help='Max even n to run gecode on optimization (default: 6)'
    )

    p_single = sub.add_parser('single', help='Run one model for a given n')
    p_single.add_argument('--model', required=True, choices=['satisfaction', 'optimization'],
                          help='Which model to run')
    p_single.add_argument('--model-path', required=True, help='Path to .mzn file')
    p_single.add_argument('--n', type=int, required=True, help='Even n value')
    p_single.add_argument('--output-dir', default='res/CP', help='Output directory')
    p_single.add_argument('--timeout', type=int, default=300000, help='Timeout in ms')
    p_single.add_argument('--sat-solver', default='chuffed', help='Solver tag for satisfaction')
    p_single.add_argument('--opt-solver', default='cp-sat', help='Solver tag for optimization')

    args = parser.parse_args()
    out_dir = Path(args.output_dir)

    if args.mode == 'all':
        # run chuffed & gecode on the satisfaction model
        # run chuffed & gecode on the satisfaction model
        for s in args.sat_solvers:
            solver_tag = s
            max_n = args.gecode_max_sat if s == 'gecode' else None
            run_batch(
                args.sat_model,
                solver_tag,
                s,
                out_dir,
                args.timeout,
                'satisfaction',
                max_n=max_n
            )
        # run ortools (cp-sat) & gecode on the optimization model
        for s in args.opt_solvers:
            solver_tag = 'cp-sat' if s == 'ortools' else s
            max_n = args.gecode_max_opt if s == 'gecode' else None
            run_batch(
                args.opt_model,
                solver_tag,
                s,
                out_dir,
                args.timeout,
                'optimization',
                max_n=max_n
            )

    else:  # single
        model_type = args.model
        solver = args.sat_solver if model_type == 'satisfaction' else args.opt_solver
        run_single(args.model_path, solver, model_type, args.n, args.timeout, out_dir)


if __name__ == '__main__':
    main()
