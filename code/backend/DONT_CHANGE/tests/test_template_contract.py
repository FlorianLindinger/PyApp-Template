"""What must stay stable: the repository name in the Actions, and what older projects expect in DONT_CHANGE."""

from __future__ import annotations

import importlib
import re
import subprocess
import unittest
from typing import List, Optional

from project_location import CODE, DONT_CHANGE, PROJECT_ROOT

# isort: split

from backend.DONT_CHANGE.scripts import dev_tools

# Projects keep their own files outside DONT_CHANGE when they update by replacing that folder. These
# are what the older copies of those files use, so moving or renaming one breaks existing apps.
PATHS_OLDER_PROJECTS_USE = (
    "bootstrap/run.bat",
    "scripts/dev_tools.py",
    "actions/setup.py",
    "actions/gen_icons.py",
    "data/icons/HOW_TO_CHANGE_ICONS.txt",
)
DEV_TOOL_COMMANDS_OLDER_PROJECTS_USE = (
    "add",
    "remove",
    "upgrade",
    "sync",
    "find-imports",
    "terminal",
    "change-python",
    "update-python",
    "make-portable",
    "export",
    "clean",
    "remove-shortcuts",
    "status",
)
WORKFLOW_FOLDER = PROJECT_ROOT / ".github" / "workflows"


def repository_name() -> Optional[str]:
    """The GitHub repository's name from the origin address, or None without one."""
    # Fixed Git command in this checkout.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(PROJECT_ROOT), "remote", "get-url", "origin"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(r"[/:]([^/:]+?)(?:\.git)?/?$", completed.stdout.strip())
    return match.group(1) if completed.returncode == 0 and match else None


def names_checked_by(text: str) -> List[str]:
    return re.findall(r"endsWith\(github\.repository,\s*'/([^']+)'\)", text)


def is_the_template_itself() -> bool:
    settings = (CODE / "backend" / "developer_settings.py").read_text(encoding="utf-8")
    return re.search(r'(?m)^program_name = "PyApp-Template"', settings) is not None


class RepositoryNameTests(unittest.TestCase):
    def test_the_actions_check_the_current_repository_name(self):
        """After renaming the repository they would be skipped, without any error."""
        workflows = sorted(WORKFLOW_FOLDER.glob("pyapp-template-*.yml"))
        name = repository_name()
        if not workflows or name is None or not is_the_template_itself():
            self.skipTest("only for a clone of the template that has its GitHub address")
        for workflow in workflows:
            checked = names_checked_by(workflow.read_text(encoding="utf-8"))
            with self.subTest(workflow=workflow.name):
                self.assertTrue(checked, "the workflow does not check the repository name")
                self.assertEqual({n.lower() for n in checked}, {name.lower()})

    def test_the_name_is_read_from_the_condition(self):
        self.assertEqual(names_checked_by("if: endsWith(github.repository, '/My-Repo')"), ["My-Repo"])


class OlderProjectTests(unittest.TestCase):
    def test_files_older_projects_start_still_exist(self):
        for relative in PATHS_OLDER_PROJECTS_USE:
            with self.subTest(path=relative):
                self.assertTrue((DONT_CHANGE / relative).is_file())

    def test_run_bat_still_takes_the_entry_script_from_the_same_variable(self):
        self.assertIn("PYAPP_ENTRY_SCRIPT", (DONT_CHANGE / "bootstrap" / "run.bat").read_text(encoding="utf-8"))

    def test_dev_tool_commands_still_exist(self):
        self.assertLessEqual(set(DEV_TOOL_COMMANDS_OLDER_PROJECTS_USE), set(dev_tools.COMMANDS))

    def test_the_editor_helper_older_settings_files_import_still_exists(self):
        console_tools = importlib.import_module("backend.DONT_CHANGE.scripts.console_tools")
        self.assertTrue(callable(console_tools.open_in_editor))


if __name__ == "__main__":
    unittest.main()
