"""The browser terminal in the launcher: its shortcut, stable address and start link.

The package itself has its own tests in browser_terminal/tests; run_browser_tests.cmd runs both.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List
from unittest import mock

from project_location import CODE, DONT_CHANGE  # noqa: F401 - puts the code folder on sys.path
from pyapp.DONT_CHANGE.scripts import console_tools

if os.name == "nt":
    from pyapp.DONT_CHANGE.actions import start_program
    from pyapp.DONT_CHANGE.scripts import shortcuts

PYTHON = getattr(sys, "_base_executable", sys.executable)


class WebPageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed (GitHub's runners have it)")
    def test_the_browser_page_passes_its_javascript_tests(self):
        """browser_terminal/tests/test_web.cjs: the page's own logic, run with Node's test runner."""
        import subprocess

        tests = DONT_CHANGE / "browser_terminal" / "tests" / "test_web.cjs"
        # Node from PATH with the repository's own test file; no shell.
        completed = subprocess.run(  # noqa: S603
            [str(shutil.which("node")), "--test", str(tests)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout[-3000:] + completed.stderr[-2000:])


class LaunchModeTest(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows browser launcher")
    def test_developer_wrapping_default_reaches_the_browser_config(self):
        from pyapp.DONT_CHANGE.scripts.config import fill_missing_settings

        s = SimpleNamespace(program_name="Example", wrap_terminal_output=False)
        fill_missing_settings(s)
        with tempfile.TemporaryDirectory() as folder, mock.patch(
            "pyapp.DONT_CHANGE.scripts.browser_links.address", return_value=("127.0.0.1", 8765, "fixture")
        ), mock.patch("pyapp.DONT_CHANGE.scripts.shortcuts.read_start_link", return_value=""):
            command = start_program.browser_command(s, Path(folder), ["child.exe"])
            config_path = Path(command[command.index("--config") + 1])
            self.assertIs(json.loads(config_path.read_text(encoding="utf-8"))["wrap_output"], False)

    def test_only_its_own_shortcut_starts_the_browser_terminal(self):
        if os.name != "nt":
            self.skipTest("Windows only")
        s = SimpleNamespace(use_classic_terminal=True)
        self.assertEqual(start_program.resolve_mode(s, "browser"), "browser")
        self.assertEqual(start_program.resolve_mode(s, "terminal"), "conhost")

    def test_the_shortcut_is_made_unless_its_name_is_empty(self):
        if os.name != "nt":
            self.skipTest("Windows only")

        def definitions(name: str) -> List[Any]:
            s = SimpleNamespace(
                program_name="App",
                terminal_shortcut_name="",
                no_terminal_shortcut_name="",
                browser_terminal_shortcut_name=name,
                stop_running_shortcut_name="",
                open_log_folder_shortcut_name="",
                open_crash_log_folder_shortcut_name="",
                open_code_shortcut_name="",
                user_settings_path="",
            )
            targets = {"logs": "", "crash_logs": "", "open_code": "", "settings": ""}
            return shortcuts.shortcut_definitions(s, "app", targets)

        ((kind, name, icon, launcher, args, app_id, _),) = definitions("App (Browser)")
        self.assertEqual((kind, name, args, app_id), ("browser_terminal", "App (Browser)", "app", "appB"))
        self.assertTrue(icon.endswith("\\icon.ico"))  # the app's own icon, as for the terminal shortcut
        self.assertTrue(launcher.endswith("\\B\\B.bat"))
        self.assertIn("PYAPP_LAUNCH_MODE=browser", Path(launcher).read_text(encoding="utf-8"))
        self.assertEqual(definitions(""), [])

    def test_a_normal_console_ignores_the_inherited_variable(self):
        with mock.patch.dict(os.environ, {"PYAPP_BROWSER_TERMINAL_UI": "x"}):
            # The tests never run in a pseudoconsole: a console window of its own, or none at all.
            self.assertFalse(console_tools.in_browser_terminal())


@unittest.skipUnless(os.name == "nt", "Windows only")
class LinksTest(unittest.TestCase):
    """The launcher's stable address and start link (scripts/browser_links.py)."""

    def setUp(self):  # pyrefly: ignore[missing-override-decorator]
        from pyapp.DONT_CHANGE.scripts import browser_links

        self.links = browser_links
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        patcher = mock.patch.object(browser_links, "BROWSER_KEY_PATH", str(Path(folder) / "key.txt"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_address_stays_the_same_for_a_project_copy(self):
        s = SimpleNamespace(browser_terminal_address="")
        first = self.links.address(s, "my-app.0123456789")
        self.assertEqual(first, self.links.address(s, "my-app.0123456789"))
        host, port, key = first
        self.assertEqual(host, "my-app.localhost")
        self.assertTrue(20000 <= port < 40000)
        self.assertNotEqual(port, self.links.address(s, "my-app.9876543210")[1])  # another folder
        self.assertGreaterEqual(len(key), 16)
        self.assertEqual(key, self.links.key())  # kept per PC

    def test_a_chosen_address_is_used(self):
        s = SimpleNamespace(browser_terminal_address="http://tool.localhost:8765/")
        self.assertEqual(self.links.address(s, "x.1")[:2], ("tool.localhost", 8765))
        self.assertIsNone(self.links.address_problem("http://127.0.0.1:8765"))
        for bad in (
            "https://tool.localhost:8765",
            "http://example.com:8765",
            "http://tool.localhost",
            "http://localhost:80",
        ):
            self.assertIsNotNone(self.links.address_problem(bad), bad)

    def test_the_start_link_is_registered_and_removed(self):
        import winreg

        name = "pyapp-test-" + os.urandom(4).hex()
        self.addCleanup(self.links.unregister_start_link, name)
        self.assertTrue(self.links.register_start_link(name, "app.1", ""))
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\" + name + "\\shell\\open\\command") as key:
            command = winreg.QueryValue(key, None)
        self.assertIn("B.bat", command)
        self.assertNotIn("%1", command)  # nothing from the link reaches the command line
        self.assertTrue(self.links.unregister_start_link(name))
        self.assertIsNone(self.links.registered_launcher(name))

    def test_a_scheme_of_another_program_is_left_alone(self):
        import winreg

        name = "pyapp-test-" + os.urandom(4).hex()
        path = "Software\\Classes\\" + name
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, path).Close()
        self.addCleanup(winreg.DeleteKey, winreg.HKEY_CURRENT_USER, path)
        self.assertFalse(self.links.register_start_link(name, "app.1", ""))
        self.assertFalse(self.links.unregister_start_link(name))
        self.assertEqual(self.links.registered_launcher(name), "")


if __name__ == "__main__":
    unittest.main()
