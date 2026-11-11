"""What must stay stable: the repository name in the Actions, and what existing projects expect in DONT_CHANGE."""

from __future__ import annotations

import re
import subprocess
import unittest
from typing import List, Optional

from project_location import CODE, DONT_CHANGE, PROJECT_ROOT

# isort: split

from pyapp.DONT_CHANGE.scripts import config
from pyapp.DONT_CHANGE.scripts.dev_tools import main as dev_tools

# Projects keep their own files outside DONT_CHANGE when they update by replacing that folder, so
# what those files use has to stay. Everything else in DONT_CHANGE is free to move between versions.
ENTRY_FILE = "run.bat"
RUN_COMMANDS = ("setup", "icons", "icons-help", "dev")
DEV_TOOL_COMMANDS = (
    "add",
    "remove",
    "upgrade",
    "sync",
    "find-imports",
    "terminal",
    "change-python",
    "update-python",
    "make-self-contained",
    "export",
    "clean",
    "remove-shortcuts",
    "status",
)
# Shortcuts made by Setup keep pointing at these until Setup runs again.
SHORTCUT_TARGETS = ("C.bat", "L.bat", "M.bat", "N.bat", "Q.bat", "S.bat", "T.bat", "W.bat")
# A setting that is renamed or removed silently stops working in existing developer_settings.py files.
SETTING_NAMES = (
    "args_for_main_py",
    "close_after_failure",
    "close_after_keyboard_interrupt",
    "close_after_success",
    "crash_log_path",
    "crash_log_path_is_relative_to_start_folder_if_relative",
    "desktop_shortcuts",
    "enable_crash_log",
    "enable_log_for_no_terminal_start",
    "enable_log_for_terminal_start",
    "environment_for_main_py",
    "error_date_format",
    "github_actions",
    "input_prepend",
    "instance_policy",
    "log_input_prepend",
    "log_path",
    "log_path_is_relative_to_start_folder_if_relative",
    "log_print_prepend",
    "main_script_path",
    "no_terminal_shortcut_name",
    "open_code_shortcut_name",
    "open_crash_log_after_failure",
    "open_crash_log_folder_shortcut_name",
    "open_log_file_after_failure",
    "open_log_file_after_keyboard_interrupt",
    "open_log_file_after_success",
    "open_log_folder_shortcut_name",
    "open_settings_shortcut_name",
    "packages",
    "play_sound_after_failure",
    "play_sound_after_success",
    "print_prepend",
    "program_name",
    "python_source",
    "python_version",
    "start_in_shortcut_folder",
    "start_menu_shortcuts",
    "start_minimized",
    "stop_running_shortcut_name",
    "stop_timeout_seconds",
    "tab_bar_color",
    "terminal_bg_color",
    "terminal_shortcut_name",
    "terminal_text_color",
    "use_classic_terminal",
    "use_system_certificates",
    "user_settings_path",
    "uv_cache",
    "uv_install_if_missing",
    "uv_prefer",
    "uv_user_python_visible_globally",
    "uv_version",
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
    settings = (CODE / "pyapp" / "developer_settings.py").read_text(encoding="utf-8")
    return re.search(r'(?m)^program_name = "PyApp-Template"', settings) is not None


def launcher_files_used_outside() -> List[str]:
    """What the scripts outside DONT_CHANGE refer to inside it."""
    scripts = list(PROJECT_ROOT.glob("*.cmd"))
    for folder in ("dev_tools", "icons"):
        scripts += (CODE / "pyapp" / folder).glob("*.cmd")
    found: List[str] = []
    for script in scripts:
        found += re.findall(r'DONT_CHANGE\\([^"\s]+)', script.read_text(encoding="utf-8"))
    return found


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


class ExistingProjectTests(unittest.TestCase):
    def test_the_entry_file_and_its_commands_exist(self):
        text = (DONT_CHANGE / ENTRY_FILE).read_text(encoding="utf-8")
        for command in RUN_COMMANDS:
            with self.subTest(command=command):
                self.assertIn(f'"%~1"=="{command}"', text)

    def test_scripts_outside_only_use_the_entry_file(self):
        used = launcher_files_used_outside()
        self.assertGreater(len(used), 10)
        self.assertEqual(set(used), {ENTRY_FILE})

    def test_dev_tool_commands_still_exist(self):
        self.assertLessEqual(set(DEV_TOOL_COMMANDS), set(dev_tools.COMMANDS))

    def test_shortcut_targets_still_exist(self):
        for name in SHORTCUT_TARGETS:
            with self.subTest(target=name):
                self.assertTrue((DONT_CHANGE / "B" / name).is_file())

    def test_setting_names_are_not_renamed_or_removed(self):
        defaults = config.default_setting_expressions(str(DONT_CHANGE / "data" / "dev_settings_default.py"))
        self.assertEqual(sorted(set(SETTING_NAMES) - set(defaults)), [])


if __name__ == "__main__":
    unittest.main()
