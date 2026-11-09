"""Run the launcher's regression tests (any Python 3.8+, standard library only).

Usage: run_regressions.py [pattern]    e.g. run_regressions.py test_wrapper.py
"run_launcher_tests.cmd" in this folder runs this with the launcher's Python.
"""

import argparse
import sys
import unittest
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("pattern", nargs="?", default="test_*.py", help="test file pattern, e.g. test_wrapper.py")
parser.add_argument("-q", "--quiet", action="store_true", help="one dot per test instead of one line")
args = parser.parse_args()
sys.path.insert(0, str(Path(__file__).parent))
from project_location import PROJECT_ROOT

print(f"Testing the launcher of {PROJECT_ROOT} with Python {sys.version.split()[0]}", flush=True)
suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern=args.pattern)
result = unittest.TextTestRunner(verbosity=1 if args.quiet else 2).run(suite)
raise SystemExit(not result.wasSuccessful())
