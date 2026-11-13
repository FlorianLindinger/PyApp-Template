"""Run the launcher's regression tests (any Python 3.8+, standard library only).

Usage: run_regressions.py [group | file pattern ...] [-q] [-j N] [--list]
    run_regressions.py                   every test
    run_regressions.py browser           one group (see --list; defined in groups.py)
    run_regressions.py setup git         several groups
    run_regressions.py test_wrapper.py   one file, or a pattern such as "test_git*.py"
"run_launcher_tests.cmd" in the tests folder runs this with the launcher's Python, "run_<group>_tests.cmd" one group.

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
from typing import Dict, List, Tuple

TESTS = Path(__file__).parent
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("names", nargs="*", metavar="group|pattern", help="groups or test file patterns (default: all)")
parser.add_argument("-q", "--quiet", action="store_true", help="one dot per test instead of one line")
parser.add_argument("-j", "--jobs", type=int, default=1, help="test files run at once (0: one per CPU)")
parser.add_argument("--list", action="store_true", help="show the groups and their files, then stop")
parser.add_argument("--folder", help=argparse.SUPPRESS)  # the folder of one file, for -j
args = parser.parse_args()
sys.path.insert(0, str(TESTS))
from groups import FOLDERS, GROUPS, all_test_files, group_files
from project_location import PROJECT_ROOT


def selected_files() -> List[Path]:
    """The test files the arguments name, each once, in the order they were named."""
    if args.folder:  # a child process of -j: one file of one folder
        return [path for name in args.names for path in sorted(Path(args.folder).glob(name))]
    if not args.names:
        return all_test_files()
    chosen: Dict[Path, None] = {}  # an ordered set
    for name in args.names:
        paths = (
            group_files(name) if name in GROUPS else [path for folder in FOLDERS for path in sorted(folder.glob(name))]
        )
        if not paths:
            raise SystemExit(f"No group or test file matches {name!r}. Groups: {', '.join(GROUPS)}")
        chosen.update(dict.fromkeys(paths))
    return list(chosen)


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


if args.list:
    for group, names in GROUPS.items():
        print(f"{group:<10}{', '.join(names)}")
    raise SystemExit(0)
files = selected_files()
print(f"Testing the launcher of {PROJECT_ROOT} with Python {sys.version.split()[0]}", flush=True)
if args.jobs != 1 and len(files) > 1:
    raise SystemExit(not run_in_parallel(files, args.jobs or os.cpu_count() or 1))
# One discovery per file: a selection may mix files of both folders. A new loader each time:
# before Python 3.9, a loader keeps the first top-level folder and refuses the other folder.
suite = unittest.TestSuite(unittest.TestLoader().discover(str(path.parent), pattern=path.name) for path in files)
result = unittest.TextTestRunner(verbosity=1 if args.quiet else 2).run(suite)
raise SystemExit(not result.wasSuccessful())
