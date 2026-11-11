"""Log paths, the diagnostics log, and shortcut names, targets and taskbar identity."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

from project_location import CODE  # noqa: F401 - makes "pyapp" importable

# isort: split

from pyapp.DONT_CHANGE.scripts import diagnostics, launcher_ui, runtime_state, shortcuts
from pyapp.DONT_CHANGE.scripts.dev_tools import housekeeping


class LogTests(unittest.TestCase):
    def test_log_path_resolution(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(
                launcher_ui.get_log_path(str(Path(folder) / "a.txt"), False),
                os.path.normpath(str(Path(folder) / "a.txt")),
            )
            with mock.patch.dict(os.environ, {"PYAPP_START_DIR": folder}):
                self.assertEqual(
                    launcher_ui.get_log_path("logs/a.txt", True), os.path.normpath(str(Path(folder) / "logs/a.txt"))
                )
        self.assertEqual(launcher_ui.get_log_path("", False), "")
        self.assertNotIn("%", launcher_ui.get_log_path(os.path.normpath(str(Path("log_%Y.txt").absolute())), False))

    def test_unique_log_names(self):
        first = runtime_state.unique_log_path("C:/logs/log.txt")
        second = runtime_state.unique_log_path("C:/logs/log.txt")
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith(".txt"))
        self.assertEqual(runtime_state.unique_log_path(""), "")

    def test_ignored_errors_are_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            log = str(Path(folder) / "diagnostics.log")
            with mock.patch.object(diagnostics, "DIAGNOSTICS_LOG_PATH", log):
                try:
                    raise ZeroDivisionError("test")
                except ZeroDivisionError:
                    diagnostics.note_ignored("unit test step")
                summary = diagnostics.diagnostics_summary()
            self.assertIn("1 ignored error", summary or "")
            self.assertIn("ZeroDivisionError", Path(log).read_text(encoding="utf-8"))

    def test_a_chained_traceback_is_one_entry(self):
        """Its blank lines ("During handling of the above exception ...") do not split it."""
        with tempfile.TemporaryDirectory() as folder:
            log = str(Path(folder) / "diagnostics.log")
            with mock.patch.object(diagnostics, "DIAGNOSTICS_LOG_PATH", log):
                try:
                    try:
                        raise KeyError("first")
                    except KeyError:
                        raise ValueError("second")  # noqa: B904 - the implicit chain is the point
                except ValueError:
                    diagnostics.note_ignored("chained step")
                summary = diagnostics.diagnostics_summary() or ""
            self.assertTrue(summary.startswith("1 ignored error(s), last: "), summary)
            self.assertTrue(summary.endswith(": chained step"), summary)


class RemoveTreeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "junctions are a Windows feature")
    def test_a_junction_to_a_folder_outside_is_removed_without_its_target(self):
        from pyapp.DONT_CHANGE.scripts.file_tools import remove_tree_inside

        with tempfile.TemporaryDirectory() as folder:
            base, outside = Path(folder, "base"), Path(folder, "outside")
            base.mkdir()
            outside.mkdir()
            (outside / "keep.txt").write_text("x", encoding="utf-8")
            link = base / "link"
            # Test subprocesses execute fixed fixture/helper code using the local interpreter or Git.
            subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True, check=True)  # noqa: S603, S607
            remove_tree_inside(str(link), str(base))
            self.assertFalse(os.path.lexists(link))
            self.assertTrue((outside / "keep.txt").is_file())
            with self.assertRaises(ValueError):
                remove_tree_inside(str(outside), str(base))


class FinishedRunFolderTests(unittest.TestCase):
    def cleanup(self, running: List[Dict[str, Any]]):
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
        with mock.patch.object(launcher_ui, "RUNS_DIR", str(Path(tempfile.gettempdir()) / "pyapp-no-such-folder")):
            launcher_ui.delete_finished_run_folders()


class CleanToolTests(unittest.TestCase):
    def clean(self, folder: str, running: List[Dict[str, Any]]):
        runs = Path(folder, "tmp", "runs", "abc")
        runs.mkdir(parents=True)
        settings = types.SimpleNamespace(
            log_path=str(Path(folder) / "a.txt"),
            log_path_is_relative_to_start_folder_if_relative=False,
            crash_log_path="",
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
            free, busy = Path(folder, "a_0123456789ab.txt"), Path(folder, "a_ba9876543210.txt")
            free.touch()
            busy.touch()
            real_unlink = Path.unlink

            def remove(path: Path):
                if Path(path).name == busy.name:
                    raise PermissionError(32, "in use", path)
                real_unlink(path)

            with mock.patch.object(Path, "unlink", autospec=True, side_effect=remove):
                self.clean(folder, [])
            self.assertFalse(free.exists())
            self.assertTrue(busy.exists())

    def test_only_the_launchers_own_logs_are_deleted(self):
        # A log folder may be shared with the app's files (e.g. log_path = "run.txt").
        with tempfile.TemporaryDirectory() as folder:
            logs = [Path(folder, "a_0123456789ab.txt"), Path(folder, "a_0123456789ab.txt.output.log")]
            others = [Path(folder, name) for name in ("valuable.csv", "a.txt", "a_notes.txt", "settings.py", ".env")]
            for path in logs + others:
                path.write_text("x", encoding="utf-8")
            Path(folder, "subfolder").mkdir()
            self.clean(folder, [])
            self.assertEqual([path for path in logs if path.exists()], [])
            self.assertEqual([path for path in others if not path.exists()], [])
            self.assertTrue(Path(folder, "subfolder").is_dir())

    def test_log_names_follow_the_date_template(self):
        pattern = housekeeping._log_name_pattern("..\\logs\\log_%Y-%m-%d_%H-%M-%S.txt")
        self.assertTrue(pattern.fullmatch("log_2026-11-10_20-29-45_0123456789ab.txt"))
        self.assertTrue(pattern.fullmatch("LOG_2026-11-10_20-29-45_0123456789AB.TXT"))
        self.assertTrue(pattern.fullmatch("log_2026-11-10_20-29-45_0123456789ab.txt.output.log"))
        self.assertFalse(pattern.fullmatch("log_2026-11-10_20-29-45.txt"))
        self.assertFalse(pattern.fullmatch("notes.txt"))
        self.assertTrue(housekeeping._log_name_pattern("100%%_%H.txt").fullmatch("100%_07_0123456789ab.txt"))

    def test_run_folders_are_kept_while_an_instance_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(self.clean(folder, [{"pid": 1}]).exists())

    def test_run_folders_are_deleted_when_nothing_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(self.clean(folder, []).exists())


class CleanMessageTests(unittest.TestCase):
    def test_kept_run_folders_are_not_reported_as_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            runs = Path(folder, "tmp", "runs")
            runs.mkdir(parents=True)
            settings = types.SimpleNamespace(
                log_path="",
                log_path_is_relative_to_start_folder_if_relative=False,
                crash_log_path="",
                crash_log_path_is_relative_to_start_folder_if_relative=False,
            )
            registry = mock.Mock()
            registry.records.return_value = ([{"pid": 1}], 0)
            tool = {
                "settings": mock.Mock(return_value=settings),
                "ask": mock.Mock(return_value="3"),
                "confirm": mock.Mock(return_value=True),
                "ProcessRegistry": mock.Mock(return_value=registry),
                "print_success": mock.DEFAULT,
            }
            folders = {"RUNS_DIR": str(runs), "TEMPORARY_DIR": str(runs.parent)}
            with mock.patch.multiple(housekeeping, **tool) as mocks, mock.patch.multiple(
                housekeeping.paths, **folders
            ), contextlib.redirect_stdout(io.StringIO()):
                housekeeping.cmd_clean([])
            self.assertNotIn("per-run diagnostics", mocks["print_success"].call_args[0][0])


class CrashCodeTests(unittest.TestCase):
    def test_common_crash_codes_are_recognized(self):
        for code in (0xC0000005, 0xC0000374, 0xC0000094, 0xC0000135, 0xC0000142, 0xE06D7363, -1073740940):
            with self.subTest(code=hex(code & 0xFFFFFFFF)):
                self.assertTrue(runtime_state.exit_code_looks_like_interpreter_crash(code))
        # Ctrl+C and sys.exit(-1) (0xFFFFFFFF) are ordinary ends.
        for code in (0xC000013A, -1, 1, 0):
            with self.subTest(code=code):
                self.assertFalse(runtime_state.exit_code_looks_like_interpreter_crash(code))


class RegistryReadTests(unittest.TestCase):
    def test_a_record_that_cannot_be_read_right_now_is_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = runtime_state.ProcessRegistry(folder)
            record = Path(folder, "123.json")
            record.write_text('{"pid": 123}', encoding="utf-8")
            real_read = Path.read_text

            def locked(path: Path, *args: Any, **kwargs: Any) -> str:
                if Path(path).name == record.name:
                    raise PermissionError(32, "in use by another process", str(path))
                return real_read(path, *args, **kwargs)

            with mock.patch.object(Path, "read_text", locked):
                self.assertEqual(registry.records(), ([], 0))
            self.assertTrue(record.exists())


class RemoveShortcutsTests(unittest.TestCase):
    def test_shortcuts_that_could_not_be_removed_stay_recorded(self):
        from pyapp.DONT_CHANGE.scripts import shortcuts as shortcut_module

        written: List[List[str]] = []

        def record(paths: List[str], *_arguments: object) -> None:
            written.append(list(paths))

        with mock.patch.object(
            shortcut_module, "read_created_shortcuts", return_value=["a.lnk", "b.lnk"]
        ), mock.patch.object(shortcut_module, "remove_shortcuts", return_value=["a.lnk"]), mock.patch.object(
            shortcut_module, "is_generated_shortcut", return_value=True
        ), mock.patch.object(
            shortcut_module, "write_created_shortcuts", side_effect=record
        ), contextlib.redirect_stdout(io.StringIO()):
            housekeeping.cmd_remove_shortcuts([])
        self.assertEqual(written, [["b.lnk"]])


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
            record = str(Path(folder) / "created.json")
            Path(record).write_text(
                json.dumps({"version": 2, "shortcuts": [], "targets": {"logs": "D:/old"}}), encoding="utf-8"
            )
            targets = {"logs": "D:/new", "open_code": "D:/m.py"}
            with mock.patch.object(shortcuts, "CREATED_SHORTCUTS_LIST_PATH", record), mock.patch.object(
                shortcuts, "shortcut_targets", return_value=targets
            ):
                self.assertEqual(shortcuts.outdated_shortcut_targets(mock.Mock()), ["logs"])


if __name__ == "__main__":
    unittest.main()
