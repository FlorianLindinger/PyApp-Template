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

Usage: python get_startup_time.py [--runs 5] [--timeout 60] [--targets terminal direct] [--keep]
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
from typing import TYPE_CHECKING, Dict, List, Set

import _ui
from _paths import CODE_DIR, PROJECT_ROOT, STARTUP_BENCHMARK_WORK_DIR

# Popen became subscriptable in 3.9; runtime inspection on 3.8 uses the public class.
if TYPE_CHECKING:
    BinaryProcess = subprocess.Popen[bytes]
else:
    BinaryProcess = subprocess.Popen

TARGETS = ("terminal", "no_terminal", "direct")
LEFT_OUT_IN_PROJECT_ROOT = {"logs", "crash logs", ".git"}
PROBE = """import os
with open({marker!r}, "w") as marker:
    marker.write(str(os.getpid()))
"""


def copy_project(destination: Path) -> None:
    """Copy the project without logs, shortcuts, caches and the launcher's runtime state."""
    dont_change = PROJECT_ROOT / "code" / "pyapp" / "DONT_CHANGE"

    def ignore(folder: str, names: List[str]) -> Set[str]:
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
    from pyapp.DONT_CHANGE.scripts.config import settings
    from pyapp.DONT_CHANGE.scripts.shortcuts import project_app_id

    return project_app_id(settings().program_name, str(copy_root))


def main_script_in(copy_root: Path) -> Path:
    """Where the copy's main file is (main_script_path in developer_settings.py)."""
    sys.path.insert(0, str(CODE_DIR))
    from pyapp.DONT_CHANGE.scripts.config import main_script_path

    return copy_root / "code" / Path(main_script_path()).relative_to(CODE_DIR)


def commands(copy_root: Path, app_id: str, script: Path) -> Dict[str, List[str]]:
    code = copy_root / "code"
    entry_batches = code / "pyapp" / "DONT_CHANGE" / "B"
    return {
        "terminal": ["cmd.exe", "/d", "/c", "call", str(entry_batches / "W.bat"), app_id],
        "no_terminal": ["cmd.exe", "/d", "/c", "call", str(entry_batches / "N.bat"), app_id],
        "direct": [str(code / "pyapp" / "generated" / ".venv" / "Scripts" / "python.exe"), str(script)],
    }


def stop_tree(process: BinaryProcess, wait_seconds: float) -> None:
    """Let the launch finish on its own, else end the whole process tree."""
    try:
        process.wait(wait_seconds)
    except subprocess.TimeoutExpired:
        # Run the benchmark command or terminate only its recorded child PID.
        subprocess.run(  # noqa: S603
            # Run the benchmark command or terminate only its recorded child PID.
            ["taskkill.exe", "/T", "/F", "/PID", str(process.pid)],  # noqa: S607
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        process.wait()


def run_once(command: List[str], marker: Path, timeout: float, cwd: Path) -> float:
    """Seconds from starting the command until the probe wrote its marker."""
    if marker.exists():
        marker.unlink()
    start = time.perf_counter()
    # Run the benchmark command or terminate only its recorded child PID.
    process = subprocess.Popen(command, cwd=str(cwd), creationflags=subprocess.CREATE_NEW_CONSOLE)  # noqa: S603
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
        _ui.error("The launcher only runs on Windows.")
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
    _ui.heading("Launcher start-up time")
    _ui.fields([("Project", PROJECT_ROOT), ("Temporary copy", copy_root), ("Runs", f"{arguments.runs} per target")])
    _ui.step("Copying the project ...")
    copy_project(copy_root)
    script = main_script_in(copy_root)
    script.write_text(PROBE.format(marker=str(marker)), encoding="utf-8")
    all_commands = commands(copy_root, app_id_for(copy_root), script)

    results: Dict[str, List[float]] = {}
    try:
        for target in arguments.targets:
            command = all_commands[target]
            _ui.step(f"{target}: warming up ...")
            run_once(command, marker, arguments.timeout * 10, copy_root)
            results[target] = []
            for index in range(arguments.runs):
                results[target].append(run_once(command, marker, arguments.timeout, copy_root))
                _ui.progress(f"{target}: run {index + 1}/{arguments.runs}: {results[target][-1] * 1000:.0f} ms")
    finally:
        if marker.exists():
            marker.unlink()
        if not arguments.keep:
            shutil.rmtree(copy_root, ignore_errors=True)

    _ui.heading(f"Until main.py runs (ms, {arguments.runs} run{'s' if arguments.runs > 1 else ''})")
    _ui.table(
        ("median", "min", "max", "target"),
        [
            (
                f"{statistics.median(values) * 1000:.0f}",
                f"{min(values) * 1000:.0f}",
                f"{max(values) * 1000:.0f}",
                target,
            )
            for target, values in results.items()
        ],
    )
    if "direct" in results:
        floor = statistics.median(results["direct"])
        overheads = [
            (target, f"{(statistics.median(results[target]) - floor) * 1000:.0f} ms")
            for target in ("terminal", "no_terminal")
            if target in results
        ]
        if overheads:
            _ui.heading("Launcher overhead (compared with direct)")
            _ui.fields(overheads)
    return 0


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
