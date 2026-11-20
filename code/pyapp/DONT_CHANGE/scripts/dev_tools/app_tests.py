"""Dev tool run-tests: the app's own tests, with the app's environment.

Looks for a "tests" folder in code/pyapp (where the template keeps an example) and in the code
folder (code/tests), never in DONT_CHANGE: the launcher's tests are run by DONT_CHANGE/tests/run_launcher_tests.cmd.
pytest runs them if the app has it among its packages, else Python's own unittest (test_*.py
files with unittest.TestCase classes). They run from the code folder, so the tests import the
app's modules as main.py does.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Sequence

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.config import display_path, settings
from pyapp.DONT_CHANGE.scripts.console_tools import print_fields, print_heading, print_info, print_success
from pyapp.DONT_CHANGE.scripts.dev_tools.common import prepare
from pyapp.DONT_CHANGE.scripts.errors import SetupError

# Where an app keeps its tests, in this order.
TEST_FOLDERS = (Path(paths.PYTHON_SCRIPTS_DIR) / "tests",)  # code/tests


def test_folders(candidates: Sequence[Path] = TEST_FOLDERS) -> List[Path]:
    """The existing tests folders that hold at least one Python file."""
    return [folder for folder in candidates if folder.is_dir() and any(folder.rglob("*.py"))]


def has_pytest(python: str) -> bool:
    # The app's own interpreter, asked whether pytest is installed in its environment.
    return subprocess.run([python, "-c", "import pytest"], capture_output=True, check=False).returncode == 0  # noqa: S603


def test_commands(
    python: str, flags: Sequence[str], folders: Sequence[Path], pytest: bool, extra: Sequence[str]
) -> List[List[str]]:
    """One command for pytest (all folders at once), or one unittest discovery per folder."""
    if pytest:
        return [[python, *flags, "-m", "pytest", *(str(folder) for folder in folders), *extra]]
    # Each folder is its own top-level directory, so it needs no __init__.py; the code folder is
    # the working directory and therefore on sys.path, for imports of the app's modules.
    return [
        [python, *flags, "-m", "unittest", "discover", "-s", str(folder), "-t", str(folder), *extra]
        for folder in folders
    ]


def cmd_run_tests(arguments: List[str]) -> None:
    """Run the app's tests; arguments go to pytest or unittest (e.g. -k name, -v)."""
    print_heading("App tests")
    folders = test_folders()
    if not folders:
        print_info(
            "No tests found. Put files named test_*.py into code/tests: plain\n"
            "unittest.TestCase classes work as they are, or add pytest with add_packages for its style."
        )
        return
    app_python = prepare(settings())
    pytest = has_pytest(app_python.exe)
    print_fields(
        [
            ("Folders", ", ".join(display_path(str(folder)) for folder in folders)),
            ("Runner", "pytest" if pytest else "unittest (add pytest with add_packages to use pytest)"),
            ("Python", display_path(app_python.exe)),
        ]
    )
    print()
    codes = [
        # The app's interpreter runs its test runner on the app's own test folders.
        subprocess.run(command, cwd=paths.PYTHON_SCRIPTS_DIR, check=False).returncode  # noqa: S603
        for command in test_commands(app_python.exe, app_python.flags, folders, pytest, arguments)
    ]
    print()
    outcome = summary(codes)
    if outcome == "failed":
        raise SetupError("Some app tests failed (see above).")
    if outcome == "none":
        print_info(NO_TESTS_HINT)
        return
    print_success("All app tests passed.")


# pytest, and unittest from Python 3.12 on, end with this code when they found no test at all.
NO_TESTS_RAN = 5
NO_TESTS_HINT = (
    "No tests ran: the tests folder has no test yet. Name test files test_*.py and put\n"
    "unittest.TestCase classes (or pytest functions) in them; see code/tests/test_example.py."
)


def summary(codes: Sequence[int]) -> str:
    """ "passed", "failed", or "none" when no runner found a single test (not counted as a failure)."""
    if any(code not in (0, NO_TESTS_RAN) for code in codes):
        return "failed"
    return "none" if codes and all(code == NO_TESTS_RAN for code in codes) else "passed"
