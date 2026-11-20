# Step 5 of a start (see B/W.bat for the first steps). The watchdog (runtime/bg_watchdog.py) starts
# this file with the APP's Python, the one with your packages. It prepares the output and logging,
# then runs code/main.py as if it had been started directly, and finally writes how it ended:
# result.json (the exit code) and, after an error, traceback.json (the crash report).
"""Run main.py with isolated arguments, mirrored logging and serialized exit reports.

Runs inside the application's interpreter, so it must work on every Python the
launcher supports (3.8+): standard library only, no "X | Y" types at runtime, no
match statements, no parenthesized context managers.
"""

from __future__ import annotations

import codecs
import contextlib
import io
import json
import os
import re
import runpy
import sys
import threading
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import Any, Callable, Dict, List, Optional, TextIO, Tuple, TypeVar, Union

# The protocol module lives next to this file; import it before sys.path[0]
# is switched to the application's folder. It stays in sys.modules as "_pyapp",
# a name that cannot shadow the application's own modules.
try:
    import _pyapp as protocol
except Exception:  # the watchdog shows this output, also for launches without a terminal
    import traceback

    traceback.print_exc()
    sys.exit(3)  # WrapperExit.INIT_FAILED: the protocol module itself failed to load

log_file = None
report_path = None
result_path = None

# ------------------------------------------------------------ logging

_ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\)|[@-Z\\-_])")


def _format_prepend(fmt: Optional[str]) -> str:
    """Current local time in the configured prefix format, or ""."""
    return datetime.now().astimezone().strftime(fmt) if fmt else ""


class _BinarySplitter:
    """Mirror binary writes to the original stream and an incrementally decoded text log."""

    def __init__(self, owner: PipeSplitter) -> None:
        self.owner = owner
        self.decoder = codecs.getincrementaldecoder(owner.encoding or "utf-8")("replace")

    def write(self, data: Union[bytes, bytearray]) -> int:
        if data and self.owner.on_output is not None:
            self.owner.on_output()
        _take_native_output()
        with self.owner._lock:
            target = getattr(self.owner.print_stream, "buffer", None)
            if target is not None:
                target.write(data)
            else:
                self.owner._write_console(data.decode(self.owner.encoding or "utf-8", "replace"))
            if self.owner.log_stream is not None:
                self.owner.log_stream.write(self.decoder.decode(data))
            self.owner.flush()
        return len(data)

    def flush(self) -> None:
        self.owner.flush()

    def __getattr__(self, name: str) -> Any:
        stream = self.owner.print_stream
        if stream is None:
            raise AttributeError(name)
        return getattr(stream.buffer, name)


