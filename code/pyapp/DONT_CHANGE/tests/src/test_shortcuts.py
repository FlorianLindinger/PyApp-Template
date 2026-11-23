"""scripts/desktop/shortcuts.py: shortcut names, order, targets, taskbar identity, and removing them."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import List
from unittest import mock

from project_location import CODE  # noqa: F401 - makes "pyapp" importable

# isort: split

from pyapp.DONT_CHANGE.scripts.desktop import shortcuts
from pyapp.DONT_CHANGE.scripts.dev_tools import housekeeping


class ShortcutTests(unittest.TestCase):
    def test_windows_startup_is_opt_in_and_each_mode_uses_the_existing_launcher(self):
        s = SimpleNamespace(start_on_windows_start=False)
        with mock.patch.object(shortcuts, "special_folder") as folder:
            self.assertIsNone(shortcuts.create_windows_startup_shortcut(s, "app.copy"))
            folder.assert_not_called()
        s = SimpleNamespace(program_name="Example", start_on_windows_start=True)
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            shortcuts, "special_folder", return_value=folder
        ), mock.patch.object(shortcuts, "generate_shortcut", return_value="created.lnk") as create:
            for mode, launcher, suffix in (
                ("terminal", shortcuts.LAUNCHER_TERMINAL, ""),
                ("no_terminal", shortcuts.LAUNCHER_NO_TERMINAL, shortcuts.NO_TERMINAL_APP_ID_SUFFIX),
                ("browser", shortcuts.LAUNCHER_BROWSER_TERMINAL, shortcuts.BROWSER_APP_ID_SUFFIX),
            ):
                s.windows_startup_launch_mode = mode
                self.assertEqual(shortcuts.create_windows_startup_shortcut(s, "app.copy"), "created.lnk")
                self.assertEqual(create.call_args.args[2], launcher)
                self.assertEqual(create.call_args.kwargs["app_id"], "app.copy" + suffix)
                self.assertEqual(create.call_args.kwargs["args"], "app.copy")

    @unittest.skipUnless(os.name == "nt", "Windows shell links")
    def test_startup_link_is_owned_recorded_and_removed_without_touching_an_unrelated_file(self):
        s = SimpleNamespace(
            program_name="Example", start_on_windows_start=True, windows_startup_launch_mode="no_terminal"
        )
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            shortcuts, "special_folder", return_value=folder
        ), mock.patch.object(shortcuts, "CREATED_SHORTCUTS_LIST_PATH", str(Path(folder) / "created.json")):
            created = shortcuts.create_windows_startup_shortcut(s, "app.copy")
            self.assertIsNotNone(created)
            self.assertTrue(Path(created).is_file())
            self.assertTrue(shortcuts.is_generated_shortcut(created))
            shortcuts.write_created_shortcuts([created])
            s.start_on_windows_start = False
            self.assertIsNone(shortcuts.create_windows_startup_shortcut(s, "app.copy"))
            self.assertEqual(shortcuts.remove_shortcuts(shortcuts.read_created_shortcuts()), [created])
            Path(created).write_text("handmade", encoding="utf-8")
            s.start_on_windows_start = True
            with self.assertRaisesRegex(FileExistsError, "unrelated"):
                shortcuts.create_windows_startup_shortcut(s, "app.copy")
            self.assertEqual(Path(created).read_text(encoding="utf-8"), "handmade")

    @unittest.skipUnless(os.name == "nt", "Windows shell links")
    def test_shortcut_default_start_in_is_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder, "shortcut location")
            shortcut = shortcuts.generate_shortcut(
                "Working folder probe", None, str(Path(folder, "target.cmd")), output_dir=str(output)
            )
            # IShellLink's HasWorkingDir flag (bit 4 of LinkFlags at byte 20).
            flags = int.from_bytes(Path(shortcut).read_bytes()[20:24], "little")
            self.assertEqual(flags & 0x10, 0)

    @unittest.skipUnless(os.name == "nt", "Windows shell links")
    def test_explicit_shortcut_start_folder_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder, "shortcut location")
            override = Path(folder, "explicit start folder")
            shortcut = shortcuts.generate_shortcut(
                "Working folder probe",
                None,
                str(Path(folder, "target.cmd")),
                wdir=str(override),
                output_dir=str(output),
            )
            self.assertIn(str(override).encode("utf-16le"), Path(shortcut).read_bytes())

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
        kinds = [d[0] for d in shortcuts.shortcut_definitions(s, "app")]
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
        kinds = [d[0] for d in shortcuts.shortcut_definitions(s, "app")]
        self.assertEqual(kinds, [k for k in expected if k != "settings"])


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
