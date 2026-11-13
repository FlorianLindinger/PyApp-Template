"""Generated pyproject.toml: round trip of the package list and copying `uv add` changes back."""

import contextlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import support  # first: makes the template importable

# isort: split

from pyapp.DONT_CHANGE.scripts import config
from pyapp.DONT_CHANGE.scripts.env import pyproject, venv
from pyapp.DONT_CHANGE.scripts.errors import SettingsError, SetupError


class PyprojectTests(unittest.TestCase):
    def test_requirements_with_quotes_survive_restarts(self):
        packages = ['pywin32; sys_platform == "win32"', "pkg[extra] ; python_version < '3.12'", "requests>=2"]
        with support.temporary_settings() as (_, load):
            config.set_list_setting("packages", packages)
            for _ in range(3):
                pyproject.reconcile_pyproject(load(), (3, 14))
            self.assertEqual(config.package_entries(load()), packages)
            self.assertEqual(pyproject.declared_dependencies(), packages)

    def test_parser_handles_comments_literal_and_escaped_strings(self):
        text = (
            'x = 1\n[project]\nname = "a"\n'
            'dependencies = [ # a comment with "quotes" and ]\n'
            '  "x>=1", \'lit "q"\',\n  "esc \\" ]",\n]\n[tool.uv]\n'
        )
        self.assertEqual(pyproject.declared_dependencies(text), ["x>=1", 'lit "q"', 'esc " ]'])

    def test_unicode_and_control_characters_make_valid_toml(self):
        packages = ["pkg @ file:///C:/pfad/😀/pkg", "café>=1", 'q"uote\\back', "tab\tnew\nline", "del\x7fnul\x00"]
        text = pyproject.render_pyproject(packages, "==3.14.*")
        self.assertEqual(pyproject.declared_dependencies(text), packages)
        if sys.version_info < (3, 11):
            self.skipTest("tomllib needs Python 3.11 or newer")
        else:
            import tomllib

            self.assertEqual(tomllib.loads(text)["project"]["dependencies"], packages)

    def test_uv_add_in_pyproject_is_copied_into_the_settings(self):
        with support.temporary_settings() as (_, load):
            pyproject.reconcile_pyproject(load(), (3, 14))
            path = Path(pyproject.PYPROJECT_PATH)
            text = path.read_text(encoding="utf-8").replace(
                "dependencies = []", 'dependencies = [\n    "requests>=2.32",\n]'
            )
            path.write_text(text, encoding="utf-8")
            pyproject.reconcile_pyproject(load(), None)
            self.assertEqual(config.package_entries(load()), ["requests>=2.32"])

    def test_dropped_package_sources_are_reported(self):
        with support.temporary_settings() as (_, load):
            pyproject.reconcile_pyproject(load(), (3, 14))
            path = Path(pyproject.PYPROJECT_PATH)
            path.write_text(
                path.read_text(encoding="utf-8") + '\n[tool.uv.sources]\npkg = { git = "https://x.org/pkg" }\n',
                encoding="utf-8",
            )
            with mock.patch.object(pyproject, "print_warn") as warn:
                pyproject.reconcile_pyproject(load(), None)
                pyproject.reconcile_pyproject(load(), None)  # said once: the table is gone now
            warn.assert_called_once()
            self.assertIn("direct reference", warn.call_args[0][0])

    def test_dropped_dependency_groups_are_reported(self):
        with support.temporary_settings() as (_, load):
            pyproject.reconcile_pyproject(load(), (3, 14))
            path = Path(pyproject.PYPROJECT_PATH)
            path.write_text(
                path.read_text(encoding="utf-8") + '\n[dependency-groups]\ndev = ["pytest"]\n', encoding="utf-8"
            )
            with mock.patch.object(pyproject, "print_warn") as warn:
                pyproject.reconcile_pyproject(load(), None)
            warn.assert_called_once()
            self.assertIn("[dependency-groups]", warn.call_args[0][0])

    def test_settings_win_when_both_changed(self):
        with support.temporary_settings() as (_, load):
            pyproject.reconcile_pyproject(load(), (3, 14))
            path = Path(pyproject.PYPROJECT_PATH)
            path.write_text(
                path.read_text(encoding="utf-8").replace("dependencies = []", 'dependencies = ["numpy"]'),
                encoding="utf-8",
            )
            config.set_list_setting("packages", ["requests"])
            pyproject.reconcile_pyproject(load(), None)
            self.assertEqual(config.package_entries(load()), ["requests"])
            self.assertEqual(pyproject.declared_dependencies(), ["requests"])

    def test_requires_python_follows_the_project_python(self):
        with support.temporary_settings() as (_, load):
            pyproject.reconcile_pyproject(load(), (3, 12))
            self.assertEqual(pyproject.current_requires_python(), "==3.12.*")
            self.assertTrue(pyproject.version_satisfies_requires((3, 12, 5), "==3.12.*"))
            self.assertFalse(pyproject.version_satisfies_requires((3, 13, 0), "==3.12.*"))


