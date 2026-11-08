"""runtime/script_wrapper.py: runs main.py like `python main.py` and reports how it ended."""

from __future__ import annotations

import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Sequence
from unittest import mock

from project_location import DONT_CHANGE

WRAPPER = DONT_CHANGE / "runtime" / "script_wrapper.py"


class WrapperTests(unittest.TestCase):
    def test_text_and_binary_logging_without_a_console(self):
        with mock.patch.object(sys, "path", [str(WRAPPER.parent), *sys.path]):
            wrapper = runpy.run_path(str(WRAPPER), run_name="wrapper_no_console_test")
        log = io.StringIO()
        stream = wrapper["PipeSplitter"](None, log)
        self.assertEqual(stream.write("text\n"), 5)
        self.assertEqual(stream.buffer.write(b"binary\n"), 7)
        stream.write_input_prompt("prompt: ")
        stream.complete_input_line("answer")
        self.assertEqual(log.getvalue(), "text\nbinary\nprompt: answer\n")
        self.assertFalse(stream.isatty())

    def run_app(
        self,
        source: str,
        args: Sequence[str] = (),
        extra_files: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
        stdin: str | None = None,
        **config: object,
    ):
        """Run `source` as main.py through the wrapper; return (exit code, stdout, run folder)."""
        folder = Path(self.temporary_folder())
        app = folder / "app"
        run = folder / "run"
        app.mkdir()
        run.mkdir()
        (app / "main.py").write_text(textwrap.dedent(source), encoding="utf-8")
        for name, text in (extra_files or {}).items():
            (app / name).write_text(text, encoding="utf-8")
        settings = {
            "script": str(app / "main.py"),
            "args": list(args),
            "traceback": str(run / "traceback.json"),
            "result": str(run / "result.json"),
            "ready": str(run / "ready"),
            "app_root": str(app),
            **config,
        }
        (run / "wrapper.json").write_text(json.dumps(settings), encoding="utf-8")
        # Test subprocesses execute fixed fixture/helper code using the local interpreter or Git.
        process = subprocess.run(  # noqa: S603
            [sys.executable, "-E", "-s", str(WRAPPER), "--config", str(run / "wrapper.json")],
            cwd=str(app),
            env={**os.environ, **(env or {})},
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
        return process.returncode, process.stdout + process.stderr, run

    def temporary_folder(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return directory.name

    def report(self, run: Path):
        return json.loads((run / "traceback.json").read_text(encoding="utf-8"))

    def test_success_writes_result_and_ready(self):
        code, _, run = self.run_app("print('hi')\n")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((run / "result.json").read_text())["wrapper_exit_code"], 0)
        self.assertTrue((run / "ready").exists())

    def test_log_records_input_after_every_kind_of_prompt(self):
        log = Path(self.temporary_folder()) / "app.log"
        source = "input('Name:\\n')\ninput('Age: ')\ninput()\n"
        code, _, _ = self.run_app(source, stdin="Flo\n42\nlast\n", log_path=str(log))
        self.assertEqual(code, 0)
        self.assertEqual(log.read_text(encoding="utf-8").splitlines(), ["Name:", "Flo", "Age: 42", "last"])

    def test_arguments_are_exact_and_launcher_variables_are_hidden(self):
        source = "import os, sys\nprint(repr(sys.argv[1:]), os.environ.get('PYAPP_SECRET'))\n"
        code, output, _ = self.run_app(source, args=["a b", "", "c"], env={"PYAPP_SECRET": "1"})
        self.assertEqual(code, 0)
        self.assertIn("['a b', '', 'c'] None", output)

    def test_apps_own_protocol_module_is_not_shadowed(self):
        code, output, _ = self.run_app(
            "import protocol\nprint('own', protocol.NAME)\n", extra_files={"protocol.py": "NAME = 'mine'\n"}
        )
        self.assertEqual(code, 0, output)
        self.assertIn("own mine", output)

    def test_exception_report_has_app_frames_and_context(self):
        code, _, run = self.run_app(
            "def f():\n    raise ValueError('boom')\n\nf()\n", traceback_lines_before=1, traceback_lines_after=0
        )
        self.assertEqual(code, 1)
        report = self.report(run)
        self.assertEqual(report["exception_type"], "ValueError")
        frames = report["chain"][-1]["frames"]
        self.assertTrue(frames[0]["filename"].endswith("main.py"), "launcher frames were not stripped")
        self.assertTrue(all(frame["app"] for frame in frames))
        self.assertTrue(frames[-1]["context"])

    def test_system_exit_codes(self):
        for source, expected in (
            ("import sys\nsys.exit(0)\n", 0),
            ("import sys\nsys.exit(3)\n", 3),
            ("import sys\nsys.exit('bye')\n", "bye"),
        ):
            with self.subTest(source=source):
                code, _, run = self.run_app(source)
                self.assertEqual(code, 1)  # reported through traceback.json
                report = self.report(run)
                self.assertEqual(report["exception_type"], "SystemExit")
                self.assertEqual(report["system_exit_code"], expected)

    def test_missing_module_is_named(self):
        _, _, run = self.run_app("import definitely_missing_pyapp_module\n")
        self.assertEqual(self.report(run)["missing_module"], "definitely_missing_pyapp_module")

    def test_os_exit_leaves_no_completion_report(self):
        code, _, run = self.run_app("import os\nos._exit(5)\n")
        self.assertEqual(code, 5)
        self.assertFalse((run / "result.json").exists())

    def test_worker_thread_failure_after_main_returned_is_recorded(self):
        source = """
            import threading, time
            def work():
                time.sleep(0.3)
                raise RuntimeError('late worker')
            threading.Thread(target=work).start()
        """
        code, _, run = self.run_app(source)
        self.assertEqual(code, 0)
        background = json.loads((run / "traceback.json.background").read_text(encoding="utf-8"))
        self.assertEqual(background["exception_type"], "RuntimeError")

    def test_log_and_print_prefixes(self):
        folder = Path(self.temporary_folder())
        log = folder / "log.txt"
        code, output, _ = self.run_app(
            "print('hello')\n", log_path=str(log), print_prepend="P| ", log_print_prepend="L| "
        )
        self.assertEqual(code, 0)
        self.assertIn("P| hello", output)
        self.assertIn("L| hello", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
