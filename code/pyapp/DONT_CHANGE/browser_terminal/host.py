"""The browser terminal host: run a command in a Windows pseudoconsole and show it in a browser.

Usually started through the package (python <folder of this package> [options] -- <command>, see
README.md); run(config, command) is the same from Python. It
  * creates a pseudoconsole (ConPTY, Windows 10 1809+) and starts the command in it, so the
    command sees a real console: input(), Ctrl+C, colors, titles and cursor movement work as in
    the classic console, and console tools (GetConsoleWindow, AttachConsole) keep working;
  * serves the page in web/ (xterm.js, bundled, so it works offline) from 127.0.0.1, behind a
    secret key in the address, and streams the console over a WebSocket. Host name, port and key
    can be fixed (config "host_name", "port", "key"), so the address can be bookmarked;
  * opens the page in a new tab of the default browser and brings that browser to the front.

Like closing a console window, closing the page ends the command (after a short grace period, so
reloading the page does not). When the command ends, the page closes itself.

Window icon and color changes cannot pass through a pseudoconsole: processes in the console ask
for them through a JSON-lines file instead (see ui.py). Standard library only, Python 3.8+, and
nothing outside this folder, so the folder can be copied into other projects.
"""

from __future__ import annotations

import base64
import contextlib
import ctypes
import hashlib
import http.server
import json
import msvcrt
import os
import secrets
import socket
import struct
import subprocess
import sys
import threading
import time
import traceback
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

try:  # imported as a package (python -m, an embedding program) or the folder run as a script (__main__.py)
    from . import ui
except ImportError:
    import ui

STATIC_DIR = Path(__file__).resolve().parent / "web"
# Files the page may load; everything else is 404. Content types are fixed here, not guessed.
STATIC_FILES = {
    "xterm.js": "text/javascript; charset=utf-8",
    "xterm.css": "text/css; charset=utf-8",
    "addon-fit.js": "text/javascript; charset=utf-8",
    "addon-web-links.js": "text/javascript; charset=utf-8",
    "addon-search.js": "text/javascript; charset=utf-8",
    "terminal.js": "text/javascript; charset=utf-8",
}
ICON_TYPES = {".ico": "image/x-icon", ".png": "image/png"}

# Size of the pseudoconsole if a connected page does not report its own within FIRST_SIZE_SECONDS
# (the classic console's default). Normally the command starts at the page's size: output printed
# at another size is partly overwritten when the pseudoconsole is resized to the page, because
# it repaints its screen then.
INITIAL_COLUMNS, INITIAL_ROWS = 120, 30
FIRST_SIZE_SECONDS = 5
# The browser must connect within this time, or the program is ended (nobody could see it).
CONNECT_TIMEOUT_SECONDS = 60
# A page that disconnects gets this long to come back (a reload) before the program is ended.
RECONNECT_GRACE_SECONDS = 5
# What a page that (re)connects receives first: the end of the output so far. ConPTY repaints the
# visible screen on the next resize, so this only has to cover the scrollback.
HISTORY_LIMIT = 2_000_000
# Largest WebSocket message accepted from the page (a big paste); larger ones close the socket.
MAX_MESSAGE_BYTES = 8_000_000
WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
# A pseudoconsole's processes get a CTRL_CLOSE_EVENT when it closes, and Windows ends them about
# 5 s later; the host waits a little longer than that for the command to end.
CLOSE_WAIT_SECONDS = 10


def _print_ignored(context: str) -> None:
    print(f"browser terminal: ignored error ({context}):", file=sys.stderr)
    traceback.print_exc()


# Called inside an except block for an error the host ignores on purpose (cosmetic steps); an
# embedding program can replace it before run(), e.g. to write its own log.
report_ignored: Callable[[str], None] = _print_ignored

# Editors started with the "code" command (bin\code.cmd sits one folder below the executable).
VSCODE_EXECUTABLES = ("Code.exe", "Code - Insiders.exe", "VSCodium.exe", "Cursor.exe")


def _vscode() -> Optional[str]:
    """VS Code (or a fork) found through the "code" command, as its .exe (no cmd.exe parsing of paths)."""
    import shutil

    found = shutil.which("code")
    if not found:
        return None
    if found.lower().endswith((".cmd", ".bat")):
        folder = Path(found).resolve().parent.parent
        for name in VSCODE_EXECUTABLES:
            if (folder / name).is_file():
                return str(folder / name)
        return None
    return found


