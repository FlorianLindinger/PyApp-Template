"""Generated pyproject.toml: round trip of the package list and copying `uv add` changes back."""

import unittest
from pathlib import Path

import support  # first: makes the template importable

# isort: split

from backend.DONT_CHANGE.scripts.env import pyproject, venv


class PyprojectTests(unittest.TestCase):
    def test_requirements_with_quotes_survive_restarts(self):
        packages = ['pywin32; sys_platform == "win32"', "pkg[extra] ; python_version < '3.12'", "requests>=2"]
        with support.temporary_settings() as (_, load):
            from backend.DONT_CHANGE.scripts import config

            config.set_list_setting("packages", packages)
            for _ in range(3):
                pyproject.reconcile_pyproject(load(), (3, 14))
            self.assertEqual(load().packages, packages)
            self.assertEqual(pyproject.declared_dependencies(), packages)

    def test_parser_handles_comments_literal_and_escaped_strings(self):
        text = (
            'x = 1\n[project]\nname = "a"\n'
            'dependencies = [ # a comment with "quotes" and ]\n'
            '  "x>=1", \'lit "q"\',\n  "esc \\" ]",\n]\n[tool.uv]\n'
        )
        self.assertEqual(pyproject.declared_dependencies(text), ["x>=1", 'lit "q"', 'esc " ]'])

    def test_uv_add_in_pyproject_is_copied_into_the_settings(self):
        with support.temporary_settings() as (_, load):
            pyproject.reconcile_pyproject(load(), (3, 14))
            path = Path(pyproject.PYPROJECT_PATH)
            text = path.read_text(encoding="utf-8").replace(
                "dependencies = []", 'dependencies = [\n    "requests>=2.32",\n]'
            )
            path.write_text(text, encoding="utf-8")
            pyproject.reconcile_pyproject(load(), None)
            self.assertEqual(load().packages, ["requests>=2.32"])

    def test_settings_win_when_both_changed(self):
        with support.temporary_settings() as (_, load):
            from backend.DONT_CHANGE.scripts import config

            pyproject.reconcile_pyproject(load(), (3, 14))
            path = Path(pyproject.PYPROJECT_PATH)
            path.write_text(
                path.read_text(encoding="utf-8").replace("dependencies = []", 'dependencies = ["numpy"]'),
                encoding="utf-8",
            )
            config.set_list_setting("packages", ["requests"])
            pyproject.reconcile_pyproject(load(), None)
            self.assertEqual(load().packages, ["requests"])
            self.assertEqual(pyproject.declared_dependencies(), ["requests"])

    def test_requires_python_follows_the_project_python(self):
        with support.temporary_settings() as (_, load):
            pyproject.reconcile_pyproject(load(), (3, 12))
            self.assertEqual(pyproject.current_requires_python(), "==3.12.*")
            self.assertTrue(pyproject.version_satisfies_requires((3, 12, 5), "==3.12.*"))
            self.assertFalse(pyproject.version_satisfies_requires((3, 13, 0), "==3.12.*"))


class FingerprintTests(unittest.TestCase):
    def test_fingerprint_is_stable_and_sees_lock_changes(self):
        with support.temporary_settings() as (_, load):
            settings = load()
            first = venv.environment_fingerprint(settings)
            self.assertEqual(first, venv.environment_fingerprint(settings))
            Path(venv.UV_LOCK_PATH).write_text("changed", encoding="utf-8")
            self.assertNotEqual(first, venv.environment_fingerprint(settings))
            Path(venv.UV_LOCK_PATH).unlink()


if __name__ == "__main__":
    unittest.main()