class TypedPackagesTests(unittest.TestCase):
    def split(self, text: str):
        from pyapp.DONT_CHANGE.scripts.dev_tools.common import split_package_entries

        return split_package_entries(text)

    def test_ranges_and_extras_stay_whole(self):
        self.assertEqual(
            self.split("numpy>=1,<2 requests[socks,security]"), ["numpy>=1,<2", "requests[socks,security]"]
        )

    def test_commas_and_spaces_separate_complete_requirements(self):
        self.assertEqual(self.split("requests, numpy,scipy"), ["requests", "numpy", "scipy"])
        self.assertEqual(self.split("numpy >= 1, < 2  pandas"), ["numpy >= 1, < 2", "pandas"])

    def test_markers_and_direct_references_stay_whole(self):
        self.assertEqual(
            self.split("pywin32; sys_platform == 'win32' pkg @ https://x.org/a.whl#sha256=ab requests"),
            ["pywin32; sys_platform == 'win32'", "pkg @ https://x.org/a.whl#sha256=ab", "requests"],
        )
        self.assertEqual(self.split("pkg[a, b] ; python_version < '3.12'"), ["pkg[a, b] ; python_version < '3.12'"])

    def test_names_ending_like_marker_words_are_separate(self):
        self.assertEqual(self.split("sign-in numpy"), ["sign-in", "numpy"])
        self.assertEqual(
            self.split("pkg; python_version >= '3.8' and sys_platform == 'win32' x"),
            ["pkg; python_version >= '3.8' and sys_platform == 'win32'", "x"],
        )

    def test_empty_input(self):
        self.assertEqual(self.split("  , "), [])