def open_in_editor(path: str, line: Optional[int] = None) -> None:
    """Open a file clicked in the output: VS Code at the line, else Notepad.

    Never with the file's Windows association: for a .py file that would run it.
    """
    file = Path(path)
    if not file.is_file():
        return
    editor = _vscode()
    env = {key: value for key, value in os.environ.items() if key.upper() != "ELECTRON_RUN_AS_NODE"}
    if editor:
        target = f"{file}:{line}" if line else str(file)
        # The user's editor, with the clicked path as one argument.
        subprocess.Popen([editor, "--goto", target], env=env)  # noqa: S603
    else:
        notepad = os.environ.get("WINDIR", "C:\\Windows") + "\\System32\\notepad.exe"
        subprocess.Popen([notepad, str(file)], env=env)  # noqa: S603


# ---------------------------------------------------------------- Windows API

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
STARTF_USESTDHANDLES = 0x00000100
PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0
SW_RESTORE = 9
VK_MENU = 0x12  # Alt
KEYEVENTF_KEYUP = 0x0002
MB_ICONERROR = 0x10


class COORD(ctypes.Structure):
    _fields_ = (("X", wintypes.SHORT), ("Y", wintypes.SHORT))


class STARTUPINFOW(ctypes.Structure):
    _fields_ = (
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    )


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = (("StartupInfo", STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p))


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    )


kernel32.CreatePipe.argtypes = [
    ctypes.POINTER(wintypes.HANDLE),
    ctypes.POINTER(wintypes.HANDLE),
    ctypes.c_void_p,
    wintypes.DWORD,
]
kernel32.CreatePipe.restype = wintypes.BOOL
kernel32.CreatePseudoConsole.argtypes = [
    COORD,
    wintypes.HANDLE,
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
]
kernel32.CreatePseudoConsole.restype = ctypes.c_long  # HRESULT
kernel32.ResizePseudoConsole.argtypes = [wintypes.HANDLE, COORD]
kernel32.ResizePseudoConsole.restype = ctypes.c_long
kernel32.ClosePseudoConsole.argtypes = [wintypes.HANDLE]
kernel32.ClosePseudoConsole.restype = None
kernel32.InitializeProcThreadAttributeList.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
kernel32.UpdateProcThreadAttribute.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL
kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
kernel32.DeleteProcThreadAttributeList.restype = None
kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.BOOL,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    ctypes.c_void_p,
    ctypes.POINTER(PROCESS_INFORMATION),
]
kernel32.CreateProcessW.restype = wintypes.BOOL
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetExitCodeProcess.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.SetConsoleCtrlHandler.argtypes = [ctypes.c_void_p, wintypes.BOOL]
kernel32.SetConsoleCtrlHandler.restype = wintypes.BOOL
kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.TerminateProcess.restype = wintypes.BOOL

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
user32.keybd_event.restype = None
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
user32.MessageBoxW.restype = ctypes.c_int


def _check(ok: object, what: str) -> None:
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error(), what)


def _environment_block(env: Dict[str, str]) -> str:
    """CreateProcessW's environment: NAME=value strings, sorted case-insensitively as Windows expects."""
    items = sorted(env.items(), key=lambda item: item[0].upper())
    return "".join(f"{key}={value}\0" for key, value in items) + "\0"