class PipeSplitter:
    """Mirror text to the console stream and an optional log, with per-line time prefixes."""

    def __init__(
        self,
        print_stream: Optional[TextIO],
        log_stream: Optional[TextIO] = None,
        print_timestamp_format: Optional[str] = "",
        log_timestamp_format: Optional[str] = "",
        input_timestamp_format: Optional[str] = "",
        log_input_timestamp_format: Optional[str] = "",
        print_red: bool = False,
    ) -> None:
        self.print_stream = print_stream
        self.log_stream = log_stream
        self.print_timestamp_format = print_timestamp_format
        self.log_timestamp_format = log_timestamp_format
        self.input_timestamp_format = input_timestamp_format
        self.log_input_timestamp_format = log_input_timestamp_format
        self.print_red = print_red
        self.buffer = _BinarySplitter(self)
        self._at_line_start = True
        self._lock = threading.RLock()
        self.on_output: Optional[Callable[[], None]] = None
        self.browser_preferences: Optional[Path] = None
        self._preference_stamp = -1
        self._print_prefix = True
        self._input_prefix = True

    def _console_prepend(self, fmt: Optional[str], *, for_input: bool = False) -> str:
        """Refresh browser preferences only when changed; preserve configured log prefixes."""
        if self.browser_preferences is not None:
            try:
                stamp = self.browser_preferences.stat().st_mtime_ns
                if stamp != self._preference_stamp:
                    values = json.loads(self.browser_preferences.read_text(encoding="utf-8"))
                    if isinstance(values, dict):
                        if isinstance(values.get("printPrefix"), bool):
                            self._print_prefix = values["printPrefix"]
                        if isinstance(values.get("inputPrefix"), bool):
                            self._input_prefix = values["inputPrefix"]
                    self._preference_stamp = stamp
            except (OSError, ValueError):
                pass  # A preference never interrupts application output.
        enabled = self._input_prefix if for_input else self._print_prefix
        return _format_prepend(fmt) if enabled else ""

    def _write_console(self, text: str) -> None:
        """A hidden/pythonw launch can have no original console stream."""
        if self.print_stream is not None:
            self.print_stream.write(text)

    def _supports_color(self) -> bool:
        return bool(getattr(self.print_stream, "isatty", lambda: False)())

    def write(self, data: object) -> int:
        if data is None:
            data = ""
        if not isinstance(data, str):
            data = str(data)
        if data == "":
            return 0
        if self.on_output is not None:
            self.on_output()
        _take_native_output()
        with self._lock:
            for part in data.splitlines(True) or [data]:
                if self._at_line_start:
                    prefix = self._console_prepend(self.print_timestamp_format)
                    if prefix:
                        self._write_console(prefix)
                    log_prefix = _format_prepend(self.log_timestamp_format)
                    if self.log_stream is not None and log_prefix:
                        self.log_stream.write(log_prefix)
                    if self.print_red and self._supports_color():
                        self._write_console("\x1b[31m")
                self._write_console(part)
                if self.log_stream is not None:
                    self.log_stream.write(_ANSI_ESCAPE.sub("", part))
                if part.endswith("\n"):
                    if self.print_red and self._supports_color():
                        self._write_console("\x1b[0m")
                    self._at_line_start = True
                else:
                    self._at_line_start = False
            self.flush()
        return len(data)

    def write_input_prompt(self, prompt: object) -> None:
        prompt = "" if prompt is None else str(prompt)
        if prompt and self.on_output is not None:
            self.on_output()
        _take_native_output()
        with self._lock:
            self._write_console(self._console_prepend(self.input_timestamp_format, for_input=True) + prompt)
            if self.log_stream is not None:
                self.log_stream.write(_format_prepend(self.log_input_timestamp_format) + _ANSI_ESCAPE.sub("", prompt))
            self._at_line_start = prompt.endswith("\n")
            self.flush()

    def write_native(self, data: bytes, log_text: str) -> None:
        """Output written below Python (see NativeOutput): unchanged to the console, as text to the log."""
        if data and self.on_output is not None:
            self.on_output()
        with self._lock:
            target = getattr(self.print_stream, "buffer", None)
            if target is not None:
                target.write(data)
            elif data:
                self._write_console(data.decode(self.encoding or "utf-8", "replace"))
            if self.log_stream is not None:
                for part in log_text.splitlines(True):
                    log_prefix = _format_prepend(self.log_timestamp_format) if self._at_line_start else ""
                    self.log_stream.write(log_prefix + _ANSI_ESCAPE.sub("", part))
                    self._at_line_start = part.endswith("\n")
            self.flush()

    def complete_input_line(self, text: str) -> None:
        with self._lock:
            if self.log_stream is not None:
                self.log_stream.write(text + "\n")
            self._at_line_start = True
            self.flush()

    def flush(self) -> None:
        with self._lock:
            if hasattr(self.print_stream, "flush"):
                self.print_stream.flush()
            if self.log_stream is not None:
                self.log_stream.flush()

    def isatty(self) -> bool:
        return self._supports_color()

    def writable(self) -> bool:
        return True

    def fileno(self) -> int:
        if hasattr(self.print_stream, "fileno"):
            return self.print_stream.fileno()
        raise OSError("The underlying stream has no file descriptor")

    @property
    def encoding(self) -> Optional[str]:
        return getattr(self.print_stream, "encoding", None)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.print_stream, name)


