"""Log paths, the diagnostics log, and shortcut names, targets and taskbar identity."""

import contextlib
import io
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
from backend.DONT_CHANGE.scripts.dev import housekeeping


class LogTests(unittest.TestCase):
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


class FinishedRunFolderTests(unittest.TestCase):
    def cleanup(self, running):
        """Run the cleanup on one old and one recent run folder; return which ones still exist."""
        with tempfile.TemporaryDirectory() as folder:
            old, recent = Path(folder, "old"), Path(folder, "recent")
            old.mkdir()
            recent.mkdir()
            Path(old, "result.json").touch()
            os.utime(old, (1, 1))
            registry = mock.Mock()
            registry.records.return_value = (running, 0)
            patch_folder = mock.patch.object(launcher_ui, "RUNS_DIR", folder)
            with patch_folder, mock.patch.object(runtime_state, "ProcessRegistry", return_value=registry):
                launcher_ui.delete_finished_run_folders()
            return old.exists(), recent.exists()

    def test_old_folders_are_deleted_and_recent_ones_kept(self):
        self.assertEqual(self.cleanup([]), (False, True))

    def test_nothing_is_deleted_while_an_instance_runs(self):
        self.assertEqual(self.cleanup([{"pid": 1}]), (True, True))

    def test_a_missing_runs_folder_is_fine(self):
        with mock.patch.object(launcher_ui, "RUNS_DIR", os.path.join(tempfile.gettempdir(), "pyapp-no-such-folder")):
            launcher_ui.delete_finished_run_folders()


class CleanToolTests(unittest.TestCase):
    def clean(self, folder, running):
        runs = Path(folder, "tmp", "runs", "abc")
        runs.mkdir(parents=True)
        settings = types.SimpleNamespace(
            log_path=os.path.join(folder, "a.txt"),
            log_path_is_relative_to_start_folder_if_relative=False,
            crash_log_path=None,
            crash_log_path_is_relative_to_start_folder_if_relative=False,
        )
        registry = mock.Mock()
        registry.records.return_value = (running, 0)
        tool = {
            "settings": mock.Mock(return_value=settings),
            "ask": mock.Mock(return_value="1 3"),
            "confirm": mock.Mock(return_value=True),
            "ProcessRegistry": mock.Mock(return_value=registry),
        }
        folders = {"RUNS_DIR": str(runs.parent), "TEMPORARY_DIR": str(runs.parent.parent)}
        patch_tool = mock.patch.multiple(housekeeping, **tool)
        patch_folders = mock.patch.multiple(housekeeping.paths, **folders)
        with patch_tool, patch_folders, contextlib.redirect_stdout(io.StringIO()):
            housekeeping.cmd_clean([])
        return runs.parent

    def test_files_in_use_are_kept_and_the_rest_is_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            free, busy = Path(folder, "free.txt"), Path(folder, "busy.txt")
            free.touch()
            busy.touch()
            real_remove = os.remove

            def remove(path):
                if os.path.basename(path) == "busy.txt":
                    raise PermissionError(32, "in use", path)
                real_remove(path)

            with mock.patch.object(housekeeping.os, "remove", side_effect=remove):
                self.clean(folder, [])
            self.assertFalse(free.exists())
            self.assertTrue(busy.exists())

    def test_run_folders_are_kept_while_an_instance_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(self.clean(folder, [{"pid": 1}]).exists())

    def test_run_folders_are_deleted_when_nothing_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(self.clean(folder, []).exists())


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
            targets = {"logs": "D:/new", "open_code": "D:/m.py"}
            with mock.patch.object(shortcuts, "CREATED_SHORTCUTS_LIST_PATH", record), mock.patch.object(
                shortcuts, "shortcut_targets", return_value=targets
            ):
                self.assertEqual(shortcuts.outdated_shortcut_targets(object()), ["logs"])


if __name__ == "__main__":
    unittest.main()
