"""Measure how long the launcher takes until main.py runs (Windows only).

The project is copied into a temporary folder (logs, shortcuts and DONT_CHANGE/tmp left out);
main.py in the copy is replaced by a probe that only writes a marker file. The copy is then
started the way its shortcuts start it, and the time until the marker appears is measured:

    terminal     B\\W.bat in a new console (the normal shortcut)
    no_terminal  B\\N.bat (the "(no Terminal)" shortcut)
    direct       .venv\\Scripts\\python.exe main.py: no launcher at all, the floor to compare with

Every target is started once untimed first, so the runtime cache, the environment check and the
.venv of the copy are ready (the first launch after a change is slower by design). The project
itself is never touched.

Usage: python measure_startup_time.py [--runs 5] [--timeout 60] [--targets terminal direct] [--keep]
"""

from __future__ import annotations

import argparse
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

from _paths import CODE_DIR, PROJECT_ROOT, STARTUP_BENCHMARK_WORK_DIR

TARGETS = ("terminal", "no_terminal", "direct")
LEFT_OUT_IN_PROJECT_ROOT = {"logs", "crash logs", ".git"}
PROBE = """import os
with open({marker!r}, "w") as marker:
    marker.write(str(os.getpid()))
"""


def copy_project(destination: Path) -> None:
    """Copy the project without logs, shortcuts, caches and the launcher's runtime state."""
    dont_change = PROJECT_ROOT / "code" / "backend" / "DONT_CHANGE"

    def ignore(folder, names):
        here = Path(folder).resolve()
        left_out = {name for name in names if name == "__pycache__" or name.lower().endswith(".lnk")}
        if here == PROJECT_ROOT:
            left_out |= LEFT_OUT_IN_PROJECT_ROOT & set(names)
        if here == dont_change and "tmp" in names:
            left_out.add("tmp")
        return left_out

    shutil.copytree(PROJECT_ROOT, destination, ignore=ignore)


def app_id_for(copy_root: Path) -> str:
    """The argument the copy's shortcuts would pass (its per-copy taskbar identity)."""
    sys.path.insert(0, str(CODE_DIR))
    from backend.DONT_CHANGE.scripts.config import settings
    from backend.DONT_CHANGE.scripts.shortcuts import project_app_id

    return project_app_id(settings().program_name, str(copy_root))


def main_script_in(copy_root: Path) -> Path:
    """Where the copy's main file is (main_script_path in developer_settings.py)."""
    sys.path.insert(0, str(CODE_DIR))
    from backend.DONT_CHANGE.scripts.config import main_script_path

    return copy_root / "code" / Path(main_script_path()).relative_to(CODE_DIR)


def commands(copy_root: Path, app_id: str, script: Path) -> dict:
    code = copy_root / "code"
    entry_batches = code / "backend" / "DONT_CHANGE" / "B"
    return {
        "terminal": ["cmd.exe", "/d", "/c", "call", str(entry_batches / "W.bat"), app_id],
        "no_terminal": ["cmd.exe", "/d", "/c", "call", str(entry_batches / "N.bat"), app_id],
        "direct": [str(code / "backend" / "generated" / ".venv" / "Scripts" / "python.exe"), str(script)],
    }


def stop_tree(process: subprocess.Popen, wait_seconds: float) -> None:
    """Let the launch finish on its own, else end the whole process tree."""
    try:
        process.wait(wait_seconds)
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill.exe", "/T", "/F", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        process.wait()


def run_once(command: list, marker: Path, timeout: float, cwd: Path) -> float:
    """Seconds from starting the command until the probe wrote its marker."""
    if marker.exists():
        marker.unlink()
    start = time.perf_counter()
    process = subprocess.Popen(command, cwd=str(cwd), creationflags=subprocess.CREATE_NEW_CONSOLE)
    try:
        while not marker.exists():
            if time.perf_counter() - start > timeout:
                raise TimeoutError(f"main.py did not run within {timeout:g} s: {subprocess.list2cmdline(command)}")
            time.sleep(0.002)
        elapsed = time.perf_counter() - start
    finally:
        stop_tree(process, wait_seconds=15)
    time.sleep(0.3)  # let the watchdog and its records finish before the next start
    return elapsed


def main() -> int:
    if os.name != "nt":
        print("[Error] The launcher only runs on Windows.")
        return 2
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=60.0, help="seconds per launch (the warm-up gets 10x)")
    parser.add_argument("--targets", nargs="+", choices=TARGETS, default=list(TARGETS))
    parser.add_argument("--keep", action="store_true", help="keep the temporary project copy")
    arguments = parser.parse_args()
    if arguments.runs < 1:
        parser.error("--runs must be positive")

    STARTUP_BENCHMARK_WORK_DIR.mkdir(parents=True, exist_ok=True)
    copy_root = STARTUP_BENCHMARK_WORK_DIR / f"copy_{os.getpid()}"
    marker = STARTUP_BENCHMARK_WORK_DIR / f"marker_{os.getpid()}.txt"
    print(f"[Info] Copying {PROJECT_ROOT} to {copy_root} ...")
    copy_project(copy_root)
    script = main_script_in(copy_root)
    script.write_text(PROBE.format(marker=str(marker)), encoding="utf-8")
    all_commands = commands(copy_root, app_id_for(copy_root), script)

    results = {}
    try:
        for target in arguments.targets:
            command = all_commands[target]
            print(f"[Info] {target}: warm-up ...", flush=True)
            run_once(command, marker, arguments.timeout * 10, copy_root)
            results[target] = []
            for index in range(arguments.runs):
                results[target].append(run_once(command, marker, arguments.timeout, copy_root))
                print(f"  run {index + 1}: {results[target][-1] * 1000:7.0f} ms", flush=True)
    finally:
        if marker.exists():
            marker.unlink()
        if not arguments.keep:
            shutil.rmtree(copy_root, ignore_errors=True)

    print()
    print(f"{'target':<12} {'median':>8} {'min':>8} {'max':>8}   (ms, {arguments.runs} runs)")
    for target, values in results.items():
        print(
            f"{target:<12} {statistics.median(values) * 1000:8.0f} {min(values) * 1000:8.0f} {max(values) * 1000:8.0f}"
        )
    if "direct" in results:
        floor = statistics.median(results["direct"])
        for target in ("terminal", "no_terminal"):
            if target in results:
                print(
                    f"[Info] Launcher overhead ({target}): {(statistics.median(results[target]) - floor) * 1000:.0f} ms"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
