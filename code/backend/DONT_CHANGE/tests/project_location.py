"""Make the code folder importable ("backend.DONT_CHANGE...") for the tests in this folder.

The tests live in code/backend/DONT_CHANGE/tests and always test the checkout they are part of.
"""

import os
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
os.environ["PYAPP_DIAGNOSTICS_LOG"] = os.path.join(tempfile.mkdtemp(prefix="pyapp-tests-"), "diagnostics.log")