class PseudoConsole:
    """A ConPTY session running one command. read()/write() carry UTF-8 text with VT sequences."""

    def __init__(
        self, command: List[str], env: Dict[str, str], columns: int, rows: int, cwd: Optional[str] = None
    ) -> None:
        input_read, input_write = wintypes.HANDLE(), wintypes.HANDLE()
        output_read, output_write = wintypes.HANDLE(), wintypes.HANDLE()
        _check(kernel32.CreatePipe(ctypes.byref(input_read), ctypes.byref(input_write), None, 0), "CreatePipe")
        _check(kernel32.CreatePipe(ctypes.byref(output_read), ctypes.byref(output_write), None, 0), "CreatePipe")
        self._console = wintypes.HANDLE()
        result = kernel32.CreatePseudoConsole(
            COORD(columns, rows), input_read, output_write, 0, ctypes.byref(self._console)
        )
        # The pseudoconsole holds its own copies of its ends of the pipes.
        kernel32.CloseHandle(input_read)
        kernel32.CloseHandle(output_write)
        if result != 0:
            kernel32.CloseHandle(input_write)
            kernel32.CloseHandle(output_read)
            raise OSError(f"CreatePseudoConsole failed (HRESULT 0x{result & 0xFFFFFFFF:08X}); Windows 10 1809+ needed")
        # File descriptors make reading and writing plain os.read/os.write calls; closing them
        # closes the handles.
        self._input = msvcrt.open_osfhandle(input_write.value or 0, os.O_WRONLY | os.O_BINARY)
        self._output = msvcrt.open_osfhandle(output_read.value or 0, os.O_RDONLY | os.O_BINARY)
        self._closed = False
        self._write_lock = threading.Lock()
        self.process = self._start(command, env, cwd)

    def _start(self, command: List[str], env: Dict[str, str], cwd: Optional[str]) -> int:
        size = ctypes.c_size_t()
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))  # asks for the size
        attributes = ctypes.create_string_buffer(size.value)
        _check(
            kernel32.InitializeProcThreadAttributeList(attributes, 1, 0, ctypes.byref(size)),
            "InitializeProcThreadAttributeList",
        )
        try:
            # The attribute's value is the HPCON itself, not a pointer to it.
            _check(
                kernel32.UpdateProcThreadAttribute(
                    attributes,
                    0,
                    PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
                    self._console.value,
                    ctypes.sizeof(wintypes.HANDLE),
                    None,
                    None,
                ),
                "UpdateProcThreadAttribute",
            )
            startup = STARTUPINFOEXW()
            startup.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
            # Empty standard handles: without them the child would use this host's (a log file),
            # because Windows hands a redirected parent's handles on even to a pseudoconsole child.
            # Left empty, the console attaches its own input and output.
            startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES
            startup.lpAttributeList = ctypes.cast(attributes, ctypes.c_void_p)
            info = PROCESS_INFORMATION()
            # Processes inherit "ignore Ctrl+C" from their parent (some shells and launchers set
            # it); the command must react to the Ctrl+C typed in the page like in a console window.
            kernel32.SetConsoleCtrlHandler(None, False)
            command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
            environment = ctypes.create_unicode_buffer(_environment_block(env))
            _check(
                kernel32.CreateProcessW(
                    None,
                    command_line,
                    None,
                    None,
                    False,
                    EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT,
                    ctypes.cast(environment, ctypes.c_void_p),
                    cwd,
                    ctypes.byref(startup),
                    ctypes.byref(info),
                ),
                "CreateProcessW",
            )
        finally:
            kernel32.DeleteProcThreadAttributeList(attributes)
        kernel32.CloseHandle(info.hThread)
        self.pid = int(info.dwProcessId)
        return int(info.hProcess or 0)

    def read(self) -> bytes:
        """The next output (blocking); b"" once the pseudoconsole is closed."""
        try:
            return os.read(self._output, 65536)
        except OSError:  # broken pipe: the pseudoconsole is gone
            return b""

    def write(self, data: bytes) -> None:
        """Send keyboard input (UTF-8, VT sequences for special keys)."""
        with self._write_lock:
            if self._closed:
                return
            view = memoryview(data)
            while view:
                written = os.write(self._input, view[:65536])
                view = view[written:]

    def resize(self, columns: int, rows: int) -> None:
        columns = max(2, min(columns, 1000))
        rows = max(2, min(rows, 500))
        if not self._closed:
            kernel32.ResizePseudoConsole(self._console, COORD(columns, rows))

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """The command's exit code, or None while it still runs after timeout seconds."""
        milliseconds = INFINITE if timeout is None else int(timeout * 1000)
        if kernel32.WaitForSingleObject(self.process, milliseconds) != WAIT_OBJECT_0:
            return None
        code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(self.process, ctypes.byref(code))
        return code.value

    def close(self) -> None:
        """Close the pseudoconsole: its processes get CTRL_CLOSE_EVENT, like a closed console window.

        On older Windows 10, ClosePseudoConsole waits until its last output was read, so read()
        must keep running in another thread meanwhile.
        """
        with self._write_lock:
            if self._closed:
                return
            self._closed = True
            with contextlib.suppress(OSError):
                os.close(self._input)
        kernel32.ClosePseudoConsole(self._console)


# ---------------------------------------------------------------- WebSocket (RFC 6455, server side)


class WebSocketClosed(Exception):
    pass


