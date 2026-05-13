import argparse
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DONT_CHANGE_DIR = SCRIPT_DIR.parent
CODE_DIR = DONT_CHANGE_DIR.parent

MODULES = [
    "DONT_CHANGE.specific_scripts.common_variables",
    "DONT_CHANGE.specific_scripts.common_code",
    "DONT_CHANGE.specific_scripts.launcher_common",
]


def run_once(code: str, env: dict[str, str]) -> float:
    start = time.perf_counter_ns()
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=CODE_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    if result.returncode != 0:
        output = (result.stdout or "").strip()
        detail = f"\n{output}" if output else ""
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {code}{detail}")
    return elapsed_ms


def measure(code: str, runs: int, env: dict[str, str]) -> list[float]:
    return [run_once(code, env) for _ in range(runs)]


def format_stats(values: list[float], baseline_ms: float) -> str:
    median_ms = statistics.median(values)
    mean_ms = statistics.mean(values)
    return f"{median_ms - baseline_ms:8.1f} {median_ms:8.1f} {mean_ms:8.1f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure import cost for shared PyApp backend modules.")
    parser.add_argument("--runs", type=int, default=10, help="Fresh subprocess runs per import. Default: 10.")
    args = parser.parse_args()

    if args.runs < 1:
        raise ValueError("--runs must be at least 1")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(CODE_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    baseline = measure("pass", args.runs, env)
    baseline_median = statistics.median(baseline)

    print(f"Runs per module: {args.runs}")
    print(f"Baseline process startup median: {baseline_median:.1f} ms")
    print()
    print("ImportMs  TotalMs   MeanMs  Module")
    print("-----------------------------------")

    for module in MODULES:
        values = measure(f"import {module}", args.runs, env)
        print(f"{format_stats(values, baseline_median)}  {module}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
