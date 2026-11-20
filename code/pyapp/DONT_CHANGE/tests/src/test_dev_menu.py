"""The dev tools menu offers every command exactly once."""

import tempfile
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

import project_location  # also makes this checkout's code importable
from pyapp.DONT_CHANGE.scripts.dev_tools import main as dev_tools


class MenuTests(unittest.TestCase):
    def test_every_command_is_in_the_menu_once(self):
        names = [name for _, group in dev_tools.MENU_GROUPS for name in group]
        names += [name for groups in dev_tools.SUBMENU_GROUPS.values() for _, group in groups for name in group]
        self.assertEqual(sorted(names), sorted(dev_tools.COMMANDS))

    def test_compilation_is_a_submenu_and_returns_without_an_extra_pause(self):
        with mock.patch.object(dev_tools, "_run_menu") as show:
            dev_tools.cmd_compilation_menu([])
        commands = [name for _, rows in show.call_args.args[0] for name, _ in rows]
        self.assertEqual(
            commands,
            [
                "compilation-presets",
                "validate-syntax",
                "compile-app",
                "clean-compilation",
                "test-linux",
                "setup-linux",
                "compile-linux",
            ],
        )
        self.assertIn("compilation", dev_tools.NO_PAUSE)
        root_commands = [name for _, group in dev_tools.MENU_GROUPS for name in group]
        with mock.patch.object(
            dev_tools, "ask", side_effect=[str(root_commands.index("compilation") + 1), "", ""]
        ), mock.patch.object(dev_tools, "wait_for_enter") as pause, mock.patch("builtins.print"):
            dev_tools.cmd_menu([])
        pause.assert_not_called()

    def test_zero_opens_the_developer_settings_and_returns_to_the_menu(self):
        with mock.patch.object(dev_tools, "ask", side_effect=["0", ""]), mock.patch(
            "pyapp.DONT_CHANGE.scripts.console_tools.open_in_editor"
        ) as editor, mock.patch.object(dev_tools, "run_command") as run, mock.patch("builtins.print"):
            dev_tools.cmd_menu([])
        editor.assert_called_once()
        self.assertTrue(editor.call_args.args[0].endswith("developer_settings.py"))
        run.assert_not_called()

    def test_zero_in_the_compilation_menu_opens_its_settings_folder(self):
        with mock.patch.object(dev_tools, "ask", side_effect=["0", ""]), mock.patch(
            "os.startfile", create=True
        ) as explorer, mock.patch.object(Path, "is_dir", return_value=True), mock.patch("builtins.print"):
            dev_tools.cmd_compilation_menu([])
        explorer.assert_called_once()

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
        ), mock.patch.object(venv, "add_packages") as add, mock.patch.object(
            venv, "install_problem", return_value=None
        ), mock.patch("builtins.print"):
            process_exit.handle_missing_module("requests", "", False)
        add.assert_not_called()

    def test_digits_int_cannot_read_are_asked_again(self):
        """ "²".isdigit() is True, but int("²") fails: the menu must ask again, not crash."""
        from pyapp.DONT_CHANGE.runtime import process_exit
        from pyapp.DONT_CHANGE.scripts.env import venv

        with mock.patch.multiple(
            process_exit,
            local_module_exists=mock.Mock(return_value=False),
            ask=mock.Mock(side_effect=["\u00b2", ""]),
        ), mock.patch(
            "pyapp.DONT_CHANGE.scripts.import_finder.distribution_for_import", return_value="requests"
        ), mock.patch.object(venv, "install_problem", return_value=None), mock.patch("builtins.print"):
            process_exit.handle_missing_module("requests", "", False)

    def menu(self, problem: Optional[str], answers: List[str], add_error: Optional[Exception] = None) -> Dict[str, Any]:
        """Run the missing-package menu for PySide2; returns the mocks of what it printed and did."""
        from pyapp.DONT_CHANGE.runtime import process_exit
        from pyapp.DONT_CHANGE.scripts.env import venv

        with mock.patch.multiple(
            process_exit,
            local_module_exists=mock.Mock(return_value=False),
            ask=mock.Mock(side_effect=answers),
            print_traceback=mock.DEFAULT,
            print_error=mock.DEFAULT,
            print_warn=mock.DEFAULT,
            print_choices=mock.DEFAULT,
            restart_program=mock.DEFAULT,
        ) as mocks, mock.patch(
            "pyapp.DONT_CHANGE.scripts.import_finder.distribution_for_import", return_value="PySide2"
        ), mock.patch.object(venv, "add_packages", side_effect=add_error) as add, mock.patch.object(
            venv, "install_problem", return_value=problem
        ), mock.patch("builtins.print"):
            process_exit.handle_missing_module("PySide2", "", False)
        mocks["add"] = add
        return mocks

    def test_a_package_that_cannot_exist_here_is_said_once_without_add_choices(self):
        mocks = self.menu("it does not exist for Python 3.14 on Windows (64-bit).", [""])
        headline = mocks["print_warn"].call_args[0][0]
        self.assertIn("cannot be: it does not exist for Python 3.14", headline)
        self.assertIn("older python_version", headline)
        choices = list(mocks["print_choices"].call_args[0][0])
        self.assertFalse([choice for choice in choices if choice.startswith(("Add", "Install"))])
        mocks["add"].assert_not_called()

    def test_a_failed_add_gives_a_message_not_a_traceback(self):
        from pyapp.DONT_CHANGE.scripts.errors import SetupError

        mocks = self.menu(None, ["1", ""], add_error=SetupError("uv add PySide2 failed (exit code 1)."))
        mocks["print_traceback"].assert_not_called()
        mocks["restart_program"].assert_not_called()
        self.assertIn("uv's message above says why", mocks["print_error"].call_args[0][0])

    def test_uv_answers_become_plain_reasons(self):
        from pyapp.DONT_CHANGE.scripts.env import venv

        for err, expected in (
            (
                "cause: Because all versions of pyside2 have no wheels with a matching platform tag",
                "does not exist for",
            ),
            ("cause: ... have no wheels with a matching Python ABI tag (e.g., `cp314`)", "does not exist for"),
            ("the requested Python version (>=3.14) does not satisfy Python>=3.6,<3.11", "does not exist for"),
            ("cause: Because nope was not found in the package registry", "there is no package"),
            ("cause: Because a==1 depends on b<2 and c depends on b>=2", None),
        ):
            with self.subTest(err=err), mock.patch.object(venv, "run_uv_captured", return_value=(1, "", err)):
                problem = venv.install_problem("x")
                if expected is None:
                    self.assertIsNone(problem)
                else:
                    self.assertIn(expected, problem or "")


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


