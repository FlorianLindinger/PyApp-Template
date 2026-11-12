"""The browser terminal package on its own: no launcher, standard library only.

The host tests run host.run() with a small Python program and talk to it over a raw WebSocket
like the page does; no browser is opened. Run them from anywhere:

    python -m unittest discover -s <this folder>
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
from typing import Any, Dict, List, Tuple
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1]
# Imported as plain modules from the package folder, as `python <folder>` runs it.
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))
import ui

if os.name == "nt":
    import host as browser_terminal

PYTHON = getattr(sys, "_base_executable", sys.executable)
# Modules the package may import besides its own (all of the standard library).
STDLIB = set(getattr(sys, "stdlib_module_names", ())) or {
    "__future__",
    "argparse",
    "ast",
    "base64",
    "contextlib",
    "ctypes",
    "hashlib",
    "http",
    "json",
    "msvcrt",
    "os",
    "pathlib",
    "secrets",
    "shutil",
    "socket",
    "struct",
    "subprocess",
    "sys",
    "tempfile",
    "threading",
    "time",
    "traceback",
    "typing",
    "webbrowser",
    "winreg",
}

PROGRAM = r"""
import os, sys, time
print("tty", sys.stdin.isatty(), sys.stdout.isatty())
print("size", os.get_terminal_size().columns, os.get_terminal_size().lines)
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


class SmallPartsTest(unittest.TestCase):
    def test_colors_follow_the_color_command(self):
        self.assertEqual(ui.colors_from_code("9F"), {"background": "#3B78FF", "foreground": "#F2F2F2"})
        # One digit is the text color, as with `color`; "" is the console's default.
        self.assertEqual(ui.colors_from_code("A"), {"background": "#0C0C0C", "foreground": "#16C60C"})
        self.assertEqual(ui.colors_from_code(""), {"background": "#0C0C0C", "foreground": "#CCCCCC"})

    @unittest.skipUnless(os.name == "nt", "Windows only")
    def test_the_page_opens_in_a_tab_without_the_hidden_variables(self):
        seen: Dict[str, Any] = {}

        def fake_open(url: str, new: int) -> bool:
            seen.update(url=url, new=new, visible=os.environ.get("MYTOOL_SECRET"))
            return True

        with mock.patch.dict(os.environ, {"MYTOOL_SECRET": "x"}), mock.patch("webbrowser.open", fake_open):
            browser_terminal.open_browser("http://127.0.0.1:1/t/", ("MYTOOL_",))
            # Hidden only while the browser starts, which may outlive the run; back afterwards.
            self.assertEqual(os.environ.get("MYTOOL_SECRET"), "x")
        self.assertEqual(seen, {"url": "http://127.0.0.1:1/t/", "new": 2, "visible": None})


@unittest.skipUnless(os.name == "nt", "Windows only")
class OpenInEditorTest(unittest.TestCase):
    """Paths clicked in the output: an editor, never the file's own Windows association."""

    def test_vs_code_opens_the_file_at_its_line(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "main.py"
            file.write_text("print(1)\n", encoding="utf-8")
            with mock.patch.object(browser_terminal, "_vscode", return_value="C:\\Code\\Code.exe"), mock.patch.object(
                browser_terminal.subprocess, "Popen"
            ) as popen, mock.patch("os.startfile", create=True) as startfile:
                browser_terminal.open_in_editor(str(file), 9)
            self.assertEqual(popen.call_args[0][0], ["C:\\Code\\Code.exe", "--goto", f"{file}:9"])
            startfile.assert_not_called()  # it would run a .py file

    def test_without_vs_code_notepad_opens_it(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "main.py"
            file.write_text("print(1)\n", encoding="utf-8")
            with mock.patch.object(browser_terminal, "_vscode", return_value=None), mock.patch.object(
                browser_terminal.subprocess, "Popen"
            ) as popen:
                browser_terminal.open_in_editor(str(file), 9)
            self.assertTrue(popen.call_args[0][0][0].lower().endswith("notepad.exe"))

    def test_a_path_that_is_no_file_opens_nothing(self):
        with mock.patch.object(browser_terminal.subprocess, "Popen") as popen:
            browser_terminal.open_in_editor("C:\\does\\not\\exist.py", 1)
        popen.assert_not_called()


@unittest.skipUnless(os.name == "nt", "Windows only")
class StandaloneTest(unittest.TestCase):
    def test_a_copy_of_the_folder_runs_on_its_own(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "terminal_copy"
            shutil.copytree(str(PACKAGE), str(copy))
            # -I: no current folder, no PYTHONPATH, so nothing of the launcher can be imported.
            # The test's own interpreter with fixed arguments.
            completed = subprocess.run(  # noqa: S603
                [PYTHON, "-I", "-S", str(copy), "--help"], capture_output=True, text=True, timeout=60, check=False
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("--title", completed.stdout)

    def test_the_package_imports_only_itself_and_the_standard_library(self):
        import ast

        own = {path.stem for path in PACKAGE.glob("*.py")}
        for path in PACKAGE.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                else:
                    continue
                for name in names:
                    self.assertTrue(name in own or name in STDLIB, f"{path.name} imports {name}")


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
        # The program started at the page's size, not at a default one that would be redrawn later.
        self.assertIn("size 100 30", page.output.decode("utf-8", "replace"))
        self.assertIn("äöü €", page.output.decode("utf-8", "replace"))
        page.send({"t": "i", "d": "Bob\r"})
        self.assertTrue(page.wait_for(b"hi Bob, waiting for Ctrl+C"), page.output)
        # Icon and color requests of the launcher processes reach the page.
        icon = str(self.run_dir / "icon.ico")
        (self.run_dir / "browser-ui.jsonl").write_text(
            json.dumps({"colors": {"background": "#000000", "foreground": "#FFFFFF"}})
            + "\n"
            + json.dumps({"icon": icon})
            + "\n"
            + json.dumps({"notify": '"main.py" failed: ValueError', "failed": True})
            + "\n",
            encoding="utf-8",
        )
        # A path clicked in the output opens in the editor, at its line.
        with mock.patch.object(browser_terminal, "open_in_editor") as opened:
            page.send({"t": "o", "path": "C:\\x\\main.py", "line": 9})
            deadline = time.monotonic() + 5
            while not opened.called and time.monotonic() < deadline:
                time.sleep(0.02)
        opened.assert_called_once_with("C:\\x\\main.py", 9)
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
        self.assertIn({"t": "notify", "text": '"main.py" failed: ValueError', "failed": True}, page.messages)
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


if __name__ == "__main__":
    unittest.main()
