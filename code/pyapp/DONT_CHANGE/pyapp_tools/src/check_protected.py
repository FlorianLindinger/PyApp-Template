"""What existing projects rely on, before each commit (git_hooks/pre-commit).

Runs tests/src/test_template_contract.py (well under a second) when the staged changes touch
code/pyapp: the lists in backend_settings (PROTECTED_*) must still match the code, and nothing
may be taken off them before a new MAJOR version. The hook runs this in an isolated staged
checkout; direct invocation checks the working files.

Usage: check_protected.py   (exit code 1: something existing projects rely on would break)
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import List

import _ui
from _paths import DONT_CHANGE_DIR, PROJECT_ROOT
from check_all import with_links

TEST_FILE = "test_template_contract.py"
RUNNER = DONT_CHANGE_DIR / "tests" / "src" / "run_regressions.py"


def staged_paths() -> List[str]:
    # A fixed Git command in the project folder.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(PROJECT_ROOT), "diff", "--cached", "--name-only", "-z"],  # noqa: S607
        capture_output=True,
        check=False,
    )
    return [name for name in completed.stdout.decode("utf-8", "replace").split("\0") if name]


def first_problem(output: str) -> str:
    """The first failure's message (else its test's name), for the one line Git clients show."""
    message = re.search(r"^\w*(?:Error|Exception): (.+)$", output, re.MULTILINE)
    if message:
        first = message.group(1).split(". ")[0]
        if first.startswith("Developer Tools commands missing from PROTECTED_DEV_TOOL_COMMANDS: "):
            return first.replace(
                "Developer Tools commands missing from PROTECTED_DEV_TOOL_COMMANDS: ",
                "Unregistered Developer Tools commands: ",
                1,
            )
        if re.search(r"not found in \[|Lists differ:|Items in the .* set", first):
            test = re.search(r"^(?:FAIL|ERROR): (\w+)", output, re.MULTILINE)
            name = test.group(1) if test else ""
            descriptions = {
                "test_protected_setting_names_still_exist": "Protected developer settings are missing from fallback defaults",
                "test_protected_dev_tool_commands_still_exist": "Protected Developer Tools commands are missing",
                "test_scripts_outside_use_only_protected_commands": "Project scripts use unregistered launcher commands",
                "test_scripts_outside_use_only_protected_paths": "Project scripts reference unprotected launcher paths",
                "test_the_entry_file_and_its_commands_exist": "run.bat is missing protected commands",
                "test_protected_project_files_are_still_where_the_launcher_looks": "Protected project files no longer match launcher paths",
            }
            return descriptions.get(
                name, name.replace("test_", "", 1).replace("_", " ") or "protected files/settings do not match"
            )
        return first[:200]  # the first sentence: the rest is in the details
    test = re.search(r"^(?:FAIL|ERROR): (\w+)", output, re.MULTILINE)
    return test.group(1).replace("test_", "", 1).replace("_", " ") if test else "the contract test failed"


def main() -> int:
    if not any(name.startswith("code/pyapp/") for name in staged_paths()):
        return 0  # nothing of the launcher or the project files it relies on is being committed
    if not RUNNER.is_file():
        return 0  # a project without the launcher's tests
    # This Python runs this checkout's own test runner on one fixed test file.
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-B", "-X", "utf8", str(RUNNER), TEST_FILE, "-q"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode == 0:
        return 0  # silent: this runs on every commit
    output = "\n".join(completed.stdout.decode("utf-8", "replace").splitlines()).strip()
    _ui.info(
        f"Commit blocked: Launcher compatibility check failed: {first_problem(output)}. "
        'Update backend_settings.py or restore the reported files/settings. Click "Show Command Output" for details.'
    )
    _ui.heading(f"Output of {TEST_FILE}")
    _ui.info(with_links(output))
    _ui.heading("How to fix")
    _ui.info(
        "1. Check the protected files/settings named above (backend_settings.py: PROTECTED_*).\n"
        "2. Register new commands in the corresponding protected list; restore accidental removals.\n"
        "   Removing a protected entry requires a new MAJOR version and migration steps in CHANGELOG.md.\n"
        "3. Review and stage the corrections, then commit again.\n"
        "This check reads working files, including unstaged edits."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(
        _ui.run(main, "Commit blocked: Compatibility check could not complete. Check Python/Git availability.")
    )
