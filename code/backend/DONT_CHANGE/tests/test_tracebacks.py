"""Traceback reports (runtime/_pyapp.py) and their rendering (scripts/traceback_render.py)."""

import runpy
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from project_location import CODE  # noqa: F401 - makes "backend" importable

# isort: split

from backend.DONT_CHANGE.runtime import _pyapp
from backend.DONT_CHANGE.scripts.traceback_render import render


def report_for(source, extra_lines=2):
    """Run source as an app file and return the report of the exception it raises."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "main.py"
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        try:
            runpy.run_path(str(path), run_name="__main__")
        except BaseException as error:
            return _pyapp.build_report(error, str(path), folder, (extra_lines, extra_lines))
    raise AssertionError("the source did not raise")


class ReportTests(unittest.TestCase):
    def test_chain_order_and_relations(self):
        report = report_for(
            """
            try:
                raise KeyError('first')
            except KeyError as error:
                raise ValueError('second') from error
            """
        )
        chain = report["chain"]
        self.assertEqual([entry["exception_only"][0].split(":")[0] for entry in chain], ["KeyError", "ValueError"])
        self.assertIn("direct cause", chain[1]["relation"])

    def test_suppressed_context_is_left_out(self):
        report = report_for(
            """
            try:
                raise KeyError('hidden')
            except KeyError:
                raise ValueError('shown') from None
            """
        )
        self.assertEqual(len(report["chain"]), 1)

    def test_notes_are_kept(self):
        if sys.version_info < (3, 11):
            self.skipTest("exception notes need Python 3.11+")
        report = report_for("e = ValueError('x')\ne.add_note('a note')\nraise e\n")
        self.assertIn("a note", "\n".join(report["chain"][-1]["exception_only"]))

    def test_exception_groups_use_cpython_formatting(self):
        if sys.version_info < (3, 11):
            self.skipTest("exception groups need Python 3.11+")
        report = report_for("raise ExceptionGroup('group', [ValueError(1), TypeError(2)])\n")
        self.assertTrue(report["has_group"])
        text = "\n".join(render(report))
        self.assertIn("ExceptionGroup", text)
        self.assertIn("TypeError", text)

    def test_success_rules_for_system_exit(self):
        for code, success in ((None, True), (0, True), (False, True), (1, False), (True, False), ("x", False)):
            self.assertEqual(_pyapp.exit_code_is_success(code), success, code)

    def test_explicit_exit_code_mapping(self):
        mapping = _pyapp.EXIT_MODE_FOR_WRAPPER_EXIT
        self.assertEqual(mapping[_pyapp.WrapperExit.SUCCESS], _pyapp.ExitMode.SUCCESS)
        self.assertEqual(mapping[_pyapp.WrapperExit.APP_FAILED], _pyapp.ExitMode.APP_EXIT)
        self.assertNotIn(_pyapp.WrapperExit.INIT_FAILED, mapping)
        self.assertFalse(set(vars(_pyapp.WrapperExit).values()) & {_pyapp.ExitMode.APP_EXIT, _pyapp.ExitMode.NO_REPORT})


class RenderTests(unittest.TestCase):
    def test_plain_text_has_context_and_marker(self):
        report = report_for("x = 1\ny = 2\nraise RuntimeError('boom')\n")
        text = "\n".join(render(report, colors=False))
        self.assertIn("RuntimeError: boom", text)
        self.assertIn(">", text)
        self.assertNotIn("\x1b[", text)

    def test_lines_before_and_after_are_separate(self):
        source = "a = 1\nb = 2\nc = 3\nraise RuntimeError('boom')\nd = 4\ne = 5\n"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.py"
            path.write_text(source, encoding="utf-8")
            try:
                runpy.run_path(str(path), run_name="__main__")
            except RuntimeError as error:
                report = _pyapp.build_report(error, str(path), folder, (2, 1))
            else:
                self.fail("the source did not raise")
        numbers = [number for number, _ in report["chain"][-1]["frames"][-1]["context"]]
        self.assertEqual(numbers, [2, 3, 4, 5])

    def test_colored_lines_keep_a_black_background(self):
        report = report_for("raise RuntimeError('boom')\n")
        for line in render(report, colors=True):
            self.assertTrue(line.startswith("\x1b[40m"), repr(line))

    def test_colors_only_when_asked(self):
        report = report_for("raise RuntimeError('boom')\n")
        self.assertIn("\x1b[", "\n".join(render(report, colors=True)))


if __name__ == "__main__":
    unittest.main()
