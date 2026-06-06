"""Measure import times for imported python scripts"""

import os
import statistics
import subprocess
import sys
import time

runs = int(sys.argv[1])
file_dir=os.path.normpath(sys.argv[2])
files= sys.argv[3:]

def run_once(code: str) -> float:
    start = time.perf_counter_ns()
    result = subprocess.run(  # noqa
        [sys.executable, "-c", f"import sys;sys.path.insert(0, r'{file_dir}');"+ code],
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


def measure(code: str, runs: int) -> list[float]:
    return [run_once(code) for _ in range(runs)]


def format_stats(values: list[float], baseline_ms: float) -> str:
    median_ms = statistics.median(values)
    mean_ms = statistics.mean(values)
    return f"{median_ms - baseline_ms:8.1f} {mean_ms - baseline_ms:8.1f}"


def main() -> int:

    baseline = measure("pass", runs)
    baseline_median = statistics.median(baseline)

    print(f"Runs per module: {runs}")
    print(f"Baseline process startup median: {baseline_median:.1f} ms")
    print()
    print("[ms] Median-Baseline Mean-Baseline Module")
    print("-----------------------------------")

    for f in files:
        values = measure(f"import {f}", runs)
        print(f"{format_stats(values, baseline_median)}  {f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
