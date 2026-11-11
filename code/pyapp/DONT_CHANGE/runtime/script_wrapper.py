"""Run main.py with isolated arguments, mirrored logging and serialized exit reports.

Runs inside the application's interpreter, so it must work on every Python the
launcher supports (3.8+): standard library only, no "X | Y" types at runtime, no
match statements, no parenthesized context managers.
"""

from __future__ import annotations

import codecs
import io
import os
import re
import runpy
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional, TextIO, Tuple, Union

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
        _take_native_output()
        with self._lock:
            for part in data.splitlines(True) or [data]:
                if self._at_line_start:
                    prefix = _format_prepend(self.print_timestamp_format)
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
        _take_native_output()
        with self._lock:
            self._write_console(_format_prepend(self.input_timestamp_format) + prompt)
            if self.log_stream is not None:
                self.log_stream.write(_format_prepend(self.log_input_timestamp_format) + _ANSI_ESCAPE.sub("", prompt))
            self._at_line_start = prompt.endswith("\n")
            self.flush()

    def write_native(self, data: bytes, log_text: str) -> None:
        """Output written below Python (see NativeOutput): unchanged to the console, as text to the log."""
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
        log_file = Path(log_path).open("w", encoding="utf-8", buffering=1)  # noqa: SIM115
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


def install_input_prefix(input_prepend: Optional[str]) -> None:
    """input() bypasses sys.stdout's prefixing, so wrap it."""
    import builtins

    original_input = builtins.input

    def input_with_prepend(prompt: object = "") -> str:
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
    # the watchdog then reports as a failure. Python 3.8/3.9 only print it. Other ignored errors
    # (e.g. in __del__) stay non-fatal, as before.
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


# ------------------------------------------------------------ main


def main() -> None:
    """Load the launch configuration, prepare logging and argv, then run main.py as __main__."""
    global report_path, result_path
    import json

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

    sys.argv = [script_path, *list(config.get("args", []))]
    # With logging, stdout/stderr are pipes that would use the legacy ANSI code page and fail on
    # characters like "\u65e5"; the watchdog reads them as UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            if isinstance(stream, io.TextIOWrapper) and not stream.isatty():
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass
    if log_path or print_prepend or log_print_prepend or input_prepend or log_input_prepend:
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
    if input_prepend or log_input_prepend or hasattr(sys.stdout, "complete_input_line"):
        install_input_prefix(input_prepend)

    # Make the application's folder sys.path[0], exactly like `python main.py`,
    # instead of this launcher folder.
    sys.path[0] = str(Path(os.path.normpath(str(Path(script_path).absolute()))).parent)

    pending_background_error = capture_background_errors(
        script_path, report_path + ".background", app_root, context_lines
    )
    if ready_path:
        with Path(ready_path).open("w", encoding="utf-8") as stream:
            stream.write("ready")
    try:
        runpy.run_path(script_path, run_name="__main__")
        background_error = pending_background_error()
        if background_error is not None:
            raise background_error
        save_result(protocol.WrapperExit.SUCCESS)
    except BaseException as error:  # includes SystemExit (also successful ones) and KeyboardInterrupt
        if isinstance(error, SystemExit) and protocol.exit_code_is_success(error.code):
            background_error = pending_background_error()
            if background_error is not None:
                error = background_error
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
