"""Make the code folder importable ("pyapp.DONT_CHANGE...") for the tests in this folder.

The tests live in code/pyapp/DONT_CHANGE/tests and always test the checkout they are part of.
"""

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

DONT_CHANGE = Path(__file__).resolve().parents[1]
CODE = DONT_CHANGE.parents[1]
PROJECT_ROOT = CODE.parent
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

# Errors the launcher ignores on purpose go to a temporary log, never into the project's
# tmp/diagnostics.log (also for the launcher processes the tests start).
# Only the process that creates the folder removes it; the launcher processes a test starts inherit
# the variable and must not delete the folder under the test.
if "PYAPP_DIAGNOSTICS_LOG" not in os.environ:
    _diagnostics_folder = tempfile.mkdtemp(prefix="pyapp-tests-")
    atexit.register(shutil.rmtree, _diagnostics_folder, ignore_errors=True)
    os.environ["PYAPP_DIAGNOSTICS_LOG"] = str(Path(_diagnostics_folder) / "diagnostics.log")
