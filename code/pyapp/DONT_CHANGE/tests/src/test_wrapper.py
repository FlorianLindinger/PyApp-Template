"""runtime/script_wrapper.py: runs main.py like `python main.py` and reports how it ended."""

from __future__ import annotations

import io
import json
import os
import runpy
import signal
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Dict, Optional, Sequence
from unittest import mock

from project_location import DONT_CHANGE

WRAPPER = DONT_CHANGE / "runtime" / "script_wrapper.py"


class WrapperTests(unittest.TestCase):
    def test_interrupt_policy_ignores_or_confirms_ctrl_c_but_stop_always_interrupts(self):
        with mock.patch.object(sys, "path", [str(WRAPPER.parent), *sys.path]):
            wrapper = runpy.run_path(str(WRAPPER), run_name="interrupt_policy_test")
        install = wrapper["install_keyboard_interrupt_policy"]
        with tempfile.TemporaryDirectory() as folder:
            stop = Path(folder) / "stop"
            for action in ("ignore", "confirm"):
                with self.subTest(action=action), mock.patch.object(signal, "signal") as set_signal:
                    install(action, "Example", str(stop))
                    handler = set_signal.call_args.args[1]
                    confirm = mock.Mock(return_value=False)
                    with mock.patch.dict(install.__globals__, confirm_keyboard_interrupt=confirm):
                        handler(signal.SIGINT, None)
                        self.assertEqual(confirm.call_count, int(action == "confirm"))
                        if action == "confirm":
                            confirm.return_value = True
                            with self.assertRaises(KeyboardInterrupt):
                                handler(signal.SIGINT, None)
                        stop.write_text("stop", encoding="utf-8")
                        with self.assertRaises(KeyboardInterrupt):
                            handler(signal.SIGINT, None)
                        stop.unlink()

    def test_real_sigint_can_be_ignored_and_default_keyboard_interrupt_is_reported(self):
        source = "import signal\nsignal.raise_signal(signal.SIGINT)\nprint('continued')\n"
        code, output, _ = self.run_app(source, keyboard_interrupt_action="ignore")
        self.assertEqual(code, 0, output)
        self.assertIn("continued", output)
        code, output, run = self.run_app(source, keyboard_interrupt_action="interrupt")
        self.assertNotEqual(code, 0, output)
        self.assertEqual(
            json.loads((run / "traceback.json").read_text(encoding="utf-8"))["exception_type"], "KeyboardInterrupt"
        )

    def test_confirmation_reentrancy_and_a_failed_dialog_do_not_strand_the_app(self):
        with mock.patch.object(sys, "path", [str(WRAPPER.parent), *sys.path]):
            wrapper = runpy.run_path(str(WRAPPER), run_name="interrupt_confirmation_test")
        install = wrapper["install_keyboard_interrupt_policy"]
        with mock.patch.object(signal, "signal") as set_signal:
            install("confirm", "Example")
        handler = set_signal.call_args.args[1]

        def confirm(_name: str) -> bool:
            handler(signal.SIGINT, None)  # second Ctrl+C while the first dialog is active
            return False

        confirm_mock = mock.Mock(side_effect=confirm)
        with mock.patch.dict(install.__globals__, confirm_keyboard_interrupt=confirm_mock):
            handler(signal.SIGINT, None)
        confirm_mock.assert_called_once_with("Example")
        with mock.patch.dict(
            install.__globals__, confirm_keyboard_interrupt=mock.Mock(side_effect=OSError("denied"))
        ), self.assertRaises(KeyboardInterrupt):
            handler(signal.SIGINT, None)

    def test_native_focus_restores_only_a_visible_console_window(self):
        import ctypes

        with mock.patch.object(sys, "path", [str(WRAPPER.parent), *sys.path]):
            wrapper = runpy.run_path(str(WRAPPER), run_name="native_focus_test")
        for visible in (False, True):
            kernel, user = mock.Mock(), mock.Mock()
            kernel.GetConsoleWindow.return_value = 123
            user.IsWindowVisible.return_value = visible
            with self.subTest(visible=visible), mock.patch.object(ctypes, "WinDLL", side_effect=[kernel, user]):
                wrapper["request_foreground"]("")
            if visible:
                user.ShowWindow.assert_called_once_with(123, 9)
                user.SetForegroundWindow.assert_called_once_with(123)
            else:
                user.ShowWindow.assert_not_called()
                user.SetForegroundWindow.assert_not_called()

    def test_first_output_attention_is_shared_by_text_binary_and_error_streams(self):
        with mock.patch.object(sys, "path", [str(WRAPPER.parent), *sys.path]):
            wrapper = runpy.run_path(str(WRAPPER), run_name="first_output_test")
        request = mock.Mock()
        callback_factory = wrapper["first_output_callback"]
        with mock.patch.dict(callback_factory.__globals__, request_foreground=request):
            callback = callback_factory("browser.jsonl")
            out = wrapper["PipeSplitter"](io.StringIO())
            err = wrapper["PipeSplitter"](io.StringIO())
            out.on_output = err.on_output = callback
            out.write("")
            err.buffer.write(b"")
            request.assert_not_called()
            err.buffer.write(b"first")
            out.write("second")
            err.write("third")
        request.assert_called_once_with("browser.jsonl")

    def test_first_output_focus_failure_does_not_break_printing(self):
        with mock.patch.object(sys, "path", [str(WRAPPER.parent), *sys.path]):
            wrapper = runpy.run_path(str(WRAPPER), run_name="focus_failure_test")
        request = mock.Mock(side_effect=OSError("focus denied"))
        callback_factory = wrapper["first_output_callback"]
        with mock.patch.dict(callback_factory.__globals__, request_foreground=request):
            target = io.StringIO()
            stream = wrapper["PipeSplitter"](target)
            stream.on_output = callback_factory("")
            stream.write("one")
            stream.write("two")
        self.assertEqual(target.getvalue(), "onetwo")
        request.assert_called_once()

    def test_first_print_setting_requests_browser_focus_only_once_and_defaults_off(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                request_file = Path(self.temporary_folder()) / "ui.jsonl"
                code, _, _ = self.run_app(
                    'import helper\nprint("main")\n',
                    extra_files={"helper.py": 'import sys\nprint("imported", file=sys.stderr)\n'},
                    browser_ui=str(request_file),
                    foreground_on_first_print=enabled,
                )
                self.assertEqual(code, 0)
                self.assertEqual(
                    request_file.read_text(encoding="utf-8") if request_file.exists() else "",
                    '{"foreground": true}\n' if enabled else "",
                )

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
        extra_files: Optional[Dict[str, str]] = None,
        env: Optional[Dict[str, str]] = None,
        stdin: Optional[str] = None,
        main_relative: str = "main.py",
        **config: object,
    ):
        """Run `source` as main.py through the wrapper; return (exit code, stdout, run folder)."""
        folder = Path(self.temporary_folder())
        app = folder / "app"
        run = folder / "run"
        app.mkdir()
        run.mkdir()
        script = app / main_relative
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(textwrap.dedent(source), encoding="utf-8")
        for name, text in (extra_files or {}).items():
            path = app / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        settings = {
            "script": str(script),
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

    def test_nested_main_can_import_code_root_and_keeps_local_import_priority(self):
        code, output, _ = self.run_app(
            "import sys, root_helper, local_helper, collision\n"
            "from pathlib import Path\n"
            "assert sys.path[:2] == [str(Path(__file__).parent), str(Path(__file__).parent.parent)]\n"
            "print(root_helper.VALUE, local_helper.VALUE, collision.VALUE)\n",
            main_relative="nested/main.py",
            extra_files={
                "root_helper.py": 'VALUE = "root"\n',
                "nested/local_helper.py": 'VALUE = "local"\n',
                "collision.py": 'VALUE = "wrong priority"\n',
                "nested/collision.py": 'VALUE = "script first"\n',
            },
        )
        self.assertEqual(code, 0, output)
        self.assertIn("root local script first", output)

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
        variable_frames = report["variables"][-1]["frames"]
        self.assertTrue(all(frame["filename"].endswith("main.py") for frame in variable_frames))
        self.assertEqual(variable_frames[-1]["name"], "f")
        self.assertIn("f", variable_frames[-1]["globals"])

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
        self.assertTrue(background["variables"])

    def run_logged(self, source: str):
        """Run with a log and native output capture; return (exit code, console, log text, raw path)."""
        log = Path(self.temporary_folder()) / "log.txt"
        raw = Path(str(log) + ".output.log")
        code, console, _ = self.run_app(source, log_path=str(log), native_output=str(raw))
        log_bytes = log.read_bytes()
        self.assertNotIn(b"\r\r", log_bytes, "a native line end was doubled")
        return code, console, log_bytes.decode("utf-8"), raw

    def test_native_and_child_output_is_merged_into_the_log_in_order(self):
        source = """
            import os, subprocess, sys
            print("one")
            os.write(1, b"two\\n")
            print("three", file=sys.stderr)
            subprocess.run([sys.executable, "-c", "print('four')"], check=True)
            print("five")
            os.write(2, b"six")
        """
        code, console, log, raw = self.run_logged(source)
        self.assertEqual(code, 0)
        self.assertEqual(log.split(), ["one", "two", "three", "four", "five", "six"])
        for word in ("one", "two", "three", "four", "five", "six"):
            self.assertIn(word, console)
        self.assertEqual(raw.read_bytes().split(), [b"two", b"four", b"six"])

    def test_native_output_before_a_hard_crash_is_kept(self):
        code, _, _, raw = self.run_logged("import os\nos.write(1, b'last words\\n')\nos._exit(7)\n")
        self.assertEqual(code, 7)
        self.assertIn(b"last words", raw.read_bytes())

    def test_atexit_failure_is_recorded(self):
        source = """
            import atexit
            def save():
                raise RuntimeError('final save failed')
            atexit.register(lambda: print('remaining cleanup ran'))
            atexit.register(save)
        """
        code, output, run = self.run_app(source)
        self.assertEqual(code, 0)
        self.assertIn("remaining cleanup ran", output)
        background = json.loads((run / "traceback.json.background").read_text(encoding="utf-8"))
        self.assertEqual(background["exception_type"], "RuntimeError")
        self.assertTrue(background["variables"])

    def test_atexit_system_exit_preserves_success_and_records_failure(self):
        for status in (0, 1):
            with self.subTest(status=status):
                code, _, run = self.run_app(f"import atexit\nimport sys\natexit.register(sys.exit, {status})\n")
                self.assertEqual(code, 0)
                self.assertEqual((run / "traceback.json.background").exists(), status != 0)

    def test_atexit_registration_keeps_decorators_arguments_and_reverse_order(self):
        source = """
            import atexit
            def finish(name, *, suffix):
                print(name + suffix)
            assert atexit.register(finish, 'first', suffix='!') is finish
            @atexit.register
            def second():
                print('second')
            assert second.__name__ == 'second'
        """
        code, output, run = self.run_app(source)
        self.assertEqual(code, 0)
        self.assertEqual(output.splitlines(), ["second", "first!"])
        self.assertFalse((run / "traceback.json.background").exists())

    def test_atexit_unregister_removes_duplicates_and_equal_callables(self):
        source = """
            import atexit
            def removed():
                raise RuntimeError('should not run')
            atexit.register(removed)
            atexit.register(removed)
            atexit.unregister(removed)
            class EqualCallback:
                def __call__(self):
                    raise RuntimeError('equal callback should not run')
                def __eq__(self, other):
                    return isinstance(other, EqualCallback)
            atexit.register(EqualCallback())
            atexit.unregister(EqualCallback())
            try:
                atexit.register(42)
            except TypeError:
                pass
            else:
                raise AssertionError('non-callable was accepted')
        """
        code, _, run = self.run_app(source)
        self.assertEqual(code, 0)
        self.assertFalse((run / "traceback.json.background").exists())

    def test_other_ignored_errors_stay_harmless(self):
        source = """
            class Leaky:
                def __del__(self):
                    raise RuntimeError('in __del__')
            Leaky()
            import atexit
            atexit.register(lambda: None)
        """
        code, _, run = self.run_app(source)
        self.assertEqual(code, 0)
        self.assertFalse((run / "traceback.json.background").exists())

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
