"""Run the launcher's regression tests (any Python 3.8+, standard library only).

Usage: run_regressions.py [pattern] [-q] [-j N]    e.g. run_regressions.py test_wrapper.py
"run_launcher_tests.cmd" in this folder runs this with the launcher's Python.

-j N runs the test files in N processes at once (-j 0: one per CPU). Each file gets its own
process, so tests that patch modules or start processes cannot affect each other; only the output
of failing files is shown, followed by the usual "Ran N tests" summary.
"""

import argparse
import os
import re
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Tuple

TESTS = Path(__file__).parent
# The browser terminal is a standalone package with its own tests; they run here too.
PACKAGE_TESTS = TESTS.parent / "browser_terminal" / "tests"
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("pattern", nargs="?", default="test_*.py", help="test file pattern, e.g. test_wrapper.py")
parser.add_argument("-q", "--quiet", action="store_true", help="one dot per test instead of one line")
parser.add_argument("-j", "--jobs", type=int, default=1, help="test files run at once (0: one per CPU)")
parser.add_argument("--folder", help=argparse.SUPPRESS)  # the folder of one file, for -j
args = parser.parse_args()
sys.path.insert(0, str(TESTS))
from project_location import PROJECT_ROOT


def run_file(path: Path) -> Tuple[Path, int, str]:
    """One test file in its own process: (file, exit code, output)."""
    # The test runner itself, with the same interpreter, on one of its own test files.
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-B", str(Path(__file__)), path.name, "-q", "--folder", str(path.parent)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    return path, completed.returncode, completed.stdout + completed.stderr


def run_in_parallel(files: List[Path], jobs: int) -> bool:
    start = time.monotonic()
    with ThreadPoolExecutor(jobs) as pool:
        results = list(pool.map(run_file, files))
    tests = 0
    failed: List[Path] = []
    for path, code, output in results:
        counted = re.search(r"^Ran (\d+) tests?", output, re.MULTILINE)
        tests += int(counted.group(1)) if counted else 0
        if code:
            failed.append(path)
            print(f"\n=== {path.name} ===\n{output.rstrip()}")
    # The same summary as unittest's, which other tools (test_all_pythons) read.
    print("-" * 70)
    print(f"Ran {tests} tests in {time.monotonic() - start:.3f}s\n")
    print(f"FAILED ({len(failed)} of {len(files)} files: {', '.join(p.name for p in failed)})" if failed else "OK")
    return not failed


print(f"Testing the launcher of {PROJECT_ROOT} with Python {sys.version.split()[0]}", flush=True)
folders = [Path(args.folder)] if args.folder else [TESTS, PACKAGE_TESTS]
files = [path for folder in folders for path in sorted(folder.glob(args.pattern))]
if args.jobs != 1 and len(files) > 1:
    raise SystemExit(not run_in_parallel(files, args.jobs or os.cpu_count() or 1))
suite = unittest.TestSuite(
    unittest.defaultTestLoader.discover(str(folder), pattern=args.pattern)
    for folder in folders
    if any(folder.glob(args.pattern))
)
result = unittest.TextTestRunner(verbosity=1 if args.quiet else 2).run(suite)
raise SystemExit(not result.wasSuccessful())