class NativeOutput:
    """Output that bypasses sys.stdout/sys.stderr: C extensions, os.write, child processes.

    Such output goes to the process's file descriptors 1 and 2 (and the Windows standard handles,
    which os.dup2 updates), not through the Python streams that write the log. They are pointed at
    the raw output file next to the log, and new bytes from it are passed on to the console and
    the log: right before every Python write, so the log keeps the order of both, and every
    50 ms otherwise. The file is on disk, so it still holds the last output after a hard crash.
    """

    def __init__(self, raw_path: str) -> None:
        sys.stdout.flush()
        sys.stderr.flush()
        # Copies of the console (the watchdog's pipe), for Python's own output and to restore later.
        self.console_fds = (os.dup(1), os.dup(2))
        with Path(raw_path).open("wb", buffering=0) as raw:
            os.dup2(raw.fileno(), 1)
            os.dup2(raw.fileno(), 2)
        self.reader = Path(raw_path).open("rb")  # noqa: SIM115 - closed by finish()
        self.target: Optional[PipeSplitter] = None
        self.pending = b""  # an incomplete last line, held back from the log until it ends
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._poll, name="pyapp-native-output", daemon=True)

    def console_stream(self, index: int) -> TextIO:
        """A text stream to the console like the original sys.stdout/sys.stderr (with \\r\\n line ends)."""
        return io.TextIOWrapper(
            io.open(self.console_fds[index], "wb", closefd=False),  # noqa: UP020 - a raw descriptor
            encoding="utf-8",
            errors="backslashreplace",
        )

    def start(self, target: PipeSplitter) -> None:
        self.target = target
        self.thread.start()

    def _poll(self) -> None:
        while not self.stopped.wait(0.05):
            self.take()

    def take(self, final: bool = False) -> None:
        """Pass on what was written since the last call; final: also an unfinished last line."""
        with self.lock:
            if self.reader.closed:  # after finish(): a late write through a kept reference to the splitter
                return
            data = self.reader.read()
            if self.target is None or not (data or (final and self.pending)):
                return
            text = self.pending + data
            end = text.rfind(b"\n") + 1
            if final:
                end = len(text)
            self.pending = text[end:]
            self.target.write_native(data, _decode_native(text[:end]))

    def finish(self) -> None:
        """Pass on the rest, then give the console back to the file descriptors."""
        self.stopped.set()
        self.take(final=True)
        self.reader.close()
        os.dup2(self.console_fds[0], 1)
        os.dup2(self.console_fds[1], 2)


