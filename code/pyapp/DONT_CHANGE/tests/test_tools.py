"""tools/fresh_clone_test and tools/test_all_pythons: the parts that can be checked without a clone."""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "template_tools" / "src"), *sys.path]):
    import fresh_clone_test as clone_tool
    import test_all_pythons as python_tool


def assigned_values(source: str):
    """{name: value} of the plain assignments of a source text, the last one winning."""
    values = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            values[node.targets[0].id] = ast.literal_eval(node.value)
    return values


class FreshCloneTests(unittest.TestCase):
    def test_setup_in_the_clone_cannot_touch_the_real_shortcuts(self):
        values = assigned_values(
            "start_menu_shortcuts = True\ndesktop_shortcuts = ['terminal']\n" + clone_tool.TEST_SETTINGS
        )
        self.assertIs(values["start_menu_shortcuts"], False)
        self.assertEqual(values["desktop_shortcuts"], [])

    def test_no_window_can_wait_for_someone(self):
        values = assigned_values(clone_tool.TEST_SETTINGS)
        self.assertIs(values["close_after_success"], True)
        self.assertIs(values["close_after_failure"], True)

    def test_main_script_value_understands_the_settings_file(self):
        text = 'main_script_path: str = "first.py"\nmain_script_path = "..\\\\main.py"\n'
        self.assertEqual(clone_tool.main_script_value(text), "..\\main.py")
        with self.assertRaises(RuntimeError):
            clone_tool.main_script_value("other = 1\n")

    def make_project(self, root: Path, main_script: str) -> Path:
        settings = root / "code" / "pyapp" / "developer_settings.py"
        settings.parent.mkdir(parents=True)
        settings.write_text(f"main_script_path = {main_script!r}\n", encoding="utf-8")
        (root / "code" / "main.py").write_text("real app", encoding="utf-8")
        return settings

    def test_an_absolute_main_script_is_replaced_in_the_clone_only(self):
        with tempfile.TemporaryDirectory() as folder:
            project, clone = Path(folder) / "project", Path(folder) / "clone"
            original = project / "code" / "main.py"
            self.make_project(project, str(original.parent.resolve() / "main.py"))
            clone_settings = self.make_project(clone, str(original.parent.resolve() / "main.py"))

            clone_tool.prepare_clone(clone, Path(folder) / "marker.txt", project)

            self.assertEqual(original.read_text(encoding="utf-8"), "real app")
            self.assertIn("marker.txt", (clone / "code" / "main.py").read_text(encoding="utf-8"))
            # The clone's launcher must run the clone's probe, not the original app.
            self.assertEqual(
                assigned_values(clone_settings.read_text(encoding="utf-8"))["main_script_path"], "..\\main.py"
            )

    def test_a_relative_main_script_stays_relative(self):
        with tempfile.TemporaryDirectory() as folder:
            project, clone = Path(folder) / "project", Path(folder) / "clone"
            self.make_project(project, "..\\main.py")
            self.make_project(clone, "..\\main.py")
            clone_tool.prepare_clone(clone, Path(folder) / "marker.txt", project)
            self.assertEqual((project / "code" / "main.py").read_text(encoding="utf-8"), "real app")
            self.assertIn("marker.txt", (clone / "code" / "main.py").read_text(encoding="utf-8"))

    def test_a_main_script_outside_the_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            project, clone = Path(folder) / "project", Path(folder) / "clone"
            outside = Path(folder) / "elsewhere.py"
            outside.write_text("keep", encoding="utf-8")
            self.make_project(project, "..\\main.py")
            self.make_project(clone, "..\\..\\..\\elsewhere.py")
            with self.assertRaises(RuntimeError):
                clone_tool.prepare_clone(clone, Path(folder) / "marker.txt", project)
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep")
            with self.assertRaises(RuntimeError):
                clone_tool.clone_main_script(clone, str(outside), project)

    def test_batch_command_quotes_paths_with_spaces(self):
        command = clone_tool.batch_command(Path("C:/a b/x.cmd"), "arg")
        self.assertTrue(command.startswith('cmd.exe /d /s /c ""'))
        self.assertTrue(command.endswith(' "arg""'))

    def test_status_separates_new_files(self):
        changed, new = clone_tool.split_status(" M a.py\n?? b.py\nA  c.py\n")
        self.assertEqual((changed, new), (["a.py", "c.py"], ["b.py"]))

    def test_the_launcher_variables_are_not_inherited(self):
        with mock.patch.dict("os.environ", {"PYAPP_PYTHON": "x", "OTHER": "y"}):
            env = clone_tool.clean_environment()
        self.assertNotIn("PYAPP_PYTHON", env)
        self.assertEqual(env["OTHER"], "y")


class AllPythonsTests(unittest.TestCase):
    def test_newest_stable_ignores_prereleases_and_other_builds(self):
        downloads = [
            {"implementation": "cpython", "variant": "default", "version": "3.9.1"},
            {"implementation": "cpython", "variant": "default", "version": "3.14.2"},
            {"implementation": "cpython", "variant": "default", "version": "3.15.0a1"},
            {"implementation": "cpython", "variant": "freethreaded", "version": "3.16.0"},
            {"implementation": "pypy", "variant": "default", "version": "3.17.0"},
        ]
        self.assertEqual(python_tool.newest_stable(downloads), "3.14")

    def test_no_downloads_is_a_clear_problem(self):
        with self.assertRaises(RuntimeError):
            python_tool.newest_stable([])

    def test_summary_reads_the_unittest_output(self):
        output = "noise\nRan 130 tests in 11.0s\n\nOK (skipped=2)\n"
        self.assertEqual(python_tool.summary_of(output), ("130", "OK (skipped=2)"))
        self.assertEqual(python_tool.summary_of("crashed"), ("?", "no result"))

    def test_failure_details_skip_the_noise_before_the_reports(self):
        output = "printed while running\n=====\nFAIL: x\n"
        self.assertEqual(python_tool.failure_details(output), ["=====", "FAIL: x"])

    def test_duplicates_are_dropped(self):
        with mock.patch.object(python_tool, "uv_output", return_value="[]"):
            self.assertEqual(python_tool.resolve_requests("uv", ["3.8", "3.8", "3.12"]), ["3.8", "3.12"])


if __name__ == "__main__":
    unittest.main()
