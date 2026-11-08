"""Measure what importing modules adds to a fresh interpreter start.

    python get_import_times.py launcher             the launcher's own modules (launcher Python, -I -S)
    python get_import_times.py app numpy pandas     packages in the app's .venv
    python get_import_times.py app                  every package in developer_settings.py "packages"

Each module is imported in a new process; the median start-up of an empty interpreter is
subtracted. For a breakdown of one import use: python -X importtime -c "import numpy".
"""

from __future__ import annotations

import argparse
import statistics
import subprocess
import sys
import time
from typing import List

from _paths import CODE_DIR, VENV_PYTHON

LAUNCHER_MODULES = (
    "backend.DONT_CHANGE.backend_settings",
    "backend.DONT_CHANGE.scripts.entrypoint",
    "backend.DONT_CHANGE.scripts.config",
    "backend.DONT_CHANGE.actions.start_program",
    "backend.DONT_CHANGE.runtime.bg_watchdog",
    "backend.DONT_CHANGE.runtime.process_exit",
)
IMPORT = "import importlib, sys; sys.path.insert(0, sys.argv[1]); sys.argv[2] and importlib.import_module(sys.argv[2])"


def run_once(python: List[str], module: str) -> float:
    start = time.perf_counter()
    # Run the selected local interpreter; module names are arguments to fixed source.
    result = subprocess.run(  # noqa: S603
        [*python, "-c", IMPORT, str(CODE_DIR), module],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    elapsed = (time.perf_counter() - start) * 1000
    if result.returncode:
        raise RuntimeError(f"Importing {module} failed:\n{result.stdout}")
    return elapsed


def app_modules() -> List[str]:
    """Top-level import names of the declared packages, read from the installed metadata in .venv."""
    sys.path.insert(0, str(CODE_DIR))
    from backend.DONT_CHANGE.scripts.config import settings
    from backend.DONT_CHANGE.scripts.dev.common import normalized, requirement_name
    from backend.DONT_CHANGE.scripts.import_finder import installed_import_map

    declared = {requirement_name(requirement) for requirement in settings().packages}
    return sorted(
        name
        for name, distribution in installed_import_map().items()
        if normalized(distribution) in declared and not name.startswith("_")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("interpreter", choices=("launcher", "app"))
    parser.add_argument("modules", nargs="*")
    parser.add_argument("--runs", type=int, default=10)
    arguments = parser.parse_args()
    if arguments.interpreter == "launcher":
        python = [sys.executable, "-I", "-S"]
        modules = arguments.modules or list(LAUNCHER_MODULES)
    else:
        if not VENV_PYTHON.is_file():
            print(f"[Error] {VENV_PYTHON} does not exist yet. Start the app once first.")
            return 2
        python = [str(VENV_PYTHON)]
        modules = arguments.modules or app_modules()

    baseline = statistics.median(run_once(python, "") for _ in range(arguments.runs))
    print(f"Interpreter: {' '.join(python)}")
    print(f"Empty interpreter start, median of {arguments.runs}: {baseline:.1f} ms")
    print(f"{'median':>8} {'mean':>8}  module (ms added by the import)")
    for module in modules:
        values = [run_once(python, module) for _ in range(arguments.runs)]
        print(f"{statistics.median(values) - baseline:8.1f} {statistics.mean(values) - baseline:8.1f}  {module}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
