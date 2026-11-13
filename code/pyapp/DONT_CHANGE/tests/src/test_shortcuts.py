"""scripts/shortcuts.py: shortcut names, order, targets, taskbar identity, and removing them."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import List
from unittest import mock

from project_location import CODE  # noqa: F401 - makes "pyapp" importable

# isort: split

from pyapp.DONT_CHANGE.scripts import shortcuts
from pyapp.DONT_CHANGE.scripts.dev_tools import housekeeping


class ShortcutTests(unittest.TestCase):
    def test_taskbar_identity_is_per_project_folder(self):
        first = shortcuts.project_app_id("PyApp-Template", "D:/A")
        self.assertEqual(first, shortcuts.project_app_id("PyApp-Template", "D:/A"))
        self.assertNotEqual(first, shortcuts.project_app_id("PyApp-Template", "D:/B"))
        self.assertTrue(first.startswith("pyapp-template."))
        self.assertTrue(shortcuts.project_app_id("名前", "D:/A").startswith("pyapp."))
        self.assertLessEqual(len(shortcuts.project_app_id("x" * 300, "D:/A")), 128)

    def test_shortcut_file_names(self):
        self.assertEqual(shortcuts.shortcut_filename("My App"), "My App.lnk")
        cleaned = shortcuts.shortcut_filename('a<b>c:"d/e')
        self.assertTrue(cleaned.endswith(".lnk"))
        self.assertFalse(set('<>:"/') & set(cleaned))
        long_a, long_b = shortcuts.shortcut_filename("x" * 300 + "a"), shortcuts.shortcut_filename("x" * 300 + "b")
        self.assertNotEqual(long_a, long_b)
        self.assertLessEqual(len(long_a), 255)

    @unittest.skipUnless(os.name == "nt", "Windows only")
    def test_shortcuts_are_made_in_their_listed_order(self):
        names = (
            "terminal_shortcut_name",
            "no_terminal_shortcut_name",
            "browser_terminal_shortcut_name",
            "open_settings_shortcut_name",
            "stop_running_shortcut_name",
            "open_log_folder_shortcut_name",
            "open_crash_log_folder_shortcut_name",
            "open_code_shortcut_name",
        )
        s = SimpleNamespace(program_name="App", user_settings_path="settings.py", **{n: n for n in names})
        targets = {"logs": "", "crash_logs": "", "open_code": "", "settings": ""}
        kinds = [d[0] for d in shortcuts.shortcut_definitions(s, "app", targets)]
        expected = [
            "terminal",
            "no_terminal",
            "browser_terminal",
            "settings",
            "stop",
            "logs",
            "crash_logs",
            "open_code",
        ]
        self.assertEqual(kinds, expected)
        # Without a settings file there is no settings shortcut, whatever its name.
        s.user_settings_path = ""
        kinds = [d[0] for d in shortcuts.shortcut_definitions(s, "app", targets)]
        self.assertEqual(kinds, [k for k in expected if k != "settings"])

    def test_outdated_targets_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            record = str(Path(folder) / "created.json")
            Path(record).write_text(
                json.dumps({"version": 2, "shortcuts": [], "targets": {"logs": "D:/old"}}), encoding="utf-8"
            )
            targets = {"logs": "D:/new", "open_code": "D:/m.py"}
            with mock.patch.object(shortcuts, "CREATED_SHORTCUTS_LIST_PATH", record), mock.patch.object(
                shortcuts, "shortcut_targets", return_value=targets
            ):
                self.assertEqual(shortcuts.outdated_shortcut_targets(mock.Mock()), ["logs"])


class RemoveShortcutsTests(unittest.TestCase):
    def test_shortcuts_that_could_not_be_removed_stay_recorded(self):
        written: List[List[str]] = []

        def record(paths: List[str], *_arguments: object) -> None:
            written.append(list(paths))

        with mock.patch.object(shortcuts, "read_created_shortcuts", return_value=["a.lnk", "b.lnk"]), mock.patch.object(
            shortcuts, "remove_shortcuts", return_value=["a.lnk"]
        ), mock.patch.object(shortcuts, "is_generated_shortcut", return_value=True), mock.patch.object(
            shortcuts, "write_created_shortcuts", side_effect=record
        ), contextlib.redirect_stdout(io.StringIO()):
            housekeeping.cmd_remove_shortcuts([])
        self.assertEqual(written, [["b.lnk"]])


if __name__ == "__main__":
    unittest.main()
