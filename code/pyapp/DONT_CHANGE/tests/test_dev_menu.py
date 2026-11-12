"""The dev tools menu offers every command exactly once."""

import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import project_location  # noqa: F401 - make this checkout's code importable
from pyapp.DONT_CHANGE.scripts.dev_tools import main as dev_tools


class MenuTests(unittest.TestCase):
    def test_every_command_is_in_the_menu_once(self):
        names = [name for _, group in dev_tools.MENU_GROUPS for name in group]
        self.assertEqual(sorted(names), sorted(dev_tools.COMMANDS))

    def test_headings_belong_to_commands(self):
        self.assertLessEqual(set(dev_tools.HEADINGS), set(dev_tools.COMMANDS))


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

    def test_digits_int_cannot_read_are_asked_again(self):
        """ "²".isdigit() is True, but int("²") fails: the menu must ask again, not crash."""
        from pyapp.DONT_CHANGE.runtime import process_exit

        with mock.patch.multiple(
            process_exit,
            local_module_exists=mock.Mock(return_value=False),
            ask=mock.Mock(side_effect=["\u00b2", ""]),
        ), mock.patch(
            "pyapp.DONT_CHANGE.scripts.import_finder.distribution_for_import", return_value="requests"
        ), mock.patch("builtins.print"):
            process_exit.handle_missing_module("requests", "", False)


class ExportTests(unittest.TestCase):
    def test_the_export_never_overwrites_the_requirements_path_file(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages
        from pyapp.DONT_CHANGE.scripts.errors import SetupError

        exported = packages.paths.EXPORTED_REQUIREMENTS_PATH
        with mock.patch.object(packages, "requirements_file_path", return_value=exported.upper()), mock.patch.object(
            packages, "settings"
        ), mock.patch.object(packages, "prepare") as prepare, mock.patch.object(
            packages, "run_uv"
        ) as run_uv, self.assertRaises(SetupError):
            packages.cmd_export([])
        prepare.assert_not_called()
        run_uv.assert_not_called()


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
