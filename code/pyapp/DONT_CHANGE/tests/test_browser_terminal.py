"""The browser terminal: its shortcut, the standalone package, and the host with a real pseudoconsole.

The host tests run browser_terminal/host.py's run() with a small Python program and talk to it
over a raw WebSocket like the page does; no browser is opened.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple
from unittest import mock

from project_location import CODE, DONT_CHANGE  # noqa: F401 - puts the code folder on sys.path
from pyapp.DONT_CHANGE.browser_terminal import ui
from pyapp.DONT_CHANGE.scripts import console_tools

if os.name == "nt":
    from pyapp.DONT_CHANGE.actions import start_program
    from pyapp.DONT_CHANGE.browser_terminal import host as browser_terminal
    from pyapp.DONT_CHANGE.scripts import shortcuts

PYTHON = getattr(sys, "_base_executable", sys.executable)

PROGRAM = r"""
import sys, time
print("tty", sys.stdin.isatty(), sys.stdout.isatty())
print("\x1b[31mred\x1b[0m äöü €")
name = input("name? ")
try:
    print("hi " + name + ", waiting for Ctrl+C", flush=True)
    while True:
        time.sleep(0.05)
except KeyboardInterrupt:
    print("interrupted")
sys.exit(3)
"""


class LaunchModeTest(unittest.TestCase):
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
        self.assertTrue(icon.endswith("browser.ico"))
        self.assertTrue(launcher.endswith("\\B\\B.bat"))
        self.assertIn("PYAPP_LAUNCH_MODE=browser", Path(launcher).read_text(encoding="utf-8"))
        self.assertEqual(definitions(""), [])

    def test_the_page_opens_in_a_tab_without_the_hidden_variables(self):
        if os.name != "nt":
            self.skipTest("Windows only")
        seen: Dict[str, Any] = {}

        def fake_open(url: str, new: int) -> bool:
            seen.update(url=url, new=new, visible=os.environ.get("PYAPP_TEST_SECRET"))
            return True

        with mock.patch.dict(os.environ, {"PYAPP_TEST_SECRET": "x"}), mock.patch("webbrowser.open", fake_open):
            browser_terminal.open_browser("http://127.0.0.1:1/t/", ("PYAPP_",))
            # Hidden only while the browser starts, which may outlive the run; back afterwards.
            self.assertEqual(os.environ.get("PYAPP_TEST_SECRET"), "x")
        self.assertEqual(seen, {"url": "http://127.0.0.1:1/t/", "new": 2, "visible": None})

    def test_colors_follow_the_color_command(self):
        self.assertEqual(ui.colors_from_code("9F"), {"background": "#3B78FF", "foreground": "#F2F2F2"})
        # One digit is the text color, as with `color`; "" is the console's default.
        self.assertEqual(ui.colors_from_code("A"), {"background": "#0C0C0C", "foreground": "#16C60C"})
        self.assertEqual(ui.colors_from_code(""), {"background": "#0C0C0C", "foreground": "#CCCCCC"})

    def test_a_normal_console_ignores_the_inherited_variable(self):
        with mock.patch.dict(os.environ, {"PYAPP_BROWSER_TERMINAL_UI": "x"}):
            # The tests never run in a pseudoconsole: a console window of its own, or none at all.
            self.assertFalse(console_tools.in_browser_terminal())


@unittest.skipUnless(os.name == "nt", "Windows only")
class StandaloneTest(unittest.TestCase):
    def test_a_copy_of_the_folder_runs_on_its_own(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "terminal_copy"
            shutil.copytree(str(DONT_CHANGE / "browser_terminal"), str(copy))
            # -I: no current folder, no PYTHONPATH, so nothing of the launcher can be imported.
            # The test's own interpreter with fixed arguments.
            completed = subprocess.run(  # noqa: S603
                [PYTHON, "-I", "-S", str(copy), "--help"], capture_output=True, text=True, timeout=60, check=False
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("--title", completed.stdout)

    def test_the_package_needs_nothing_from_the_launcher(self):
        for path in (DONT_CHANGE / "browser_terminal").glob("*.py"):
            self.assertNotIn("pyapp", path.read_text(encoding="utf-8").lower(), path.name)


class PageClient:
    """The page's side of the WebSocket: binary output collected, JSON messages listed."""

    def __init__(self, port: int, path: str, origin: str = "", host_name: str = "127.0.0.1") -> None:
        self.host = f"{host_name}:{port}"
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\nHost: {self.host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nOrigin: {origin or 'http://' + self.host}\r\n\r\n"
        )
        self.socket.sendall(request.encode("ascii"))
        head = b""
        while b"\r\n\r\n" not in head:
            head += self.socket.recv(1)
        self.status = int(head.split(b" ", 2)[1])
        self.output = b""
        self.messages: List[Dict[str, Any]] = []
        if self.status == 101:
            threading.Thread(target=self._read, daemon=True).start()

    def _receive(self, count: int) -> bytes:
        data = b""
        while len(data) < count:
            chunk = self.socket.recv(count - len(data))
            if not chunk:
                raise EOFError
            data += chunk
        return data

    def _frame(self) -> Tuple[int, bytes]:
        first, second = self._receive(2)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._receive(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._receive(8))[0]
        return first & 0x0F, self._receive(length)

    def _read(self) -> None:
        try:
            while True:
                opcode, payload = self._frame()
                if opcode == 2:
                    self.output += payload
                elif opcode == 1:
                    self.messages.append(json.loads(payload))
                else:
                    return
        except (OSError, EOFError):
            return

    def send(self, message: Dict[str, Any]) -> None:
        payload = json.dumps(message).encode("utf-8")
        mask = os.urandom(4)
        header = (
            struct.pack("!BB", 0x81, 0x80 | len(payload))
            if len(payload) < 126
            else struct.pack("!BBH", 0x81, 0xFE, len(payload))
        )
        self.socket.sendall(header + mask + bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload)))

    def wait_for(self, text: bytes, seconds: float = 20) -> bool:
        deadline = time.monotonic() + seconds
        while text not in self.output and time.monotonic() < deadline:
            time.sleep(0.02)
        return text in self.output

    def close(self) -> None:
        self.socket.close()