class RequirementsFileTests(unittest.TestCase):
    """requirements_path: packages from a file, in addition to "packages"; the launcher only reads it."""

    def settings_with(self, requirements: str, packages: str = '"requests"'):
        def transform(text: str) -> str:
            return text + f'\r\npackages = {packages}\r\nrequirements_path = "requirements.txt"\r\n'

        context = support.temporary_settings(transform)
        path, load = context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        (path.parent / "requirements.txt").write_text(requirements, encoding="utf-8")
        return path, load

    def test_both_lists_reach_the_environment(self):
        _, load = self.settings_with("# from the file\nnumpy>=2 \\\n    --hash=sha256:aa\n")
        config.validate(load())
        self.assertEqual(config.all_packages(load()), ["requests", "numpy>=2"])
        pyproject.reconcile_pyproject(load(), (3, 14))
        self.assertEqual(pyproject.declared_dependencies(), ["requests", "numpy>=2"])

    def test_problems_in_the_file_are_named(self):
        for content, expected in (("-r other.txt\n", "-r other.txt"), ("Requests>=2\n", "also in")):
            with self.subTest(content=content):
                _, load = self.settings_with(content)
                with self.assertRaises(SettingsError) as raised:
                    config.validate(load())
                self.assertIn(expected, str(raised.exception))
        path, load = self.settings_with("numpy\n")
        (path.parent / "requirements.txt").unlink()
        with self.assertRaises(SettingsError) as raised:
            config.validate(load())
        self.assertIn("cannot be read", str(raised.exception))

    def test_uv_add_is_copied_into_packages_but_never_the_file_packages(self):
        _, load = self.settings_with("numpy>=2\n")
        pyproject.reconcile_pyproject(load(), (3, 14))
        path = Path(pyproject.PYPROJECT_PATH)
        text = path.read_text(encoding="utf-8").replace('"numpy>=2",', '"numpy>=2",\n    "rich>=13",')
        path.write_text(text, encoding="utf-8")
        pyproject.reconcile_pyproject(load(), None)
        self.assertEqual(config.package_entries(load()), ["requests", "rich>=13"])
        self.assertEqual(pyproject.declared_dependencies(), ["requests", "rich>=13", "numpy>=2"])

    def test_a_file_package_is_removed_in_the_file(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages

        _, load = self.settings_with("numpy>=2\n")
        with mock.patch.object(packages, "settings", load), mock.patch.object(
            packages, "prepare"
        ) as prepare, self.assertRaises(SetupError) as raised:
            packages.cmd_remove(["NumPy"])
        self.assertIn("requirements_path", str(raised.exception))
        prepare.assert_not_called()


class RunningInstanceTests(unittest.TestCase):
    """Nothing changes the environment while the app runs (its files are in use)."""

    def an_instance_runs(self) -> None:
        registry = mock.Mock()
        registry.records.return_value = ([{"pid": 1}], 0)
        patcher = mock.patch("pyapp.DONT_CHANGE.scripts.runtime_state.ProcessRegistry", return_value=registry)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_package_changes_are_refused_before_uv_runs(self):
        self.an_instance_runs()
        with mock.patch.object(venv, "run_uv") as run_uv, mock.patch.object(venv, "reconcile_pyproject"):
            for change in (
                lambda: venv.add_packages(["x"]),
                lambda: venv.remove_packages(["x"]),
                lambda: venv.install_without_recording(["x"], "python.exe"),
            ):
                with self.assertRaises(SetupError):
                    change()
        run_uv.assert_not_called()

    def test_dev_tools_refuse_before_preparing_the_environment(self):
        self.an_instance_runs()
        from pyapp.DONT_CHANGE.scripts.dev_tools import packages

        with mock.patch.object(packages, "prepare") as prepare, mock.patch.object(packages, "settings"):
            for command in (packages.cmd_add, packages.cmd_remove, packages.cmd_upgrade, packages.cmd_sync):
                with self.assertRaises(SetupError):
                    command(["x"])
        prepare.assert_not_called()

    def test_a_launch_does_not_sync_under_a_running_instance(self):
        self.an_instance_runs()
        s = SimpleNamespace(python_version="3.14")
        read_stamp = mock.Mock(return_value="old")
        with mock.patch.multiple(
            venv,
            settings=mock.Mock(return_value=s),
            validate=mock.DEFAULT,
            FileLock=mock.Mock(return_value=contextlib.nullcontext()),
            read_python_version_file=mock.Mock(return_value="3.14"),
            request_matches=mock.Mock(return_value=True),
            reconcile_pyproject=mock.Mock(return_value=s),
            current_requires_python=mock.Mock(return_value="==3.14.*"),
            environment_fingerprint=mock.Mock(return_value="new"),
            _read_stamp=read_stamp,
            _write_stamp=mock.DEFAULT,
            sync=mock.DEFAULT,
            build_venv=mock.DEFAULT,
        ) as mocks:
            with self.assertRaises(SetupError):
                venv.ensure_environment()
            mocks["sync"].assert_not_called()
            mocks["build_venv"].assert_not_called()
            # An unchanged environment is not touched, so a second instance can still start.
            read_stamp.return_value = "new"
            venv.ensure_environment()


class FingerprintTests(unittest.TestCase):
    def test_fingerprint_is_stable_and_sees_lock_changes(self):
        with support.temporary_settings() as (_, load):
            settings = load()
            first = venv.environment_fingerprint(settings)
            self.assertEqual(first, venv.environment_fingerprint(settings))
            Path(venv.UV_LOCK_PATH).write_text("changed", encoding="utf-8")
            self.assertNotEqual(first, venv.environment_fingerprint(settings))
            Path(venv.UV_LOCK_PATH).unlink()

    def test_fingerprint_ignores_bytecode_but_sees_installed_packages(self):
        """The first import after Setup writes site-packages/__pycache__; that must keep the fast path."""
        with support.temporary_settings() as (_, load), tempfile.TemporaryDirectory() as venv_dir:
            site_packages = Path(venv_dir, "Lib", "site-packages")
            site_packages.mkdir(parents=True)
            (site_packages / "six.py").write_text("", encoding="utf-8")
            with mock.patch.object(venv, "VENV_DIR", venv_dir):
                settings = load()
                first = venv.environment_fingerprint(settings)
                (site_packages / "__pycache__").mkdir()
                (site_packages / "__pycache__" / "six.cpython-314.pyc").write_bytes(b"")
                self.assertEqual(first, venv.environment_fingerprint(settings))
                (site_packages / "requests-2.32.0.dist-info").mkdir()
                self.assertNotEqual(first, venv.environment_fingerprint(settings))


if __name__ == "__main__":
    unittest.main()
