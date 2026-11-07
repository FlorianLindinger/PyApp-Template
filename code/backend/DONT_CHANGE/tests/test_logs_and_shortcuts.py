"""Log paths and retention, the diagnostics log, and shortcut names, targets and taskbar identity."""

import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from project_location import CODE  # noqa: F401 - makes "backend" importable

# isort: split

from backend.DONT_CHANGE.scripts import diagnostics, launcher_ui, runtime_state, shortcuts


class LogTests(unittest.TestCase):
    def test_retention_counts_runs_with_their_output_logs(self):
        with tempfile.TemporaryDirectory() as folder:
            for index in range(5):
                for name in (f"log_{index}.txt", f"log_{index}.txt.output.log"):
                    path = os.path.join(folder, name)
                    Path(path).write_text("x", encoding="utf-8")
                    os.utime(path, (1000 + index, 1000 + index))
            settings = types.SimpleNamespace(
                log_path=os.path.join(folder, "log_%Y.txt"),
                log_path_is_relative_to_start_folder_if_relative=False,
                crash_log_path=None,
                crash_log_path_is_relative_to_start_folder_if_relative=False,
                max_log_files=2,
                max_run_folder_age_days=None,
            )
            launcher_ui.prune_logs(settings)
            self.assertEqual(
                sorted(os.listdir(folder)), ["log_3.txt", "log_3.txt.output.log", "log_4.txt", "log_4.txt.output.log"]
            )

    def test_log_path_resolution(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(
                launcher_ui.get_log_path(os.path.join(folder, "a.txt"), False),
                os.path.normpath(os.path.join(folder, "a.txt")),
            )
            with mock.patch.dict(os.environ, {"PYAPP_START_DIR": folder}):
                self.assertEqual(
                    launcher_ui.get_log_path("logs/a.txt", True), os.path.normpath(os.path.join(folder, "logs/a.txt"))
                )
        self.assertEqual(launcher_ui.get_log_path(None, False), "")
        self.assertNotIn("%", launcher_ui.get_log_path(os.path.abspath("log_%Y.txt"), False))

    def test_unique_log_names(self):
        first = runtime_state.unique_log_path("C:/logs/log.txt")
        second = runtime_state.unique_log_path("C:/logs/log.txt")
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith(".txt"))
        self.assertEqual(runtime_state.unique_log_path(""), "")

    def test_ignored_errors_are_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            log = os.path.join(folder, "diagnostics.log")
            with mock.patch.object(diagnostics, "DIAGNOSTICS_LOG_PATH", log):
                try:
                    raise ZeroDivisionError("test")
                except ZeroDivisionError:
                    diagnostics.note_ignored("unit test step")
                summary = diagnostics.diagnostics_summary()
            self.assertIn("1 ignored error", summary or "")
            self.assertIn("ZeroDivisionError", Path(log).read_text(encoding="utf-8"))


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

    def test_outdated_targets_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            record = os.path.join(folder, "created.json")
            Path(record).write_text(
                json.dumps({"version": 2, "shortcuts": [], "targets": {"logs": "D:/old"}}), encoding="utf-8"
            )
            targets = {"logs": "D:/new", "main_py": "D:/m.py"}
            with mock.patch.object(shortcuts, "CREATED_SHORTCUTS_LIST_PATH", record):
                with mock.patch.object(shortcuts, "shortcut_targets", return_value=targets):
                    self.assertEqual(shortcuts.outdated_shortcut_targets(object()), ["logs"])


if __name__ == "__main__":
    unittest.main()