class WebSocket:
    """The server end of one WebSocket connection: whole messages in, frames out."""

    def __init__(self, connection: socket.socket) -> None:
        self._socket = connection
        self._send_lock = threading.Lock()

    def _receive_exactly(self, count: int) -> bytes:
        data = bytearray()
        while len(data) < count:
            chunk = self._socket.recv(count - len(data))
            if not chunk:
                raise WebSocketClosed()
            data.extend(chunk)
        return bytes(data)

    def receive(self) -> Tuple[int, bytes]:
        """The next text (1) or binary (2) message; answers pings, raises WebSocketClosed at the end."""
        message = bytearray()
        message_opcode = 0
        while True:
            first, second = self._receive_exactly(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._receive_exactly(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._receive_exactly(8))[0]
            if not second & 0x80 or length > MAX_MESSAGE_BYTES:
                raise WebSocketClosed()  # browsers always mask; anything else is not a browser
            mask = self._receive_exactly(4)
            payload = self._unmask(self._receive_exactly(length), mask)
            if opcode == 0x8:
                with contextlib.suppress(OSError):
                    self.send(0x8, payload[:2])
                raise WebSocketClosed()
            if opcode == 0x9:
                self.send(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode in (0x1, 0x2):
                message_opcode = opcode
                message = bytearray()
            message.extend(payload)
            if len(message) > MAX_MESSAGE_BYTES:
                raise WebSocketClosed()
            if first & 0x80:  # FIN: the message is complete
                return message_opcode, bytes(message)

    @staticmethod
    def _unmask(payload: bytes, mask: bytes) -> bytes:
        if not payload:
            return payload
        # One big-integer XOR instead of a Python loop per byte: pastes can be megabytes.
        repeated = (mask * (len(payload) // 4 + 1))[: len(payload)]
        value = int.from_bytes(payload, "little") ^ int.from_bytes(repeated, "little")
        return value.to_bytes(len(payload), "little")

    def send(self, opcode: int, payload: bytes) -> None:
        length = len(payload)
        if length < 126:
            header = struct.pack("!BB", 0x80 | opcode, length)
        elif length < 65536:
            header = struct.pack("!BBH", 0x80 | opcode, 126, length)
        else:
            header = struct.pack("!BBQ", 0x80 | opcode, 127, length)
        with self._send_lock:
            self._socket.sendall(header + payload)

    def send_json(self, message: Dict[str, Any]) -> None:
        self.send(0x1, json.dumps(message).encode("utf-8"))

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self.send(0x8, struct.pack("!H", 1000))
        with contextlib.suppress(OSError):
            self._socket.shutdown(socket.SHUT_RDWR)


# ---------------------------------------------------------------- session


class Session:
    """The running command, the connected pages and what a newly connected page needs to know."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.console: Optional[PseudoConsole] = None  # started once the first page reported its size
        self.first_size: Optional[Tuple[int, int]] = None
        self.size_known = threading.Event()
        self.lock = threading.Lock()
        self.clients: Set[WebSocket] = set()
        self.history = bytearray()
        self.ever_connected = threading.Event()
        self.last_disconnect = time.monotonic()
        self.output_done = threading.Event()
        self.exit_code: Optional[int] = None
        self.icon_path: str = config.get("icon", "")
        self.icon_version = 0
        self.colors: Dict[str, str] = {}
        self.window_ready = threading.Event()
        self.window = 0  # the browser window of the page, once found (find_window)
        self.front_on_input = False  # the page's switch "bring to front when input is needed"
        self._ui_lock = threading.Lock()
        self._ui_offset = 0
        self._ui_pending = b""  # an incomplete last line

    # -- output

    def pump_output(self, console: PseudoConsole) -> None:
        """Copy the pseudoconsole's output to every page and into the history, until it closes."""
        try:
            while True:
                data = console.read()
                if not data:
                    break
                with self.lock:
                    self.history.extend(data)
                    if len(self.history) > HISTORY_LIMIT:
                        # Cut after a line break, so the replay does not start inside an escape sequence.
                        cut = self.history.find(b"\n", len(self.history) - HISTORY_LIMIT)
                        del self.history[: cut + 1 if cut >= 0 else len(self.history) - HISTORY_LIMIT]
                    clients = list(self.clients)
                for client in clients:
                    self._send(client, lambda c=client, d=data: c.send(0x2, d))
        finally:
            self.output_done.set()

    def broadcast(self, message: Dict[str, Any]) -> None:
        with self.lock:
            clients = list(self.clients)
        for client in clients:
            self._send(client, lambda c=client: c.send_json(message))

    def _send(self, client: WebSocket, action: Callable[[], None]) -> None:
        try:
            action()
        except OSError:
            self.disconnect(client)
            client.close()

    # -- pages

    def connect(self, client: WebSocket) -> None:
        """Bring a new page up to date: settings, the output so far, and whether its window is known."""
        hello: Dict[str, Any] = {
            "t": "hello",
            "iconVersion": self.icon_version,
            "colors": self.colors,
            "ready": self.window_ready.is_set(),
        }
        with self.lock:
            client.send_json(hello)
            if self.history:
                client.send(0x2, bytes(self.history))
            self.clients.add(client)
            first = not self.ever_connected.is_set()
            self.ever_connected.set()
        if self.exit_code is not None and self.output_done.is_set():
            client.send_json({"t": "exit", "code": self.exit_code})
        if first:
            threading.Thread(target=self.find_window, daemon=True).start()

    def disconnect(self, client: WebSocket) -> None:
        with self.lock:
            if client in self.clients:
                self.clients.discard(client)
                self.last_disconnect = time.monotonic()

    def handle_message(self, opcode: int, payload: bytes) -> None:
        """Keyboard input, pastes and size changes from a page."""
        if opcode != 0x1:
            return
        message = json.loads(payload.decode("utf-8"))
        kind = message.get("t")
        console = self.console  # None until the command runs: typing before that is dropped
        if kind == "i" and isinstance(message.get("d"), str) and console:
            console.write(message["d"].encode("utf-8"))
        elif kind == "b" and isinstance(message.get("d"), str) and console:
            # xterm.js's binary input (some mouse reports): one character per byte.
            console.write(message["d"].encode("latin-1", errors="replace"))
        elif kind == "r":
            columns, rows = message.get("c"), message.get("r")
            if isinstance(columns, int) and isinstance(rows, int):
                if console:
                    console.resize(columns, rows)
                elif not self.size_known.is_set():
                    self.first_size = (columns, rows)
                    self.size_known.set()
        elif kind == "p":
            # The page's preferences that the host acts on.
            self.front_on_input = message.get("frontOnInput") is True
        elif kind == "o" and isinstance(message.get("path"), str):
            # A clicked file path in the output (e.g. a traceback line).
            line = message.get("line")
            try:
                open_in_editor(message["path"], line if isinstance(line, int) and line > 0 else None)
            except Exception:
                report_ignored("browser terminal: open a file from the output")

    # -- the browser window

    def find_window(self) -> None:
        """Find the page's top-level window by the unique title it shows first.

        The new tab's browser window is brought to the front, and its handle is written to
        config "window_file" for other programs (e.g. to bring it to the front later). Then the
        page is told to show the real title.
        """
        marker = self.config["marker"]
        deadline = time.monotonic() + 20
        found = 0
        while not found and time.monotonic() < deadline:
            found = _window_with_title_containing(marker)
            if not found:
                time.sleep(0.05)
        if found:
            self.window = found
            try:
                bring_to_front(found)
            except Exception:
                report_ignored("browser terminal: bring the browser to the front")
            try:
                Path(self.config["window_file"]).write_text(json.dumps({"hwnd": found}), encoding="utf-8")
            except OSError:
                report_ignored("browser terminal: write the window handle")
        self.window_ready.set()
        self.broadcast({"t": "ready"})

    # -- side channel from the launcher processes in the console

    def follow_ui_requests(self, path: Path) -> None:
        """Apply the icon and color requests that console_tools appends to the UI file, until the end."""
        while not self.output_done.is_set():
            time.sleep(0.15)
            self.read_ui_requests(path)

    def read_ui_requests(self, path: Path) -> None:
        """Apply the requests added since the last call (also called once more at the end, so none is lost)."""
        with self._ui_lock:
            try:
                with path.open("rb") as stream:
                    stream.seek(self._ui_offset)
                    data = stream.read()
            except OSError:  # not created yet
                return
            self._ui_offset += len(data)
            *lines, self._ui_pending = (self._ui_pending + data).split(b"\n")
            for line in lines:
                try:
                    self._apply_ui_request(json.loads(line.decode("utf-8")))
                except (ValueError, AttributeError):
                    report_ignored("browser terminal: UI request")

    def _apply_ui_request(self, request: Dict[str, Any]) -> None:
        icon = request.get("icon")
        if isinstance(icon, str) and Path(icon).suffix.lower() in ICON_TYPES:
            self.icon_path = icon
            self.icon_version += 1
            self.broadcast({"t": "icon", "v": self.icon_version})
        colors = request.get("colors")
        if isinstance(colors, dict):
            self.colors = {key: value for key, value in colors.items() if key in ("background", "foreground")}
            self.broadcast({"t": "colors", "colors": self.colors})
        if request.get("input") is True:
            # The program waits for input: the page shows it, and comes to the front if wanted.
            self.broadcast({"t": "input"})
            if self.front_on_input and self.window:
                try:
                    bring_to_front(self.window)
                except Exception:
                    report_ignored("browser terminal: bring the page to the front for input")
        notify = request.get("notify")
        if isinstance(notify, str) and notify:
            # The page shows it if notifications are on and nobody is looking at it.
            self.broadcast({"t": "notify", "text": notify[:300], "failed": bool(request.get("failed"))})


def _window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _window_with_title_containing(text: str) -> int:
    """A visible top-level window whose title contains text (a browser adds its own name), or 0."""
    found: List[int] = []

    def visit(hwnd: int, _: int) -> bool:
        if user32.IsWindowVisible(hwnd) and text in _window_title(hwnd):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(WNDENUMPROC(visit), 0)
    return found[0] if found else 0


def bring_to_front(hwnd: int) -> None:
    """Restore and activate the browser window that shows the new tab.

    Windows lets only the foreground process activate windows; this host runs hidden, so the
    browser would at most flash in the taskbar. A short Alt key press lifts that lock for the
    next SetForegroundWindow, as when the user clicks.
    """
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    if user32.SetForegroundWindow(hwnd):
        return
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    user32.SetForegroundWindow(hwnd)


# ---------------------------------------------------------------- HTTP


def make_handler(session: Session, token: str, hosts: Set[str]) -> type:
    """A request handler class bound to this session; every path starts with /<token>/.

    hosts: the accepted values of the Host header ("name:port"), filled in once the port is known.
    """
    prefix = "/" + token + "/"

    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "BrowserTerminal"
        sys_version = ""

        # typing.override requires Python 3.12; keep this override dependency-free on 3.8.
        def log_message(self, format: str, *args: Any) -> None:  # pyrefly: ignore[missing-override-decorator]
            """No request log: this process's output goes to the run's bootstrap.log."""

        def _host(self) -> str:
            """The Host header when it names this server, else "".

            Any other name would be a web page that uses DNS rebinding to reach this port.
            """
            host = self.headers.get("Host", "")
            return host if host in hosts else ""

        def _reply(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                f"font-src 'self' data:; connect-src ws://{self._host()}; base-uri 'none'; form-action 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if not self._host():
                self._reply(404, b"Not found", "text/plain")
                return
            if not self.path.startswith(prefix):
                # E.g. a bookmark without the key: say what is missing, never what the key is.
                self._reply(404, b"Not found. Open the terminal's full address, including its key.", "text/plain")
                return
            name = self.path[len(prefix) :].split("?", 1)[0]
            if name in ("", "index.html"):
                self._reply(200, self._page(), "text/html; charset=utf-8")
            elif name in STATIC_FILES:
                self._reply(200, (STATIC_DIR / name).read_bytes(), STATIC_FILES[name])
            elif name == "icon":
                self._icon()
            elif name == "ws":
                self._websocket()
            else:
                self._reply(404, b"Not found", "text/plain")

        def _page(self) -> bytes:
            page = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
            settings = {
                key: session.config[key] for key in ("title", "marker", "theme", "font", "windowsBuild", "scroll")
            }
            settings["startLink"] = session.config["start_link"]
            # Inside <script type="application/json">: "</" must not end the element.
            data = json.dumps(settings).replace("</", "<\\/")
            return page.replace("__BROWSER_TERMINAL_CONFIG__", data).encode("utf-8")

        def _icon(self) -> None:
            path = Path(session.icon_path)
            content_type = ICON_TYPES.get(path.suffix.lower())
            try:
                body = path.read_bytes() if content_type else b""
            except OSError:
                body = b""
            if body and content_type:
                self._reply(200, body, content_type)
            else:
                self._reply(404, b"Not found", "text/plain")

        def _websocket(self) -> None:
            key = self.headers.get("Sec-WebSocket-Key", "")
            # Only this page may connect: a page of another site in the same browser sends its own Origin.
            if (
                self.headers.get("Upgrade", "").lower() != "websocket"
                or not self._host()
                or self.headers.get("Origin") != "http://" + self._host()
                or not key
            ):
                self._reply(403, b"Forbidden", "text/plain")
                return
            # RFC 6455 prescribes SHA-1 for this handshake value; it protects nothing.
            # (usedforsecurity=False would say so, but needs Python 3.9.)
            digest = hashlib.sha1((key + WEBSOCKET_GUID).encode("ascii")).digest()  # noqa: S324
            accept = base64.b64encode(digest).decode("ascii")
            self.send_response(101, "Switching Protocols")
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", accept)
            self.end_headers()
            self.wfile.flush()
            self.close_connection = True
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client = WebSocket(self.connection)
            try:
                session.connect(client)
                while True:
                    opcode, payload = client.receive()
                    try:
                        session.handle_message(opcode, payload)
                    except ValueError:  # also UnicodeDecodeError
                        report_ignored("browser terminal: message from the page")
            except (WebSocketClosed, OSError):
                pass
            finally:
                session.disconnect(client)
                client.close()

    return Handler


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    # Never share the port with another process (SO_REUSEADDR would allow that on Windows).
    allow_reuse_address = False


def start_server(port: int, handler: type) -> Server:
    """The server on 127.0.0.1: on port, else the next free of the following 20, else any free port.

    A fixed port keeps a bookmarked address valid; a second instance of the same program then
    gets the next one.
    """
    if port:
        for candidate in range(port, min(port + 21, 65536)):
            try:
                return Server(("127.0.0.1", candidate), handler)
            except OSError:  # in use
                continue
    return Server(("127.0.0.1", 0), handler)


# ---------------------------------------------------------------- browser


def open_browser(url: str, hidden_env_prefixes: Tuple[str, ...] = ()) -> None:
    """Open the page in a new tab of the default browser.

    A browser that was not running yet outlives this run and keeps the environment it was started
    with: variables starting with hidden_env_prefixes are left out of it.
    """
    import webbrowser

    hidden = tuple(prefix.upper() for prefix in hidden_env_prefixes)
    removed = {key: value for key, value in os.environ.items() if hidden and key.upper().startswith(hidden)}
    # webbrowser starts the browser through the Windows shell, which takes no environment of its
    # own; the variables leave this process's environment for that moment (the command's
    # environment was copied before).
    for key in removed:
        del os.environ[key]
    try:
        opened = webbrowser.open(url, new=2)  # 2: a new tab
    finally:
        os.environ.update(removed)
    if not opened:
        raise RuntimeError("No browser found to open the terminal page.")


# ---------------------------------------------------------------- main


def complete_config(config: Dict[str, Any], command: List[str]) -> Dict[str, Any]:
    """The configuration with every missing setting filled in. All settings are optional:

    title             page title until the command sets its own (default: the command's name)
    cwd               working folder of the command (default: the current one)
    icon              .ico or .png file shown as the page's icon
    theme, font       xterm.js theme (default: the classic console's palette) and {"family", "size"}
    scroll            lines per mouse wheel step, as a multiple of the browser's (default 5; Alt+wheel: 5x more)
    start_link        a link that starts the program (e.g. "my-tool://start"), offered by the page's
                      bookmark hint; the program that registers it fills it in (default: none)
    host_name         name in the address (default 127.0.0.1); a name ending in .localhost, e.g.
                      "my-tool.localhost", reaches this PC in Edge, Chrome and Firefox
    port              port to try first (default: any free one); when it is taken, the next free
                      one of the following 20, else any
    key               secret part of the address (default: a new random one per run); fix it, with
                      host_name and port, to make the address stable enough for a bookmark
    state_dir         folder for the files below (default: a new temporary folder)
    ui_file           the file of icon/color requests (ui.py); its path is in the variable ui_env_var
    window_file       where the handle of the browser window is written once it is found
    ui_env_var        name of that variable (default ui.ENV_VAR)
    hidden_env_prefixes   variables with these prefixes are not passed on to the browser
    """
    config = dict(config)
    if not config.get("state_dir"):
        import tempfile

        config["state_dir"] = tempfile.mkdtemp(prefix="browser-terminal-")
    state = Path(config["state_dir"])
    config.setdefault("title", Path(command[0]).stem if command else "Terminal")
    # Shown as the page's first title, until find_window() has found the browser window by it.
    config.setdefault("marker", f"{config['title']} [{secrets.token_hex(5)}]")
    config.setdefault("ui_file", str(state / "browser-ui.jsonl"))
    config.setdefault("window_file", str(state / "browser-window.json"))
    config.setdefault("ui_env_var", ui.ENV_VAR)
    config.setdefault("hidden_env_prefixes", [])
    config.setdefault("icon", "")
    config.setdefault("host_name", "127.0.0.1")
    config.setdefault("port", 0)
    if not config.get("key"):
        config["key"] = secrets.token_urlsafe(24)
    config["theme"] = {**ui.DEFAULT_THEME, **(config.get("theme") or {})}
    font = {"family": '"Cascadia Mono", Consolas, "Courier New", monospace', "size": 15}
    config["font"] = {**font, **(config.get("font") or {})}
    config.setdefault("windowsBuild", sys.getwindowsversion().build)
    config.setdefault("scroll", 5)
    config.setdefault("start_link", "")
    return config


def run(config: Dict[str, Any], command: List[str]) -> int:
    """Run command in a pseudoconsole shown in the browser; returns its exit code."""
    config = complete_config(config, command)
    ui_file = Path(config["ui_file"])
    env = dict(os.environ)
    env[config["ui_env_var"]] = str(ui_file)
    session = Session(config)
    hosts: Set[str] = set()
    server = start_server(int(config["port"]), make_handler(session, config["key"], hosts))
    port = server.server_address[1]
    hosts.update({f"{config['host_name']}:{port}", f"127.0.0.1:{port}"})
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=session.follow_ui_requests, args=(ui_file,), daemon=True).start()
    open_browser(f"http://{config['host_name']}:{port}/{config['key']}/", tuple(config["hidden_env_prefixes"]))
    # The command starts at the page's size (see INITIAL_COLUMNS).
    started = time.monotonic()
    connected_at = 0.0
    while not session.size_known.wait(0.1):
        if session.ever_connected.is_set():
            connected_at = connected_at or time.monotonic()
            if time.monotonic() - connected_at > FIRST_SIZE_SECONDS:
                break
        elif time.monotonic() - started > CONNECT_TIMEOUT_SECONDS:
            server.shutdown()
            user32.MessageBoxW(
                None,
                "The browser did not open the terminal page in time, so the program was not started.",
                config["title"],
                MB_ICONERROR,
            )
            return 1
    columns, rows = session.first_size or (INITIAL_COLUMNS, INITIAL_ROWS)
    console = PseudoConsole(command, env, columns, rows, config.get("cwd"))
    session.console = console
    threading.Thread(target=session.pump_output, args=(console,), daemon=True).start()
    code: Optional[int] = None
    while code is None:
        code = console.wait(0.25)
        if code is not None:
            break
        with session.lock:
            connected = bool(session.clients)
            last_disconnect = session.last_disconnect
        if not connected and time.monotonic() - last_disconnect > RECONNECT_GRACE_SECONDS:
            # The window was closed: end the program like a closed console window does.
            _end_unseen(console)
            return 1
    # The command ended. Closing the pseudoconsole flushes its last output; then the pages hear about it.
    session.exit_code = code
    console.close()
    session.output_done.wait(5)
    session.read_ui_requests(ui_file)
    session.broadcast({"t": "exit", "code": code})
    _close_pages(session)
    server.shutdown()
    return code


def _end_unseen(console: PseudoConsole) -> None:
    """End a program nobody can see: close its console and wait for its processes to react."""
    console.close()
    if console.wait(CLOSE_WAIT_SECONDS) is None:
        kernel32.TerminateProcess(console.process, 1)


def _close_pages(session: Session) -> None:
    """Give the pages a moment to close their tabs themselves (window.close()) before the server stops."""
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        with session.lock:
            if not session.clients:
                return
        time.sleep(0.05)


def main(argv: Optional[List[str]] = None) -> int:
    """Command line: [--config FILE] [--title TEXT] [--cwd DIR] [--host-name NAME] [--port N] [--key TEXT] [-- COMMAND ...]."""
    import argparse

    arguments = list(sys.argv[1:] if argv is None else argv)
    command: List[str] = []
    if "--" in arguments:
        index = arguments.index("--")
        arguments, command = arguments[:index], arguments[index + 1 :]
    parser = argparse.ArgumentParser(
        prog="browser_terminal",
        description="Run a console program in a terminal in the browser (default: the command prompt).",
        epilog="Example: python browser_terminal --title Python -- python -i",
    )
    parser.add_argument("--config", help="JSON file with settings (see complete_config in host.py)")
    parser.add_argument("--title", help="page title until the program sets its own")
    parser.add_argument("--cwd", help="working folder of the program")
    parser.add_argument("--host-name", help='name in the address, e.g. "my-tool.localhost" (default 127.0.0.1)')
    parser.add_argument("--port", type=int, help="port to use if free (default: any free port)")
    parser.add_argument("--key", help="secret part of the address (default: a new random one)")
    options = parser.parse_args(arguments)
    config: Dict[str, Any] = {}
    if options.config:
        config = json.loads(Path(options.config).read_text(encoding="utf-8"))
    for key in ("title", "cwd", "host_name", "port", "key"):
        if getattr(options, key):
            config[key] = getattr(options, key)
    command = command or [os.environ.get("COMSPEC", "cmd.exe")]
    try:
        return run(config, command)
    except Exception:
        traceback.print_exc()
        user32.MessageBoxW(
            None,
            "The browser terminal failed:\n\n" + traceback.format_exc(limit=3),
            config.get("title") or "Browser terminal",
            MB_ICONERROR,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
