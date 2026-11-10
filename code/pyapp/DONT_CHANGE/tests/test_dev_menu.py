"""The dev tools menu offers every command exactly once."""

import tempfile
import types
import unittest
from pathlib import Path
from typing import Optional
from unittest import mock

import project_location  # noqa: F401 - make this checkout's code importable
from pyapp.DONT_CHANGE.scripts.dev_tools import main as dev_tools


class MenuTests(unittest.TestCase):
    def test_every_command_is_in_the_menu_once(self):
        names = [name for _, group in dev_tools.MENU_GROUPS for name in group]
        self.assertEqual(sorted(names), sorted(dev_tools.COMMANDS))

    def test_headings_belong_to_commands(self):
        self.assertLessEqual(set(dev_tools.HEADINGS), set(dev_tools.COMMANDS))


class ToolsMenuTests(unittest.TestCase):
    """The Tools shortcut's menu for the people using the app."""

    def test_every_tool_is_a_command_with_a_note(self):
        for name, label, note in dev_tools.USER_TOOLS:
            self.assertIn(name, dev_tools.COMMANDS)
            self.assertTrue(label and note)

    def test_the_tools_that_change_what_everyone_gets_are_left_out(self):
        names = {name for name, _, _ in dev_tools.USER_TOOLS}
        self.assertFalse(names & {"remove", "upgrade", "change-python", "update-python", "find-imports", "export"})

    def test_the_menu_warns_about_settings_and_temporary_installs(self):
        notes = {name: note for name, _, note in dev_tools.USER_TOOLS}
        self.assertIn("developer_settings.py of this copy", notes["make-self-contained"])
        self.assertIn("only temporary", notes["terminal"])

    def test_a_chosen_tool_runs_and_enter_leaves(self):
        command = mock.Mock(__doc__="Repair.")
        with mock.patch.dict(dev_tools.COMMANDS, {"sync": command}), mock.patch.object(
            dev_tools, "ask", side_effect=["2", ""]
        ), mock.patch.object(dev_tools, "wait_for_enter"), mock.patch("builtins.print"):
            dev_tools.cmd_tools([])
        command.assert_called_once_with([])

    def test_the_shortcut_runs_the_tools_menu(self):
        from pyapp.DONT_CHANGE.scripts import shortcuts

        def kinds(name: Optional[str]):
            s = types.SimpleNamespace(
                program_name="App",
                terminal_shortcut_name=None,
                no_terminal_shortcut_name=None,
                stop_running_shortcut_name=None,
                open_log_folder_shortcut_name=None,
                open_crash_log_folder_shortcut_name=None,
                open_code_shortcut_name=None,
                tools_shortcut_name=name,
                user_settings_path=None,
            )
            targets = {"logs": "", "crash_logs": "", "open_code": "", "settings": ""}
            return shortcuts.shortcut_definitions(s, "app", targets)

        (tools,) = kinds("App - Tools")
        self.assertEqual((tools[0], tools[1]), ("tools", "App - Tools"))
        self.assertTrue(tools[3].endswith("T.bat"))
        self.assertEqual(kinds(None), [])


class CancelTests(unittest.TestCase):
    """Every prompt has a way out that changes nothing."""

    def test_change_python_can_be_cancelled(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import py_vers

        s = types.SimpleNamespace(python_version="3.14")
        for answer in ("q", "Cancel", " n "):
            with mock.patch.multiple(
                py_vers,
                settings=mock.Mock(return_value=s),
                read_python_version_file=mock.Mock(return_value="3.14"),
                available_summary=mock.Mock(return_value=""),
                ask=mock.Mock(return_value=answer),
                edit_settings=mock.DEFAULT,
                prepare=mock.DEFAULT,
            ) as mocks, mock.patch("builtins.print"):
                py_vers.cmd_change_python([])
            mocks["edit_settings"].assert_not_called()
            mocks["prepare"].assert_not_called()

    def test_enter_cancels_a_launch_after_a_python_version_change(self):
        from pyapp.DONT_CHANGE.scripts.env import venv
        from pyapp.DONT_CHANGE.scripts.errors import LaunchCancelled

        s = types.SimpleNamespace(python_version="3.13")
        with mock.patch.multiple(
            venv,
            show_setup_window=mock.DEFAULT,
            ask=mock.Mock(return_value=""),
            switch_python=mock.DEFAULT,
            edit_settings=mock.DEFAULT,
        ) as mocks, mock.patch.object(venv.sys, "stdin", object()), mock.patch("builtins.print"), self.assertRaises(
            LaunchCancelled
        ):
            venv.handle_version_change("3.14", s, interactive=True)
        mocks["switch_python"].assert_not_called()
        mocks["edit_settings"].assert_not_called()

    def test_enter_quits_the_missing_package_menu(self):
        from pyapp.DONT_CHANGE.runtime import process_exit
        from pyapp.DONT_CHANGE.scripts.env import venv

        with mock.patch.multiple(
            process_exit,
            local_module_exists=mock.Mock(return_value=False),
            ask=mock.Mock(return_value=""),
        ), mock.patch(
            "pyapp.DONT_CHANGE.scripts.import_finder.distribution_for_import", return_value="requests"
        ), mock.patch.object(venv, "add_packages") as add, mock.patch("builtins.print"):
            process_exit.handle_missing_module("requests", "", False)
        add.assert_not_called()


class SelfContainedTests(unittest.TestCase):
    def test_status_tells_whether_everything_is_inside_the_folder(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import self_contained

        local = types.SimpleNamespace(**self_contained.SELF_CONTAINED_SETTINGS)
        shared = types.SimpleNamespace(**{**self_contained.SELF_CONTAINED_SETTINGS, "python_source": "uv_user"})
        with tempfile.TemporaryDirectory() as folder:
            uv = Path(folder) / "uv" / "uv.exe"
            pythons = Path(folder) / "pythons"
            uv.parent.mkdir()
            uv.touch()
            config = {"home": str(pythons / "cpython-3.14" / "")}
            with mock.patch.multiple(
                self_contained.paths, LOCAL_UV_EXE=str(uv), LOCAL_PYTHONS_DIR=str(pythons)
            ), mock.patch.object(self_contained, "read_venv_config", return_value=config):
                self.assertTrue(self_contained.is_self_contained(local))
                self.assertFalse(self_contained.is_self_contained(shared))
                config["home"] = "D:/shared/uv/python/cpython-3.14"  # a shared Python outside the folder
                self.assertFalse(self_contained.is_self_contained(local))


if __name__ == "__main__":
    unittest.main()
