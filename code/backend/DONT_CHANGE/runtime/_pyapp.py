"""Exit codes and traceback reports shared by the wrapper, watchdog and completion handler.

Imported inside the application's interpreter too, so: standard library only and
Python 3.8 compatible (no match statements, no X | Y types at runtime, ...). There it is a
top-level module, so its name must not collide with the app's modules or packages
(a plain "protocol" would shadow the app's own protocol.py).
"""

import json
import linecache
import os
import sys
import traceback


class WrapperExit:
    """Exit codes of script_wrapper.py (the process that runs main.py)."""

    SUCCESS = 0  # main.py finished; result.json written
    APP_FAILED = 1  # exception/SystemExit(non-zero)/Ctrl+C in main.py; traceback.json written
    WRAPPER_FAILED = 2  # the wrapper itself failed; traceback.json written
    INIT_FAILED = 3  # the wrapper failed before it could write reports


class ExitMode:
    """Outcome the watchdog passes to process_exit.py (independent of the wrapper's exit codes)."""

    SUCCESS = 10
    APP_EXIT = 11  # see traceback.json: SystemExit, exception, Ctrl+C
    WRAPPER_ERROR = 12
    WATCHDOG_ERROR = 13
    NO_REPORT = 14  # the interpreter ended without its completion report (native crash, os._exit, ...)


# How the watchdog reports a wrapper exit code that came with a matching result.json.
# WrapperExit.INIT_FAILED writes no result.json and therefore becomes ExitMode.NO_REPORT.
EXIT_MODE_FOR_WRAPPER_EXIT = {
    WrapperExit.SUCCESS: ExitMode.SUCCESS,
    WrapperExit.APP_FAILED: ExitMode.APP_EXIT,
    WrapperExit.WRAPPER_FAILED: ExitMode.WRAPPER_ERROR,
}


def _launcher_files():
    """Filenames whose frames are launcher plumbing, not the application."""
    names = {"<frozen runpy>"}
    try:
        import runpy

        names.add(os.path.normcase(os.path.realpath(runpy.__file__)))
    except (ImportError, AttributeError, TypeError):
        pass  # no runpy file (e.g. a frozen build): its frames are filtered by name only
    here = os.path.dirname(os.path.realpath(__file__))
    for name in ("script_wrapper.py", "_pyapp.py"):
        names.add(os.path.normcase(os.path.join(here, name)))
    return names


def strip_launcher_frames(tb):
    """Drop the leading wrapper/runpy frames so the report looks like `python main.py`."""
    skip = _launcher_files()
    while tb is not None:
        filename = tb.tb_frame.f_code.co_filename
        key = filename if filename.startswith("<") else os.path.normcase(os.path.realpath(filename))
        if key not in skip:
            break
        tb = tb.tb_next
    return tb


def _is_app_file(filename, app_root):
    if not app_root or not filename or filename.startswith("<"):
        return False
    path = os.path.normcase(os.path.abspath(filename))
    root = os.path.normcase(os.path.abspath(app_root))
    if not path.startswith(root + os.sep):
        return False
    relative = path[len(root) + 1 :]
    first = relative.split(os.sep, 1)[0]
    return first not in ("backend", ".venv") and not first.startswith(".venv")


def _frames(te, app_root, extra_lines):
    frames = []
    for frame in te.stack:
        is_app = _is_app_file(frame.filename, app_root)
        context = []
        if is_app and extra_lines and frame.lineno:
            for number in range(max(1, frame.lineno - extra_lines), frame.lineno + extra_lines + 1):
                text = linecache.getline(frame.filename, number)
                if text:
                    context.append([number, text.rstrip("\r\n")])
        frames.append(
            {
                "filename": frame.filename,
                "lineno": frame.lineno,
                "name": frame.name,
                "line": (frame.line or "").strip(),
                "app": is_app,
                "context": context,
            }
        )
    return frames


def _chain(te, app_root, extra_lines):
    """Exception chain oldest first, like CPython prints it.

    Each entry's "relation" is the sentence printed between the previous entry and it.
    """
    entries = []
    seen = set()

    def add(current):
        if current is None or id(current) in seen:
            return
        seen.add(id(current))
        relation = ""
        if current.__cause__ is not None:
            add(current.__cause__)
            relation = "The above exception was the direct cause of the following exception:"
        elif current.__context__ is not None and not current.__suppress_context__:
            add(current.__context__)
            relation = "During handling of the above exception, another exception occurred:"
        entries.append(
            {
                "relation": relation,
                "frames": _frames(current, app_root, extra_lines),
                "exception_only": [line.rstrip("\n") for line in current.format_exception_only()],
                "group": bool(getattr(current, "exceptions", None)),
            }
        )

    add(te)
    return entries


def build_report(error, script_path, app_root=None, extra_lines=3):
    """Serializable report of an exception as if main.py had been run directly."""
    tb = strip_launcher_frames(error.__traceback__)
    te = traceback.TracebackException(type(error), error, tb, capture_locals=False)
    exit_code = None
    if isinstance(error, SystemExit):
        code = error.code
        exit_code = code if code is None or isinstance(code, (bool, int, float, str)) else repr(code)
    chain = _chain(te, app_root, extra_lines)
    return {
        "script_path": script_path,
        "python_version": sys.version.split()[0],
        "exception_type": type(error).__name__,
        "missing_module": getattr(error, "name", None) if isinstance(error, ModuleNotFoundError) else None,
        "system_exit_code": exit_code,
        "plain": "".join(te.format()),
        "chain": chain,
        "has_group": any(entry["group"] for entry in chain),
    }


def save_report(error, script_path, output_path, app_root=None, extra_lines=3):
    """Write the report atomically (temporary file + replace)."""
    report = build_report(error, script_path, app_root, extra_lines)
    temporary = output_path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(report, stream)
    os.replace(temporary, output_path)
    return report


def exit_code_is_success(code):
    """Only None and integer zero (including False) count as a successful SystemExit."""
    return code is None or (isinstance(code, int) and code == 0)