def _decode_native(data: bytes) -> str:
    """Native output has no declared encoding: UTF-8 if it is valid, else the Windows ANSI code page.

    Line ends become "\\n", like Python's own prints: the log is a text stream that writes each
    "\\n" as "\\r\\n" itself, so a native "\\r\\n" would otherwise end up as "\\r\\r\\n".
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("mbcs" if os.name == "nt" else "latin-1", "replace")
    return text.replace("\r\n", "\n")


native_output: Optional[NativeOutput] = None


def _take_native_output() -> None:
    if native_output is not None:
        native_output.take()


def setup_log_prints(
    log_path: Optional[str],
    print_prepend: Optional[str],
    log_print_prepend: Optional[str],
    input_prepend: Optional[str],
    log_input_prepend: Optional[str],
    native_output_path: Optional[str] = None,
) -> None:
    """Install stdout/stderr splitters and point faulthandler at the log.

    With native_output_path (only together with a log), output that bypasses the Python streams
    is captured there and merged into the log as well (see NativeOutput).
    """
    import atexit
    import faulthandler

    global log_file, native_output
    if log_path:
        folder = str(Path(log_path).parent)
        if folder:
            Path(folder).mkdir(parents=True, exist_ok=True)
        # The application-wide log stream is closed by _finish_logging after all exit callbacks.
        # Appending: the watchdog has already written its "Started ..." note (each run has its own log).
        log_file = Path(log_path).open("a", encoding="utf-8", buffering=1)  # noqa: SIM115
    # Registered before the application's callbacks, so it runs after them.
    atexit.register(_finish_logging)
    common = {
        "print_timestamp_format": print_prepend,
        "log_timestamp_format": log_print_prepend,
        "input_timestamp_format": input_prepend,
        "log_input_timestamp_format": log_input_prepend,
    }
    console_out: Optional[TextIO] = sys.__stdout__
    console_err: Optional[TextIO] = sys.__stderr__
    if log_file is not None and native_output_path:
        native_output = NativeOutput(native_output_path)
        console_out, console_err = native_output.console_stream(0), native_output.console_stream(1)
    sys.stdout = PipeSplitter(console_out, log_file, **common)
    sys.stderr = PipeSplitter(console_err, log_file, print_red=True, **common)
    if native_output is not None:
        native_output.start(sys.stdout)
    if log_file is not None:
        faulthandler.enable(file=log_file, all_threads=True)
    else:
        faulthandler.enable(all_threads=True)


def _finish_logging() -> None:
    import faulthandler

    try:
        sys.stdout.flush()
        sys.stderr.flush()
        if native_output is not None:
            native_output.finish()
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        if log_file is not None:
            faulthandler.disable()
            log_file.close()


def install_input_prefix(input_prepend: Optional[str], browser_ui: str = "") -> None:
    """input() bypasses sys.stdout's prefixing, so wrap it.

    browser_ui: in the browser terminal, the file of its UI requests: each input() announces
    that the program waits for input there (the page can then come to the front).
    """
    import builtins

    original_input = builtins.input

    def input_with_prepend(prompt: object = "") -> str:
        if browser_ui:
            try:
                with Path(browser_ui).open("a", encoding="utf-8") as stream:
                    stream.write('{"input": true}\n')
            except OSError:
                pass  # cosmetic: the input itself must work
        if hasattr(sys.stdout, "write_input_prompt"):
            sys.stdout.write_input_prompt(prompt)
            text = original_input("")
        else:
            text = original_input(_format_prepend(input_prepend) + str(prompt))
        if hasattr(sys.stdout, "complete_input_line"):
            sys.stdout.complete_input_line(text)
        return text

    builtins.input = input_with_prepend


# ------------------------------------------------------------ reports

_ExitFunction = TypeVar("_ExitFunction", bound=Callable[..., object])


def capture_legacy_atexit_errors(record: Callable[[BaseException], None]) -> None:
    """Record errors from callbacks registered after setup on Python 3.8/3.9.

    Keep execution in the native atexit registry so shutdown ordering is unchanged.
    Wrapped callbacks compare like their originals because unregister() uses equality.
    """
    import atexit
    from functools import wraps

    original_register = atexit.register

    class ExitCallback:
        def __init__(self, function: Callable[..., object]) -> None:
            self.function = function

        def __call__(self, *args: object, **kwargs: object) -> object:
            try:
                return self.function(*args, **kwargs)
            except BaseException as error:
                record(error)
                raise

        def __eq__(self, other: object) -> bool:
            return self.function == other

        def __hash__(self) -> int:
            return hash(self.function)

        def __repr__(self) -> str:
            return repr(self.function)

    @wraps(original_register)
    def register(function: _ExitFunction, /, *args: object, **kwargs: object) -> _ExitFunction:
        if not callable(function):
            raise TypeError("the first argument must be callable")
        original_register(ExitCallback(function), *args, **kwargs)
        return function

    # Python 3.8 cannot annotate the ParamSpec signature used by modern atexit stubs.
    # Install the compatibility shim through the module namespace; its return identity and
    # native callback argument handling are preserved above.
    vars(atexit)["register"] = register


def save_result(code: int) -> None:
    """Atomic completion marker; its absence tells the watchdog the interpreter died abruptly."""
    if result_path:
        import json

        with Path(result_path + ".tmp").open("w", encoding="utf-8") as stream:
            json.dump({"wrapper_exit_code": code}, stream)
        Path(result_path + ".tmp").replace(result_path)


def capture_background_errors(
    script_path: str, output_path: str, app_root: Optional[str], context_lines: Tuple[int, int]
) -> Callable[[], Optional[BaseException]]:
    """Record the first unhandled worker-thread, Tkinter callback or atexit callback error."""
    first_error: List[Optional[BaseException]] = [None]
    lock = threading.Lock()
    previous_last = getattr(sys, "last_exc", getattr(sys, "last_value", None))

    def record(error: BaseException) -> None:
        if isinstance(error, SystemExit) and protocol.exit_code_is_success(error.code):
            return
        with lock:
            if first_error[0] is not None:
                return
            first_error[0] = error
            protocol.save_report(error, script_path, output_path, app_root, context_lines)

    previous_hook = getattr(threading, "excepthook", None)
    if previous_hook is not None:

        def thread_hook(args: threading.ExceptHookArgs) -> None:
            try:
                if args.exc_value is not None:
                    record(args.exc_value)
            finally:
                previous_hook(args)

        threading.excepthook = thread_hook

    # An exception in an atexit callback (e.g. a final save) leaves the exit code at 0. Python 3.10+
    # passes it to sys.unraisablehook, so it can be recorded like a late worker-thread error, which
    # the watchdog then reports as a failure. Older versions need registration wrappers instead.
    # Other ignored errors (e.g. in __del__) stay non-fatal, as before.
    if sys.version_info < (3, 10):
        capture_legacy_atexit_errors(record)
    previous_unraisable_hook = getattr(sys, "unraisablehook", None)
    if previous_unraisable_hook is not None:

        def unraisable_hook(unraisable: sys.UnraisableHookArgs) -> None:
            try:
                in_atexit = (unraisable.err_msg or "").startswith("Exception ignored in atexit callback")
                if in_atexit and unraisable.exc_value is not None:
                    record(unraisable.exc_value)
            finally:
                previous_unraisable_hook(unraisable)

        sys.unraisablehook = unraisable_hook

    def pending_error() -> Optional[BaseException]:
        # Tkinter's default report_callback_exception stores the error in sys.last_*.
        last = getattr(sys, "last_exc", getattr(sys, "last_value", None))
        if isinstance(last, BaseException) and last is not previous_last:
            record(last)
        return first_error[0]

    return pending_error


def request_foreground(browser_ui: str) -> None:
    """Best-effort terminal attention, without importing the launcher into the app interpreter."""
    if browser_ui:
        with Path(browser_ui).open("a", encoding="utf-8") as stream:
            stream.write('{"foreground": true}\n')
        return
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel.GetConsoleWindow.restype = wintypes.HWND
    user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user.SetForegroundWindow.argtypes = [wintypes.HWND]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    hwnd = kernel.GetConsoleWindow()
    # A pseudoconsole's hidden message window is not the Windows Terminal window: never show it.
    if hwnd and user.IsWindowVisible(hwnd):
        user.ShowWindow(hwnd, 9)  # SW_RESTORE also restores a minimized console.
        user.SetForegroundWindow(hwnd)


def first_output_callback(browser_ui: str) -> Callable[[], None]:
    """One shared attempt for stdout/stderr, even when different threads write concurrently."""
    lock = threading.Lock()
    done = False

    def foreground_once() -> None:
        nonlocal done
        with lock:
            if done:
                return
            done = True
        # Attention is cosmetic: it must never prevent printing or recursively print an error.
        with contextlib.suppress(Exception):
            request_foreground(browser_ui)

    return foreground_once


# ------------------------------------------------------------ main


def confirm_keyboard_interrupt(program_name: str) -> bool:
    """Ask through Windows UI, avoiding reentrant stdin/stdout operations inside a signal handler."""
    if os.name != "nt":
        return True  # The managed launcher is Windows-only; do not strand a direct non-Windows run.
    import ctypes
    from ctypes import wintypes

    user = ctypes.WinDLL("user32", use_last_error=True)
    user.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
    answer = user.MessageBoxW(None, f"Stop {program_name}?", program_name, 4 | 0x20 | 0x100 | 0x10000)
    if not answer:
        raise ctypes.WinError(ctypes.get_last_error())
    return answer == 6  # IDYES; No is the default button.


def install_keyboard_interrupt_policy(action: str, program_name: str, stop_request: str = "") -> None:
    """Apply Ctrl+C policy before app code; explicit Stop requests bypass ignore/confirmation.

    Only SIGINT is handled: explicit raise KeyboardInterrupt and app-installed handlers retain
    their normal meaning. A second Ctrl+C while the native dialog is open does not open another.
    """
    import signal

    if action == "interrupt":
        signal.signal(signal.SIGINT, signal.default_int_handler)
        return
    if action not in ("ignore", "confirm"):
        raise ValueError("Unknown keyboard_interrupt_action: " + action)
    prompting = False

    def handle(_signum: int, _frame: Optional[FrameType]) -> None:
        nonlocal prompting
        if stop_request and Path(stop_request).is_file():
            raise KeyboardInterrupt
        if action == "ignore" or prompting:
            return
        prompting = True
        try:
            try:
                confirmed = confirm_keyboard_interrupt(program_name)
            except OSError:
                confirmed = True  # A failed dialog must not make it impossible to interrupt.
            if confirmed:
                raise KeyboardInterrupt
        finally:
            prompting = False

    signal.signal(signal.SIGINT, handle)


def register_app_api(config: Dict[str, Any], script_path: str, app_root: str, context_lines: Tuple[int, int]) -> None:
    """Make "import pyapp_api" give main.py the launcher's helpers (DONT_CHANGE/app_api.py).

    Registered in sys.modules under that name, so it works from any folder and needs no file in
    the app. Missing (e.g. a test copy without the launcher): main.py simply cannot import it.
    """
    try:
        from pyapp.DONT_CHANGE import app_api
    except Exception:
        return
    app_api._launched = True
    app_api._launch.update(
        launch_mode=config.get("launch_mode", ""),
        app_id=config.get("shortcut_app_id", ""),
        script=script_path,
        app_root=app_root,
        context_lines=list(context_lines),
    )
    sys.modules.setdefault("pyapp_api", app_api)
    if os.name == "nt":
        try:
            import ctypes

            def on_close(event: int) -> int:
                # 2 = CTRL_CLOSE_EVENT (the window's X): Windows ends this process a few seconds
                # after this returns, so the callbacks run here, in the handler's own thread.
                if event == 2:
                    run_stop_callbacks()
                return 0

            global _close_handler
            _close_handler = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(on_close)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(_close_handler, True)
        except Exception:  # noqa: S110 - nothing to report to the app; on_stop then covers Stop and Ctrl+C
            pass


_close_handler: Optional[object] = None  # kept referenced: ctypes would free a collected callback


def run_stop_callbacks() -> None:
    """Run the callbacks main.py registered with pyapp_api.on_stop (after a requested stop)."""
    app_api = sys.modules.get("pyapp_api")
    if app_api is not None and hasattr(app_api, "_run_stop_callbacks"):
        app_api._run_stop_callbacks()


def main() -> None:
    """Load the launch configuration, prepare logging and argv, then run main.py as __main__."""
    global report_path, result_path
    import json

    # --- 1. Read wrapper.json, which the watchdog wrote into the run folder.
    if len(sys.argv) != 3 or sys.argv[1] != "--config":
        raise SystemExit("script_wrapper.py is started by the launcher with --config <file>.")
    with Path(sys.argv[2]).open(encoding="utf-8") as stream:
        config = json.load(stream)
    script_path = config["script"]
    report_path = config["traceback"]
    result_path = config["result"]
    ready_path = config.get("ready")
    app_root = config.get("app_root") or str(Path(script_path).parent)
    context_lines = (int(config.get("traceback_lines_before", 3)), int(config.get("traceback_lines_after", 3)))
    print_prepend = config.get("print_prepend") or ""
    input_prepend = config.get("input_prepend") or ""
    log_print_prepend = config.get("log_print_prepend") or ""
    log_input_prepend = config.get("log_input_prepend") or ""
    log_path = config.get("log_path") or ""
    for key in list(os.environ):  # launcher protocol is not an application API
        if key.startswith("PYAPP_"):
            os.environ.pop(key, None)

    # --- 2. Make main.py see the world as if it had been started directly: its own path and
    # arguments in sys.argv, the launcher's private variables removed, output prepared for the log.
    sys.argv = [script_path, *list(config.get("args", []))]
    # With logging, stdout/stderr are pipes that would use the legacy ANSI code page and fail on
    # characters like "\u65e5"; the watchdog reads them as UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            if isinstance(stream, io.TextIOWrapper) and not stream.isatty():
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass
    foreground_on_first_print = bool(config.get("foreground_on_first_print"))
    if (
        log_path
        or print_prepend
        or log_print_prepend
        or input_prepend
        or log_input_prepend
        or foreground_on_first_print
    ):
        setup_log_prints(
            log_path,
            print_prepend,
            log_print_prepend,
            input_prepend,
            log_input_prepend,
            config.get("native_output") or None,
        )
    if config.get("app_id"):
        # Taskbar grouping of windows created by main.py with the pinned shortcut.
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(config["app_id"])
        except Exception as error:
            print(f"Warning: could not set the taskbar identity of this window: {error}")
    browser_ui = config.get("browser_ui") or ""
    # The public browser_terminal.ui API is usable by main.py; private PYAPP_* protocol
    # variables stay hidden. Clear an inherited channel when this is not a browser run.
    if browser_ui:
        os.environ["BROWSER_TERMINAL_UI"] = browser_ui
    else:
        os.environ.pop("BROWSER_TERMINAL_UI", None)
    if browser_ui:
        for stream in (sys.stdout, sys.stderr):
            if isinstance(stream, PipeSplitter):
                stream.browser_preferences = Path(browser_ui).with_suffix(".preferences.json")
    if input_prepend or log_input_prepend or browser_ui or hasattr(sys.stdout, "complete_input_line"):
        install_input_prefix(input_prepend, browser_ui)

    # --- 3. Import paths: main.py's own folder first, then the code folder (for "import settings").
    # Keep script-local imports first; code-root modules remain importable from nested entry scripts.
    sys.path[0] = str(Path(os.path.normpath(str(Path(script_path).absolute()))).parent)
    code_folder = os.path.normpath(str(Path(app_root).absolute()))
    if os.path.normcase(code_folder) != os.path.normcase(sys.path[0]):
        sys.path.insert(1, code_folder)

    register_app_api(config, script_path, app_root, context_lines)
    pending_background_error = capture_background_errors(
        script_path, report_path + ".background", app_root, context_lines
    )
    if ready_path:
        with Path(ready_path).open("w", encoding="utf-8") as stream:
            stream.write("ready")
    if foreground_on_first_print:
        on_output = first_output_callback(browser_ui)
        for stream in (sys.stdout, sys.stderr):
            if isinstance(stream, PipeSplitter):
                stream.on_output = on_output
    try:
        install_keyboard_interrupt_policy(
            config.get("keyboard_interrupt_action", "interrupt"),
            config.get("program_name", Path(script_path).stem),
            config.get("stop_request", ""),
        )
        # --- 4. Run main.py. runpy runs a file as the main program, so its
        # 'if __name__ == "__main__":' block runs too. This line returns when main.py has finished.
        runpy.run_path(script_path, run_name="__main__")
        if config.get("stop_request") and Path(config["stop_request"]).is_file():
            run_stop_callbacks()  # a GUI closed its window because Stop asked it to
        background_error = pending_background_error()
        if background_error is not None:
            raise background_error
        save_result(protocol.WrapperExit.SUCCESS)
    # --- 5. main.py raised an error (or called sys.exit): save the crash report for process_exit.py.
    except BaseException as error:  # includes SystemExit (also successful ones) and KeyboardInterrupt
        if isinstance(error, SystemExit) and protocol.exit_code_is_success(error.code):
            background_error = pending_background_error()
            if background_error is not None:
                error = background_error
        if isinstance(error, KeyboardInterrupt):
            run_stop_callbacks()  # pyapp_api.on_stop: Ctrl+C or the Stop shortcut ended the app
        protocol.save_report(error, script_path, report_path, app_root, context_lines)
        save_result(protocol.WrapperExit.APP_FAILED)
        sys.exit(protocol.WrapperExit.APP_FAILED)


if __name__ == "__main__":
    try:
        main()
    except Exception as wrapper_error:
        if report_path:
            protocol.save_report(wrapper_error, os.path.normpath(str(Path(__file__).absolute())), report_path)
        save_result(protocol.WrapperExit.WRAPPER_FAILED)
        sys.exit(protocol.WrapperExit.WRAPPER_FAILED)