@unittest.skipUnless(os.name == "nt", "Windows only")
class HostTest(unittest.TestCase):
    def start(self, program: str, **settings: Any) -> Tuple[str, int, Dict[str, int]]:
        """Run program in the host; returns (token path, port, {"code": ...} once it ended)."""
        run_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, run_dir, True)
        self.run_dir = Path(run_dir)
        urls: List[str] = []

        def open_browser(url: str, hidden_env_prefixes: Tuple[str, ...] = ()) -> None:
            urls.append(url)

        def find_window(_session: object) -> None:
            """No window is ever found without a browser: do not wait for one."""

        patcher = mock.patch.object(browser_terminal, "open_browser", open_browser)
        patcher.start()
        self.addCleanup(patcher.stop)
        finder = mock.patch.object(browser_terminal.Session, "find_window", find_window)
        finder.start()
        self.addCleanup(finder.stop)
        config: Dict[str, Any] = {"title": "T", "state_dir": run_dir, **settings}
        result: Dict[str, int] = {}
        thread = threading.Thread(
            target=lambda: result.setdefault("code", browser_terminal.run(config, [PYTHON, "-c", program])),
            daemon=True,
        )
        thread.start()
        self.addCleanup(thread.join, 30)
        deadline = time.monotonic() + 20
        while not urls and time.monotonic() < deadline:
            time.sleep(0.02)
        self.url = urls[0]
        host, path = urls[0][len("http://") :].split("/", 1)
        return "/" + path, int(host.rsplit(":", 1)[1]), result

    def test_a_fixed_address_is_used_and_a_busy_port_skipped(self):
        busy = socket.socket()
        busy.bind(("127.0.0.1", 0))
        self.addCleanup(busy.close)
        taken = busy.getsockname()[1]
        path, port, _ = self.start(
            "import time; time.sleep(30)", host_name="my-tool.localhost", port=taken, key="fixed-key-123456"
        )
        self.assertEqual(path, "/fixed-key-123456/")
        self.assertEqual(port, taken + 1)
        self.assertEqual(self.url, f"http://my-tool.localhost:{taken + 1}/fixed-key-123456/")
        # The page under its .localhost name may connect, as under 127.0.0.1.
        page = PageClient(port, path + "ws", host_name="my-tool.localhost")
        self.addCleanup(page.close)
        self.assertEqual(page.status, 101)
        other = PageClient(port, path + "ws", host_name="evil.example")
        self.addCleanup(other.close)
        self.assertEqual(other.status, 404)

    def test_a_program_runs_in_a_real_console(self):
        path, port, result = self.start(PROGRAM)
        page = PageClient(port, path + "ws")
        self.addCleanup(page.close)
        self.assertEqual(page.status, 101)
        page.send({"t": "r", "c": 100, "r": 30})
        self.assertTrue(page.wait_for(b"name? "), page.output)
        self.assertIn("tty True True", page.output.decode("utf-8", "replace"))
        self.assertIn("äöü €", page.output.decode("utf-8", "replace"))
        page.send({"t": "i", "d": "Bob\r"})
        self.assertTrue(page.wait_for(b"hi Bob, waiting for Ctrl+C"), page.output)
        # Icon and color requests of the launcher processes reach the page.
        icon = str(self.run_dir / "icon.ico")
        (self.run_dir / "browser-ui.jsonl").write_text(
            json.dumps({"colors": {"background": "#000000", "foreground": "#FFFFFF"}})
            + "\n"
            + json.dumps({"icon": icon})
            + "\n",
            encoding="utf-8",
        )
        # Ctrl+C typed in the page is a KeyboardInterrupt in the program.
        page.send({"t": "i", "d": "\x03"})
        self.assertTrue(page.wait_for(b"interrupted"), page.output)
        deadline = time.monotonic() + 20
        while "code" not in result and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(result.get("code"), 3)
        time.sleep(0.2)
        kinds = [message["t"] for message in page.messages]
        self.assertEqual(kinds[0], "hello")
        self.assertIn({"t": "colors", "colors": {"background": "#000000", "foreground": "#FFFFFF"}}, page.messages)
        self.assertIn({"t": "icon", "v": 1}, page.messages)
        self.assertEqual(page.messages[-1], {"t": "exit", "code": 3})

    def test_only_the_page_may_connect(self):
        path, port, result = self.start("import time; time.sleep(30)")
        foreign = PageClient(port, path + "ws", origin="http://example.com")
        self.addCleanup(foreign.close)
        self.assertEqual(foreign.status, 403)
        guessed = PageClient(port, "/wrong-token/ws")
        self.addCleanup(guessed.close)
        self.assertEqual(guessed.status, 404)
        # The real page connects, then the window closes: the program ends like in a closed console.
        with mock.patch.object(browser_terminal, "RECONNECT_GRACE_SECONDS", 0.3):
            page = PageClient(port, path + "ws")
            page.wait_for(b"\x1b[", 10)
            page.close()
            deadline = time.monotonic() + 30
            while "code" not in result and time.monotonic() < deadline:
                time.sleep(0.05)
        self.assertIn("code", result)


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
