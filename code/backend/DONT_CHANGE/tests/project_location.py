"""Make the code folder importable ("backend.DONT_CHANGE...") for the tests in this folder.

The tests live in code/backend/DONT_CHANGE/tests and always test the checkout they are part of.
"""

import sys
from pathlib import Path

DONT_CHANGE = Path(__file__).resolve().parents[1]
CODE = DONT_CHANGE.parents[1]
PROJECT_ROOT = CODE.parent
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
