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

import _ui
from _paths import CODE_DIR, VENV_PYTHON

LAUNCHER_MODULES = (
    "pyapp.DONT_CHANGE.backend_settings",
    "pyapp.DONT_CHANGE.scripts.entrypoint",
    "pyapp.DONT_CHANGE.scripts.config",
    "pyapp.DONT_CHANGE.actions.start_program",
    "pyapp.DONT_CHANGE.runtime.bg_watchdog",
    "pyapp.DONT_CHANGE.runtime.process_exit",
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
    from pyapp.DONT_CHANGE.scripts.config import all_packages, settings
    from pyapp.DONT_CHANGE.scripts.dev_tools.common import normalized, requirement_name
    from pyapp.DONT_CHANGE.scripts.import_finder import installed_import_map

    declared = {requirement_name(requirement) for requirement in all_packages(settings())}
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
    if arguments.runs < 1:
        parser.error("--runs must be positive")
    if arguments.interpreter == "launcher":
        python = [sys.executable, "-I", "-S"]
        modules = arguments.modules or list(LAUNCHER_MODULES)
    else:
        if not VENV_PYTHON.is_file():
            _ui.error(f"{VENV_PYTHON} does not exist yet. Start the app once first.")
            return 2
        python = [str(VENV_PYTHON)]
        modules = arguments.modules or app_modules()

    if not modules:
        _ui.info("There is nothing to measure: no modules were named and no packages are declared.")
        return 0

    _ui.heading(f"Import times: {arguments.interpreter}")
    _ui.fields([("Interpreter", " ".join(python)), ("Runs", f"{arguments.runs} per module")])
    _ui.step("Measuring an empty interpreter start ...")
    baseline = statistics.median(run_once(python, "") for _ in range(arguments.runs))
    _ui.fields([("Empty start", f"{baseline:.1f} ms (median)")])
    rows = []
    failed = []
    for index, module in enumerate(modules, 1):
        _ui.progress(f"{index}/{len(modules)}  {module}")
        try:
            values = [run_once(python, module) for _ in range(arguments.runs)]
        except RuntimeError as error:
            failed.append(f"{module}: {str(error).strip().splitlines()[-1]}")
            continue
        rows.append((statistics.median(values) - baseline, statistics.mean(values) - baseline, module))
    if rows:
        _ui.heading("Added by each import (ms, slowest first)")
        _ui.table(
            ("median", "mean", "module"),
            [(f"{median:.1f}", f"{mean:.1f}", module) for median, mean, module in sorted(rows, reverse=True)],
        )
    if failed:
        _ui.blank_line()
        _ui.error("Could not be imported:\n" + "\n".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
