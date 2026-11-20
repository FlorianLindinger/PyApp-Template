"""DONT_CHANGE/app_api.py ("import pyapp_api"): the helpers main.py can use, with and without the launcher."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Callable, List, Tuple
from unittest import mock

import support  # noqa: F401 - makes the template importable
from project_location import CODE, DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE import app_api, backend_settings
from pyapp.DONT_CHANGE.scripts import app_api_support

WRAPPER = DONT_CHANGE / "runtime" / "script_wrapper.py"


class ContractTests(unittest.TestCase):
    def test_the_public_names_are_the_protected_ones_and_callable(self):
        self.assertEqual(sorted(app_api.__all__), sorted(backend_settings.PROTECTED_APP_API_NAMES))
        for name in app_api.__all__:
            self.assertTrue(callable(getattr(app_api, name)), name)

    def test_the_forwarder_in_code_exposes_the_same_names(self):
        forwarder = (CODE / "pyapp_api.py").read_text(encoding="utf-8")
        self.assertIn("from pyapp.DONT_CHANGE.app_api import *", forwarder)


class WithoutLauncherTests(unittest.TestCase):
    """python main.py: every launcher feature does nothing and returns a neutral value."""

    def setUp(self):  # pyrefly: ignore[missing-override-decorator]
        patcher = mock.patch.object(app_api, "_launched", False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_launcher_features_do_nothing(self):
        self.assertFalse(app_api.launched())
        self.assertFalse(app_api.notify("title", "text"))
        self.assertFalse(app_api.set_progress(0.5))
        self.assertFalse(app_api.set_overlay(None))
        self.assertFalse(app_api.highlight("error"))
        self.assertFalse(app_api.flash())
        self.assertFalse(app_api.bring_to_front())
        self.assertFalse(app_api.minimize_to_tray())
        self.assertFalse(app_api.set_title("Working"))
        self.assertFalse(app_api.on_settings_changed(lambda: None))
        self.assertIsNone(app_api.report_error(ValueError("x")))
        self.assertIsNone(app_api.restart())  # returns instead of ending the app
        self.assertFalse(app_api.on_new_start(lambda arguments, folder: None))
        with app_api.keep_awake(display=True):
            pass

    def test_wrong_arguments_are_still_reported(self):
        with mock.patch.object(app_api, "_launched", True), self.assertRaises(ValueError):
            app_api.set_progress(0.5, state="green")
        with self.assertRaises(ValueError):
            app_api.message_box("text", kind="question")
        with mock.patch.object(app_api, "_launched", True), self.assertRaises(ValueError):
            app_api.highlight("purple")


class StopCallbackTests(unittest.TestCase):
    def test_all_callbacks_run_once_in_order_even_if_one_fails(self):
        calls: List[str] = []

        def failing() -> None:
            calls.append("failing")
            raise RuntimeError("callback broke")

        callbacks: List[object] = []
        with mock.patch.object(app_api, "_stop_callbacks", callbacks), mock.patch("traceback.print_exc"):
            app_api.on_stop(lambda: calls.append("first"))
            app_api.on_stop(failing)
            app_api.on_stop(lambda: calls.append("last"))
            app_api._run_stop_callbacks()
            app_api._run_stop_callbacks()  # a second trigger (e.g. X after Ctrl+C) runs nothing again
        self.assertEqual(calls, ["first", "failing", "last"])


class SettingsWatchTests(unittest.TestCase):
    def test_saving_the_settings_file_reloads_settings_and_calls_back(self):
        called = threading.Event()

        def change_at_once(_path: Path, on_change: Callable[[], None]) -> None:
            on_change()  # instead of waiting for the file to be saved

        with tempfile.TemporaryDirectory() as folder:
            settings_file = Path(folder, "settings.py")
            settings_file.write_text("value = 1\n", encoding="utf-8")
            with mock.patch.object(app_api, "_launched", True), mock.patch.dict(
                os.environ, {"USER_SETTINGS_PATH": str(settings_file)}
            ), mock.patch.object(app_api_support, "watch_file", side_effect=change_at_once), mock.patch.object(
                app_api_support, "reload_settings_module"
            ) as reload:
                self.assertTrue(app_api.on_settings_changed(called.set))
            reload.assert_called_once_with(settings_file)
        self.assertTrue(called.is_set())

    def test_the_watcher_notices_a_saved_file(self):
        changed = threading.Event()
        with tempfile.TemporaryDirectory() as folder:
            watched = Path(folder, "settings.py")
            watched.write_text("value = 1\n", encoding="utf-8")
            app_api_support.watch_file(watched, changed.set, interval=0.05)
            time.sleep(0.2)
            watched.write_text("value = 2\n", encoding="utf-8")
            os.utime(watched, (time.time() + 5, time.time() + 5))  # a clearly newer modification time
            self.assertTrue(changed.wait(5), "the change was not noticed")


class ForwardedStartTests(unittest.TestCase):
    def test_a_cancelled_start_reaches_the_running_listener(self):
        received: List[Tuple[List[str], str]] = []
        arrived = threading.Event()

        def callback(arguments: List[str], folder: str) -> None:
            received.append((arguments, folder))
            arrived.set()

        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            app_api_support, "FORWARD_DIR", Path(folder) / "forwarded"
        ), mock.patch.object(app_api, "_launched", True):
            self.assertEqual(app_api_support.forward_start(["nobody listens"], folder), 0)
            self.assertTrue(app_api.on_new_start(callback))
            self.assertEqual(app_api_support.forward_start(["open", "file with spaces.txt"], "C:\\start"), 1)
            self.assertTrue(arrived.wait(5), "the listener did not receive the forwarded start")
            # A listener whose process has ended is cleaned up instead of receiving messages.
            (Path(folder) / "forwarded" / "listener-999999999").write_text("", encoding="utf-8")
            self.assertEqual(app_api_support.forward_start([], folder), 1)
            self.assertFalse((Path(folder) / "forwarded" / "listener-999999999").exists())
        self.assertEqual(received[0], (["open", "file with spaces.txt"], "C:\\start"))


class WrapperTests(unittest.TestCase):
    def run_app(self, source: str) -> Tuple[int, str, Path]:
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(folder, ignore_errors=True))
        script = folder / "main.py"
        script.write_text(source, encoding="utf-8")
        run = folder / "run"
        run.mkdir()
        no_arguments: List[str] = []
        config = {
            "script": str(script),
            "args": no_arguments,
            "traceback": str(run / "traceback.json"),
            "result": str(run / "result.json"),
            "ready": str(run / "ready"),
            # The real code folder, so "pyapp.DONT_CHANGE" (and with it pyapp_api) is importable.
            "app_root": str(CODE),
            "launch_mode": "conhost",
            "shortcut_app_id": "test-app",
        }
        (run / "wrapper.json").write_text(json.dumps(config), encoding="utf-8")
        # Test subprocesses execute fixed fixture/helper code using the local interpreter.
        process = subprocess.run(  # noqa: S603
            [sys.executable, "-E", "-s", str(WRAPPER), "--config", str(run / "wrapper.json")],
            cwd=str(folder),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return process.returncode, process.stdout + process.stderr, folder

    def test_main_py_imports_pyapp_api_and_on_stop_runs_after_ctrl_c(self):
        source = (
            "import pyapp_api\n"
            "from pathlib import Path\n"
            "print('launched', pyapp_api.launched())\n"
            "pyapp_api.on_stop(lambda: Path('saved.txt').write_text('saved'))\n"
            "raise KeyboardInterrupt\n"
        )
        code, output, folder = self.run_app(source)
        self.assertEqual(code, 1, output)
        self.assertIn("launched True", output)
        self.assertEqual((folder / "saved.txt").read_text(encoding="utf-8"), "saved")

    def test_a_normal_end_runs_no_stop_callback(self):
        source = (
            "import pyapp_api\n"
            "from pathlib import Path\n"
            "pyapp_api.on_stop(lambda: Path('saved.txt').write_text('saved'))\n"
        )
        code, output, folder = self.run_app(source)
        self.assertEqual(code, 0, output)
        self.assertFalse((folder / "saved.txt").exists())


@unittest.skipUnless(os.name == "nt", "Windows dialogs and notifications")
class WindowsTests(unittest.TestCase):
    def test_notify_uses_the_apps_id_and_the_click_target(self):
        with mock.patch.object(app_api, "_launched", True), mock.patch.dict(
            os.environ, {"APP_ID": "my-app"}
        ), mock.patch("pyapp.DONT_CHANGE.scripts.windows_notifications.show", return_value=None) as show:
            self.assertTrue(app_api.notify("Done", "12 files", open_path="C:\\out"))
        show.assert_called_once_with("Done", "12 files", "my-app", open_path="C:\\out")

    def test_restart_starts_the_same_shortcut_target_after_this_run(self):
        launch = {"launch_mode": "no_terminal", "app_id": "my-app"}
        with mock.patch.object(app_api, "_launched", True), mock.patch.dict(app_api._launch, launch), mock.patch.object(
            app_api_support.subprocess, "Popen"
        ) as start, self.assertRaises(SystemExit) as ended:
            app_api.restart()
        self.assertEqual(ended.exception.code, 0)
        arguments = start.call_args.args[0]
        self.assertEqual(arguments[4], str(os.getpid()))
        self.assertTrue(arguments[5].endswith("N.bat"))
        self.assertEqual(arguments[6], "my-app")

    def test_a_slow_start_is_not_mistaken_for_a_dead_listener(self):
        self.assertTrue(app_api_support.alive(os.getpid()))
        started = time.monotonic()
        self.assertFalse(app_api_support.alive(999999999))
        self.assertLess(time.monotonic() - started, 2)


if __name__ == "__main__":
    unittest.main()
