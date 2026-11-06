"""Run main.py with isolated arguments, mirrored logging and serialized exit reports.

Runs inside the application's interpreter, so it must work on every Python the
launcher supports (3.8+): standard library only, no "X | Y" types at runtime, no
match statements, no parenthesized context managers.
"""

import codecs
import io
import os
import re
import runpy
import sys
import threading
from datetime import datetime

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


def _format_prepend(fmt):
    """Current local time in the configured prefix format, or ""."""
    return datetime.now().astimezone().strftime(fmt) if fmt else ""


class _BinarySplitter:
    """Mirror binary writes to the original stream and an incrementally decoded text log."""

    def __init__(self, owner):
        self.owner = owner
        self.decoder = codecs.getincrementaldecoder(owner.encoding or "utf-8")("replace")

    def write(self, data):
        with self.owner._lock:
            target = getattr(self.owner.print_stream, "buffer", None)
            if target is not None:
                target.write(data)
            else:
                self.owner.print_stream.write(data.decode(self.owner.encoding or "utf-8", "replace"))
            if self.owner.log_stream is not None:
                self.owner.log_stream.write(self.decoder.decode(data))
            self.owner.flush()
        return len(data)

    def flush(self):
        self.owner.flush()

    def __getattr__(self, name):
        return getattr(self.owner.print_stream.buffer, name)


class PipeSplitter:
    """Mirror text to the console stream and an optional log, with per-line time prefixes."""

    def __init__(
        self,
        print_stream,
        log_stream=None,
        print_timestamp_format="",
        log_timestamp_format="",
        input_timestamp_format="",
        log_input_timestamp_format="",
        print_red=False,
    ):
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

    def _supports_color(self):
        return bool(getattr(self.print_stream, "isatty", lambda: False)())

    def write(self, data):
        if data is None:
            data = ""
        if not isinstance(data, str):
            data = str(data)
        if data == "":
            return 0
        with self._lock:
            for part in data.splitlines(True) or [data]:
                if self._at_line_start:
                    prefix = _format_prepend(self.print_timestamp_format)
                    if prefix:
                        self.print_stream.write(prefix)
                    log_prefix = _format_prepend(self.log_timestamp_format)
                    if self.log_stream is not None and log_prefix:
                        self.log_stream.write(log_prefix)
                    if self.print_red and self._supports_color():
                        self.print_stream.write("\x1b[31m")
                self.print_stream.write(part)
                if self.log_stream is not None:
                    self.log_stream.write(_ANSI_ESCAPE.sub("", part))
                if part.endswith("\n"):
                    if self.print_red and self._supports_color():
                        self.print_stream.write("\x1b[0m")
                    self._at_line_start = True
                else:
                    self._at_line_start = False
            self.flush()
        return len(data)

    def write_input_prompt(self, prompt):
        prompt = "" if prompt is None else str(prompt)
        with self._lock:
            self.print_stream.write(_format_prepend(self.input_timestamp_format) + prompt)
            if self.log_stream is not None:
                self.log_stream.write(_format_prepend(self.log_input_timestamp_format) + _ANSI_ESCAPE.sub("", prompt))
            self._at_line_start = prompt.endswith("\n")
            self.flush()

    def complete_input_line(self, text):
        with self._lock:
            if self.log_stream is not None and not self._at_line_start:
                self.log_stream.write(text + "\n")
            self._at_line_start = True
            self.flush()

    def flush(self):
        with self._lock:
            if hasattr(self.print_stream, "flush"):
                self.print_stream.flush()
            if self.log_stream is not None:
                self.log_stream.flush()

    def isatty(self):
        return self._supports_color()

    def writable(self):
        return True

    def fileno(self):
        if hasattr(self.print_stream, "fileno"):
            return self.print_stream.fileno()
        raise OSError("The underlying stream has no file descriptor")

    @property
    def encoding(self):
        return getattr(self.print_stream, "encoding", None)

    def __getattr__(self, name):
        return getattr(self.print_stream, name)


