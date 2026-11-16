"""What must stay stable: the repository name in the Actions, what existing projects expect in DONT_CHANGE.

What is protected is listed in backend_settings (PROTECTED_PATHS, PROTECTED_PROJECT_FILES,
PROTECTED_RUN_COMMANDS, PROTECTED_DEV_TOOL_COMMANDS, PROTECTED_SETTING_NAMES).
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from typing import List, Optional, Tuple
from unittest import mock

from project_location import CODE, DONT_CHANGE, PROJECT_ROOT

# isort: split

from pyapp.DONT_CHANGE import backend_settings
from pyapp.DONT_CHANGE.scripts import config
from pyapp.DONT_CHANGE.scripts.dev_tools import main as dev_tools

# What existing projects rely on is listed in backend_settings (PROTECTED_*); these tests check
# that the code still provides all of it, and that files outside DONT_CHANGE use nothing else.
ENTRY_FILE = "B/run.bat"
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


def scripts_outside() -> List[Path]:
    """The .cmd files of a project outside DONT_CHANGE (kept when DONT_CHANGE is replaced)."""
    scripts = list(PROJECT_ROOT.glob("*.cmd")) + list((CODE / "pyapp").glob("*.cmd"))
    for folder in ("dev_tools", "icons"):
        scripts += (CODE / "pyapp" / folder).rglob("*.cmd")
    return scripts


def launcher_files_used_outside() -> List[str]:
    """What the scripts outside DONT_CHANGE refer to inside it."""
    found: List[str] = []
    for script in scripts_outside():
        found += re.findall(r'DONT_CHANGE\\([^"\s]+)', script.read_text(encoding="utf-8"))
    return found


def run_commands_used_outside() -> List[Tuple[str, str]]:
    """(run.bat command, dev tool command or "") of every call to run.bat outside DONT_CHANGE."""
    found: List[Tuple[str, str]] = []
    for script in scripts_outside():
        found += re.findall(r'DONT_CHANGE\\B\\run\.bat"\s+([\w-]+)(?:\s+([\w-]+))?', script.read_text(encoding="utf-8"))
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


class ExistingProjectTests(unittest.TestCase):
    def test_the_entry_file_and_its_commands_exist(self):
        text = (DONT_CHANGE / ENTRY_FILE).read_text(encoding="utf-8")
        for command in backend_settings.PROTECTED_RUN_COMMANDS:
            with self.subTest(command=command):
                self.assertIn(f'"%~1"=="{command}"', text)

    def test_scripts_outside_use_only_protected_commands(self):
        used = run_commands_used_outside()
        self.assertGreater(len(used), 10)
        missing_run = sorted({command for command, _ in used} - set(backend_settings.PROTECTED_RUN_COMMANDS))
        missing_dev = sorted(
            {dev_command for command, dev_command in used if command == "dev"}
            - set(backend_settings.PROTECTED_DEV_TOOL_COMMANDS)
        )
        if missing_run:
            self.fail(
                "Launcher commands missing from PROTECTED_RUN_COMMANDS: "
                + ", ".join(missing_run)
                + ". Add these commands to backend_settings.py so existing project scripts remain supported."
            )
        if missing_dev:
            self.fail(
                "Developer Tools commands missing from PROTECTED_DEV_TOOL_COMMANDS: "
                + ", ".join(missing_dev)
                + ". Add these commands to backend_settings.py so existing project scripts remain supported."
            )

    def test_protected_dev_tool_commands_still_exist(self):
        # "menu" is not in COMMANDS: main() shows the menu itself (also without a command).
        known = {*dev_tools.COMMANDS, "menu"}
        self.assertLessEqual(set(backend_settings.PROTECTED_DEV_TOOL_COMMANDS), known)

    def test_protected_project_files_are_still_where_the_launcher_looks(self):
        from pyapp.DONT_CHANGE.actions import gen_icons

        # Every path the launcher uses: the constants of backend_settings, and the base image the
        # icon generator reads by name.
        used = {os.path.normcase(value) for value in vars(backend_settings).values() if isinstance(value, str)}
        used |= {os.path.normcase(str(Path(gen_icons.ICON_PNG_DIR) / gen_icons.ICON_GENERATION_SETTINGS[0][1]))}
        for relative in backend_settings.PROTECTED_PROJECT_FILES:
            with self.subTest(path=relative):
                path = os.path.normcase(str(Path(backend_settings.BACKEND_DIR) / relative))
                self.assertIn(path, used, f"no launcher path points at code/pyapp/{relative} any more")

    def test_nothing_protected_was_removed_since_the_last_release(self):
        """Removing a protected entry breaks existing projects: only a new MAJOR version may do it."""
        import json

        try:
            baseline = json.loads(Path(backend_settings.PROTECTED_BASELINE_PATH).read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.skipTest("no release has saved the protected lists yet")
        released_major = int(str(baseline["launcher_version"]).split(".")[0])
        current_major = int(backend_settings.LAUNCHER_VERSION.split(".")[0])
        if current_major > released_major:
            self.skipTest("a new MAJOR version may remove protected entries (describe the steps in CHANGELOG.md)")
        removed = {
            name: sorted(set(baseline.get(name, [])) - set(entries))
            for name, entries in backend_settings.PROTECTED.items()
            if set(baseline.get(name, [])) - set(entries)
        }
        if removed:
            # One readable sentence: its first line is what Git clients show when the commit is stopped.
            self.fail(
                f"taken off since launcher {baseline['launcher_version']}: "
                + "; ".join(f"{name} {', '.join(entries)}" for name, entries in removed.items())
                + ". Existing projects rely on them: keep them (and the file, command or setting itself), "
                "or raise the MAJOR version of LAUNCHER_VERSION and describe in CHANGELOG.md what projects have to change"
            )

    def test_protected_setting_names_still_exist(self):
        defaults = config.default_setting_expressions(backend_settings.DEFAULT_SETTINGS_PATH)
        self.assertEqual(sorted(set(backend_settings.PROTECTED_SETTING_NAMES) - set(defaults)), [])

    def test_scripts_outside_use_only_protected_paths(self):
        used = launcher_files_used_outside()
        self.assertGreater(len(used), 10)
        self.assertLessEqual(set(used), set(backend_settings.PROTECTED_PATHS))
        self.assertIn(backend_settings.FALLBACK_START_PATH, used)

    def test_every_protected_path_exists(self):
        for relative in backend_settings.PROTECTED_PATHS:
            with self.subTest(path=relative):
                self.assertTrue((DONT_CHANGE / relative.replace("\\", "/")).is_file())

    def test_every_shortcut_target_is_protected(self):
        # Existing shortcuts keep pointing at their target until Setup runs again.
        targets = [
            value
            for name, value in vars(backend_settings).items()
            if name.startswith("LAUNCHER_") and str(value).endswith(".bat")  # not LAUNCHER_VERSION
        ]
        self.assertGreaterEqual(len(targets), 8)
        for target in targets:
            with self.subTest(target=target):
                relative = str(Path(target).relative_to(backend_settings.DONT_CHANGE_DIR))
                self.assertIn(relative, backend_settings.PROTECTED_PATHS)

    def test_the_fallback_start_needs_nothing_else_from_the_launcher(self):
        path = DONT_CHANGE / backend_settings.FALLBACK_START_PATH.replace("\\", "/")
        imported = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add("." if node.level else (node.module or "").split(".")[0])
        # Only the standard library: no launcher module, nothing relative, no package of the app.
        stdlib = getattr(sys, "stdlib_module_names", None)  # Python 3.10+
        if stdlib is None:
            self.skipTest("sys.stdlib_module_names needs Python 3.10")
        self.assertEqual(sorted(imported - set(stdlib) - {"__future__"}), [])


class ContractMessageTests(unittest.TestCase):
    def test_missing_commands_are_named_without_dumping_the_protected_list(self):
        case = ExistingProjectTests("test_scripts_outside_use_only_protected_commands")
        used = [("dev", "install-requirements"), ("dev", "reset-imports")] * 6
        with mock.patch(__name__ + ".run_commands_used_outside", return_value=used), mock.patch.object(
            backend_settings, "PROTECTED_DEV_TOOL_COMMANDS", ["menu", "add"]
        ), self.assertRaises(AssertionError) as raised:
            case.test_scripts_outside_use_only_protected_commands()
        self.assertEqual(
            str(raised.exception).split(". ")[0],
            "Developer Tools commands missing from PROTECTED_DEV_TOOL_COMMANDS: install-requirements, reset-imports",
        )
        self.assertNotIn("['menu'", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