class PackageImportTests(unittest.TestCase):
    def test_requirements_path_with_spaces_is_one_uv_argument(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder, "my requirements.txt")
            source.write_text("requests>=2\n", encoding="utf-8")
            with mock.patch.multiple(
                packages, prepare=mock.DEFAULT, refuse_mutation_while_running=mock.DEFAULT, add_packages=mock.DEFAULT
            ) as mocks, mock.patch("builtins.print"):
                packages.cmd_install_requirements([str(source)])
            mocks["add_packages"].assert_called_once_with(["-r", str(source.resolve())])
            self.assertEqual(source.read_text(encoding="utf-8"), "requests>=2\n")

    def test_cancel_or_missing_requirements_file_does_not_prepare(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages
        from pyapp.DONT_CHANGE.scripts.errors import SetupError

        with mock.patch.object(packages, "ask", return_value=""), mock.patch.object(
            packages, "prepare"
        ) as prepare, mock.patch("builtins.print"):
            packages.cmd_install_requirements([])
            with tempfile.TemporaryDirectory() as folder, self.assertRaises(SetupError):
                packages.cmd_install_requirements([str(Path(folder, "missing.txt"))])
            prepare.assert_not_called()

    def test_reset_keeps_constraints_and_removes_unused_declarations(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages

        with mock.patch.multiple(
            packages,
            settings=mock.DEFAULT,
            package_entries=mock.Mock(return_value=['requests[socks]>=2; python_version >= "3.8"', "unused==1"]),
            confirm=mock.Mock(return_value=True),
            refuse_mutation_while_running=mock.DEFAULT,
            set_list_setting=mock.DEFAULT,
            prepare=mock.DEFAULT,
            sync=mock.DEFAULT,
        ) as mocks, mock.patch("builtins.print"):
            packages.reset_packages_to_imports(["requests", "numpy"])
        mocks["set_list_setting"].assert_called_once_with(
            "packages", ['requests[socks]>=2; python_version >= "3.8"', "numpy"]
        )
        mocks["sync"].assert_called_once_with(packages.paths.VENV_PYTHON_EXE, exact=True)

    def test_clear_packages_empties_the_list_only_after_confirmation(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages

        for answer in (True, False):
            with self.subTest(confirmed=answer), mock.patch.multiple(
                packages,
                settings=mock.DEFAULT,
                validate=mock.DEFAULT,
                package_entries=mock.Mock(return_value=["requests", "numpy>=2"]),
                requirements_file_entries=mock.Mock(return_value=[]),
                confirm=mock.Mock(return_value=answer),
                refuse_mutation_while_running=mock.DEFAULT,
                set_list_setting=mock.DEFAULT,
                prepare=mock.DEFAULT,
                sync=mock.DEFAULT,
            ) as mocks, mock.patch("builtins.print"):
                packages.cmd_clear_packages([])
            if answer:
                mocks["set_list_setting"].assert_called_once_with("packages", [])
                mocks["sync"].assert_called_once_with(packages.paths.VENV_PYTHON_EXE, exact=True)
            else:
                for name in ("set_list_setting", "prepare", "sync"):
                    mocks[name].assert_not_called()

    def test_clear_packages_with_nothing_declared_does_not_ask(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages

        with mock.patch.multiple(
            packages,
            settings=mock.DEFAULT,
            validate=mock.DEFAULT,
            package_entries=mock.Mock(return_value=[]),
            confirm=mock.DEFAULT,
            prepare=mock.DEFAULT,
        ) as mocks, mock.patch("builtins.print"):
            packages.cmd_clear_packages([])
        mocks["confirm"].assert_not_called()
        mocks["prepare"].assert_not_called()

    def test_declining_reset_changes_nothing(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages

        with mock.patch.multiple(
            packages,
            settings=mock.DEFAULT,
            package_entries=mock.Mock(return_value=["unused"]),
            confirm=mock.Mock(return_value=False),
            set_list_setting=mock.DEFAULT,
            prepare=mock.DEFAULT,
            sync=mock.DEFAULT,
        ) as mocks, mock.patch("builtins.print"):
            packages.reset_packages_to_imports([])
        for name in ("set_list_setting", "prepare", "sync"):
            mocks[name].assert_not_called()

    def test_reset_never_removes_after_a_parse_error(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages
        from pyapp.DONT_CHANGE.scripts.errors import SetupError

        with mock.patch.object(packages, "settings"), mock.patch.object(packages, "validate"), mock.patch(
            "pyapp.DONT_CHANGE.scripts.import_finder.find_requirements", return_value=([], ["broken.py"])
        ), mock.patch.object(packages, "set_list_setting") as write, mock.patch("builtins.print"), self.assertRaises(
            SetupError
        ):
            packages.cmd_reset_imports([])
        write.assert_not_called()

    def test_requirements_path_packages_are_excluded_from_replacement_list(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages
        from pyapp.DONT_CHANGE.scripts.import_finder import Requirement

        found = [Requirement("requests", ["requests"], "installed", ["main.py"], False)]
        with mock.patch.multiple(
            packages,
            settings=mock.DEFAULT,
            all_packages=mock.Mock(return_value=["requests>=2", "unused"]),
            requirements_file_entries=mock.Mock(return_value=["requests>=2"]),
            reset_packages_to_imports=mock.DEFAULT,
            validate=mock.DEFAULT,
        ) as mocks, mock.patch(
            "pyapp.DONT_CHANGE.scripts.import_finder.find_requirements", return_value=(found, [])
        ), mock.patch("builtins.print"):
            packages.cmd_reset_imports([])
        mocks["reset_packages_to_imports"].assert_called_once_with([])

    def test_running_app_blocks_reset_before_writing(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages
        from pyapp.DONT_CHANGE.scripts.errors import SetupError

        with mock.patch.multiple(
            packages,
            settings=mock.DEFAULT,
            package_entries=mock.Mock(return_value=["unused"]),
            confirm=mock.Mock(return_value=True),
            refuse_mutation_while_running=mock.Mock(side_effect=SetupError("app running")),
            set_list_setting=mock.DEFAULT,
            prepare=mock.DEFAULT,
        ) as mocks, mock.patch("builtins.print"), self.assertRaises(SetupError):
            packages.reset_packages_to_imports([])
        mocks["set_list_setting"].assert_not_called()
        mocks["prepare"].assert_not_called()


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


class AppTestsTests(unittest.TestCase):
    """dev tool run-tests: the app's tests folders and how they are run."""

    def test_only_tests_folders_with_python_files_count(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import app_tests

        with tempfile.TemporaryDirectory() as folder:
            code_tests, pyapp_tests, empty = (Path(folder, name) for name in ("tests", "pyapp_tests", "empty"))
            (code_tests / "unit").mkdir(parents=True)
            (code_tests / "unit" / "test_a.py").write_text("", encoding="utf-8")
            pyapp_tests.mkdir()
            (pyapp_tests / "notes.txt").write_text("", encoding="utf-8")
            empty.mkdir()
            found = app_tests.test_folders([code_tests, pyapp_tests, empty, Path(folder, "missing")])
        self.assertEqual(found, [code_tests])

    def test_pytest_gets_every_folder_and_unittest_one_run_each(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import app_tests

        folders = [Path("C:/code/tests"), Path("C:/code/pyapp/tests")]
        self.assertEqual(
            app_tests.test_commands("py.exe", ["-E"], folders, True, ["-k", "x"]),
            [["py.exe", "-E", "-m", "pytest", str(folders[0]), str(folders[1]), "-k", "x"]],
        )
        commands = app_tests.test_commands("py.exe", [], folders, False, [])
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[1][-4:], ["-s", str(folders[1]), "-t", str(folders[1])])

    def test_no_tests_at_all_is_a_note_not_a_failure(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import app_tests

        # 5: pytest, and unittest from Python 3.12 on, found no test.
        self.assertEqual(app_tests.summary([0, 0]), "passed")
        self.assertEqual(app_tests.summary([5, 5]), "none")
        self.assertEqual(app_tests.summary([0, 5]), "passed")  # one folder with tests, one empty
        self.assertEqual(app_tests.summary([1, 5]), "failed")

    def test_the_launchers_own_tests_are_never_app_tests(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import app_tests

        launcher = Path(project_location.DONT_CHANGE)
        self.assertFalse(any(launcher in folder.parents or folder == launcher for folder in app_tests.TEST_FOLDERS))


if __name__ == "__main__":
    unittest.main()