def setup_log_prints(
    log_path,
    overwrite_log,
    print_prepend,
    log_print_prepend,
    input_prepend,
    log_input_prepend,
):
    """Install stdout/stderr splitters and point faulthandler at the log."""
    import atexit
    import faulthandler

    global log_file
    if log_path:
        folder = os.path.dirname(log_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        log_file = open(  # noqa: SIM115 - open for the whole run, closed by _finish_logging
            log_path, "w" if overwrite_log else "a", encoding="utf-8", buffering=1
        )
    # Registered before the application's callbacks, so it runs after them.
    atexit.register(_finish_logging)
    common = {
        "print_timestamp_format": print_prepend,
        "log_timestamp_format": log_print_prepend,
        "input_timestamp_format": input_prepend,
        "log_input_timestamp_format": log_input_prepend,
    }
    sys.stdout = PipeSplitter(sys.__stdout__, log_file, **common)
    sys.stderr = PipeSplitter(sys.__stderr__, log_file, print_red=True, **common)
    if log_file is not None:
        faulthandler.enable(file=log_file, all_threads=True)
    else:
        faulthandler.enable(all_threads=True)


def _finish_logging():
    import faulthandler

    try:
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        if log_file is not None:
            faulthandler.disable()
            log_file.close()


def install_input_prefix(input_prepend):
    """input() bypasses sys.stdout's prefixing, so wrap it."""
    import builtins

    original_input = builtins.input

    def input_with_prepend(prompt=""):
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


def save_result(code):
    """Atomic completion marker; its absence tells the watchdog the interpreter died abruptly."""
    if result_path:
        import json

        with open(result_path + ".tmp", "w", encoding="utf-8") as stream:
            json.dump({"wrapper_exit_code": code}, stream)
        os.replace(result_path + ".tmp", result_path)


def capture_background_errors(script_path, output_path, app_root, extra_lines):
    """Record the first unhandled worker-thread error and Tkinter callback error."""
    first_error = [None]
    lock = threading.Lock()
    previous_last = getattr(sys, "last_exc", getattr(sys, "last_value", None))

    def record(error):
        if isinstance(error, SystemExit) and protocol.exit_code_is_success(error.code):
            return
        with lock:
            if first_error[0] is not None:
                return
            first_error[0] = error
            protocol.save_report(error, script_path, output_path, app_root, extra_lines)

    previous_hook = getattr(threading, "excepthook", None)
    if previous_hook is not None:

        def thread_hook(args):
            try:
                record(args.exc_value)
            finally:
                previous_hook(args)

        threading.excepthook = thread_hook

    def pending_error():
        # Tkinter's default report_callback_exception stores the error in sys.last_*.
        last = getattr(sys, "last_exc", getattr(sys, "last_value", None))
        if isinstance(last, BaseException) and last is not previous_last:
            record(last)
        return first_error[0]

    return pending_error


# ------------------------------------------------------------ main


def main():
    """Load the launch configuration, prepare logging and argv, then run main.py as __main__."""
    global report_path, result_path
    import json

    if len(sys.argv) != 3 or sys.argv[1] != "--config":
        raise SystemExit("script_wrapper.py is started by the launcher with --config <file>.")
    with open(sys.argv[2], encoding="utf-8") as stream:
        config = json.load(stream)
    script_path = config["script"]
    report_path = config["traceback"]
    result_path = config["result"]
    ready_path = config.get("ready")
    app_root = config.get("app_root") or os.path.dirname(script_path)
    extra_lines = int(config.get("traceback_extra_lines", 3))
    print_prepend = config.get("print_prepend") or ""
    input_prepend = config.get("input_prepend") or ""
    log_print_prepend = config.get("log_print_prepend") or ""
    log_input_prepend = config.get("log_input_prepend") or ""
    log_path = config.get("log_path") or ""
    for key in list(os.environ):  # launcher protocol is not an application API
        if key.startswith("PYAPP_"):
            os.environ.pop(key, None)

    sys.argv = [script_path] + list(config.get("args", []))
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
            config.get("overwrite_log", True),
            print_prepend,
            log_print_prepend,
            input_prepend,
            log_input_prepend,
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
    sys.path[0] = os.path.dirname(os.path.abspath(script_path))

    pending_background_error = capture_background_errors(
        script_path, report_path + ".background", app_root, extra_lines
    )
    if ready_path:
        with open(ready_path, "w", encoding="utf-8") as stream:
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
        protocol.save_report(error, script_path, report_path, app_root, extra_lines)
        save_result(protocol.WrapperExit.APP_FAILED)
        sys.exit(protocol.WrapperExit.APP_FAILED)


if __name__ == "__main__":
    try:
        main()
    except Exception as wrapper_error:
        if report_path:
            protocol.save_report(wrapper_error, os.path.abspath(__file__), report_path)
        save_result(protocol.WrapperExit.WRAPPER_FAILED)
        sys.exit(protocol.WrapperExit.WRAPPER_FAILED)
