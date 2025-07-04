import argparse
import subprocess
import sys
import json
import re
from pathlib import Path


def merge_into_json(json_file: Path, key: str, value: dict):
    # ensure the directory for json_file is there
    json_file.parent.mkdir(parents=True, exist_ok=True)

    # load existing or start fresh
    if json_file.exists():
        existing = json.loads(json_file.read_text())
    else:
        existing = {}

    # merge in the new solver‐results
    existing[key] = value

    # write back
    json_file.write_text(
        json.dumps(existing, separators=(',', ':'), indent=2)
    )

def run_satisfaction_cli(model_path: str, data_path: str, solver: str, timeout: int) -> dict:
    """
    Run the satisfaction MiniZinc model via CLI, capture its custom JSON output,
    and inject the actual solve-time and optimal flag.
    """
    cmd = [
        "minizinc", model_path, data_path,
        "--solver", solver,
        "--time-limit", str(timeout),
        "--output-time"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    raw = proc.stdout or ""
    err = proc.stderr or ""

    # Extract JSON from model's custom output block
    lines = [l for l in raw.splitlines() if l.strip() and not l.strip().startswith('%')]
    if not lines:
        raise RuntimeError("No output from satisfaction model. stderr:\n%s" % err)
    text = "\n".join(lines)

    # Locate JSON braces
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        raise RuntimeError("Invalid output format from satisfaction model. Output:\n%s" % text)
    json_text = text[start:end+1]

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise RuntimeError("Failed to parse JSON output: %s\n%s" % (e, text))

    # Extract solver-reported time
    m = re.search(r'time elapsed: ([0-9.]+) s', raw)
    time_val = float(m.group(1)) if m else 0.0
    timeout_s = timeout / 1000.0
    optimal = time_val < timeout_s

    # Inject fields under CP
    container = data.get('CP', data)
    container['time'] = time_val if optimal else timeout_s
    container['optimal'] = optimal

    return data
def run_optimization_cli(model_path: str, data_path: str, solver: str, timeout: int) -> dict:
    """
    Run the optimization model, let MiniZinc emit exactly the same JSON as satisfaction,
    then parse and return that dict.
    """
    cmd = [
        "minizinc", model_path, data_path,
        "--solver", solver,
        "--time-limit", str(timeout),
        "--output-time"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    raw = proc.stdout or ""
    err = proc.stderr or ""

    # strip comments/blanks
    lines = [l for l in raw.splitlines() if l.strip() and not l.strip().startswith('%')]
    if not lines:
        raise RuntimeError(f"No output from optimization model. stderr:\n{err}")
    text = "\n".join(lines)

    # grab the JSON blob
    start = text.find('{')
    end   = text.rfind('}')
    if start == -1 or end == -1:
        raise RuntimeError(f"Bad JSON from optimizer:\n{text}")
    json_text = text[start:end+1]

    # parse it
    data = json.loads(json_text)
    # now data is exactly { "CP": { "sol":…, "obj":…, "time":…, "optimal":… } }
    return data



def run_batch(model_path: str,
              solver: str,
              out_dir: Path,
              timeout: int,
              model_type: str):
    """
    Batch-run either the satisfaction or optimization model for all even n,
    and merge each result into <out_dir>/<n>.json under key "{solver}_{model_type}".
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = out_dir / 'data'
    data_dir.mkdir(exist_ok=True)

    if model_type == 'satisfaction':
        ns = range(6, 17, 2)
        runner = run_satisfaction_cli
    else:
        ns = range(6, 15, 2)
        runner = run_optimization_cli

    for n in ns:
        # 1) write the .dzn
        dzn = data_dir / f'n{n}.dzn'
        dzn.write_text(f'n = {n};')

        # 2) run the model & get its JSON
        result = runner(model_path, str(dzn), solver, timeout)
        # pick the inner CP container if present
        container = result.get('CP', result)

        # 3) merge into n.json
        json_file = out_dir / f'{n}.json'
        key = f'{solver}_{model_type}'
        merge_into_json(json_file, key, container)

        print(f"[INFO] merged {key} into {json_file}")


def run_single(model_path: str,
               solver: str,
               model_type: str,
               n: int,
               timeout: int,
               out_dir: Path):
    """
    Run one model instance for a specific n, merge into out_dir/n.json.
    """
    if n % 2 != 0:
        print(f"[ERROR] n must be even, got {n}", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = out_dir / 'data'
    data_dir.mkdir(exist_ok=True)

    dzn = data_dir / f'n{n}.dzn'
    dzn.write_text(f'n = {n};')

    if model_type == 'satisfaction':
        result = run_satisfaction_cli(model_path, str(dzn), solver, timeout)
    else:
        result = run_optimization_cli(model_path, str(dzn), solver, timeout)

    container = result.get('CP', result)
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
    p_all.add_argument('--output-dir', default='results', help='Output directory')
    p_all.add_argument('--timeout', type=int, default=300000, help='Timeout in ms')
    p_all.add_argument('--sat-solver', default='chuffed', help='Solver tag for satisfaction')
    p_all.add_argument('--opt-solver', default='cp-sat', help='Solver tag for optimization')

    p_single = sub.add_parser('single', help='Run one model for a given n')
    p_single.add_argument('--model', required=True, choices=['satisfaction', 'optimization'],
                          help='Which model to run')
    p_single.add_argument('--model-path', required=True, help='Path to .mzn file')
    p_single.add_argument('--n', type=int, required=True, help='Even n value')
    p_single.add_argument('--output-dir', default='results', help='Output directory')
    p_single.add_argument('--timeout', type=int, default=300000, help='Timeout in ms')
    p_single.add_argument('--sat-solver', default='chuffed', help='Solver tag for satisfaction')
    p_single.add_argument('--opt-solver', default='cp-sat', help='Solver tag for optimization')

    args = parser.parse_args()
    out_dir = Path(args.output_dir)

    if args.mode == 'all':
        run_batch(args.sat_model, args.sat_solver, out_dir, args.timeout, 'satisfaction')
        run_batch(args.opt_model, args.opt_solver, out_dir, args.timeout, 'optimization')
    else:  # single
        model_type = args.model
        solver = args.sat_solver if model_type == 'satisfaction' else args.opt_solver
        run_single(args.model_path, solver, model_type, args.n, args.timeout, out_dir)


if __name__ == '__main__':
    main()
