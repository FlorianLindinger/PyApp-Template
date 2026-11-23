"""Exit codes and traceback reports shared by the wrapper, watchdog and completion handler.

Imported inside the application's interpreter too, so: standard library only and
Python 3.8 compatible (no match statements, no X | Y types at runtime, ...). There it is a
top-level module, so its name must not collide with the app's modules or packages
(a plain "protocol" would shadow the app's own protocol.py).
"""

from __future__ import annotations

import json
import linecache
import os
import reprlib
import sys
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List, Optional, Set, Tuple


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


def _launcher_files() -> Set[str]:
    """Filenames whose frames are launcher plumbing, not the application."""
    names = {"<frozen runpy>"}
    try:
        import runpy

        names.add(os.path.normcase(os.path.realpath(runpy.__file__)))
    except (ImportError, AttributeError, TypeError):
        pass  # no runpy file (e.g. a frozen build): its frames are filtered by name only
    here = str(Path(os.path.realpath(__file__)).parent)
    for name in ("script_wrapper.py", "_pyapp.py"):
        names.add(os.path.normcase(str(Path(here) / name)))
    return names


def strip_launcher_frames(tb: Optional[TracebackType]) -> Optional[TracebackType]:
    """Drop the leading wrapper/runpy frames so the report looks like `python main.py`."""
    skip = _launcher_files()
    while tb is not None:
        filename = tb.tb_frame.f_code.co_filename
        key = filename if filename.startswith("<") else os.path.normcase(os.path.realpath(filename))
        if key not in skip:
            break
        tb = tb.tb_next
    return tb


def _is_app_file(filename: str, app_root: Optional[str]) -> bool:
    if not app_root or not filename or filename.startswith("<"):
        return False
    path = os.path.normcase(os.path.normpath(str(Path(filename).absolute())))
    root = os.path.normcase(os.path.normpath(str(Path(app_root).absolute())))
    if not path.startswith(root + os.sep):
        return False
    relative = path[len(root) + 1 :]
    first = relative.split(os.sep, 1)[0]
    return first not in ("pyapp", ".venv") and not first.startswith(".venv")


def _frames(
    te: traceback.TracebackException, app_root: Optional[str], context_lines: Tuple[int, int]
) -> List[Dict[str, Any]]:
    frames = []
    for frame in te.stack:
        is_app = _is_app_file(frame.filename, app_root)
        context = []
        before, after = context_lines
        if is_app and frame.lineno:
            for number in range(max(1, frame.lineno - before), frame.lineno + after + 1):
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


def _chain(
    te: traceback.TracebackException, app_root: Optional[str], context_lines: Tuple[int, int]
) -> List[Dict[str, Any]]:
    """Exception chain oldest first, like CPython prints it.

    Each entry's "relation" is the sentence printed between the previous entry and it.
    """
    entries = []
    seen = set()

    def add(current: Optional[traceback.TracebackException]) -> None:
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
                "frames": _frames(current, app_root, context_lines),
                "exception_only": [line.rstrip("\n") for line in current.format_exception_only()],
                "group": bool(getattr(current, "exceptions", None)),
            }
        )

    add(te)
    return entries


def capture_variables(error: BaseException) -> List[Dict[str, Any]]:
    """Snapshot traceback-frame scopes while they are alive; retain no frame/object references."""
    formatter = reprlib.Repr()
    formatter.maxstring = formatter.maxother = 4096
    formatter.maxlist = formatter.maxtuple = formatter.maxdict = formatter.maxset = 40
    snapshots: List[Dict[str, Any]] = []
    seen: Set[int] = set()

    def values(scope: Dict[str, Any]) -> Dict[str, str]:
        result = {}
        # repr can execute application code; freeze the names before representing values.
        for name, value in list(scope.items()):
            try:
                result[name] = formatter.repr(value)
            except BaseException:
                # A broken __repr__ must not replace the original exception, even for SystemExit.
                result[name] = f"<unrepresentable {type(value).__name__}>"
        return result

    def visit(current: BaseException) -> None:
        if id(current) in seen:
            return
        seen.add(id(current))
        if current.__cause__ is not None:
            visit(current.__cause__)
        elif current.__context__ is not None and not current.__suppress_context__:
            visit(current.__context__)
        frames = []
        tb = strip_launcher_frames(current.__traceback__)
        while tb is not None:
            frame = tb.tb_frame
            frames.append(
                {
                    "filename": frame.f_code.co_filename,
                    "lineno": tb.tb_lineno,
                    "name": frame.f_code.co_name,
                    "locals": values(frame.f_locals),
                    "globals": values(frame.f_globals),
                }
            )
            tb = tb.tb_next
        if frames:
            snapshots.append({"exception_type": type(current).__name__, "frames": frames})
        children = getattr(current, "exceptions", ())
        if isinstance(children, (tuple, list)):
            for child in children:
                if isinstance(child, BaseException):
                    visit(child)

    visit(error)
    return snapshots


def variable_dump(report: Dict[str, Any]) -> str:
    """Readable export, separate from the ordinary traceback so values stay out of console output."""
    lines = [
        "Traceback variable snapshot (values are NOT redacted)",
        "Locals/globals of captured traceback frames, not every live thread or a restorable memory dump.",
        "Large representations are shortened (up to 40 container items and 4096 string characters).",
        "Custom representations may summarize values or fail; builtins and imported modules are not expanded fully.",
        "",
        report.get("plain", ""),
    ]
    for exception in report.get("variables", []):
        lines += ["", "Exception: " + exception["exception_type"]]
        for frame in exception["frames"]:
            lines += ["", f"{frame['filename']}:{frame['lineno']} in {frame['name']}"]
            for scope in ("locals", "globals"):
                lines.append(scope.upper())
                for name, value in sorted(frame[scope].items()):
                    lines.append(f"  {name} = " + str(value).replace("\n", "\n    "))
    return "\n".join(lines) + "\n"


def build_report(
    error: BaseException, script_path: str, app_root: Optional[str] = None, context_lines: Tuple[int, int] = (3, 3)
) -> Dict[str, Any]:
    """Serializable report of an exception as if main.py had been run directly.

    context_lines: (lines before, lines after) the failing line shown for the app's own files.
    Variables are readable, bounded representations without redaction, captured before frames disappear.
    """
    tb = strip_launcher_frames(error.__traceback__)
    te = traceback.TracebackException(type(error), error, tb, capture_locals=False)
    exit_code = None
    if isinstance(error, SystemExit):
        code = error.code
        exit_code = code if code is None or isinstance(code, (bool, int, float, str)) else repr(code)
    chain = _chain(te, app_root, context_lines)
    variables: List[Dict[str, Any]]
    try:
        variables = capture_variables(error)
    except BaseException:
        variables = []  # Variable inspection must never prevent the original traceback from being saved.
    return {
        "script_path": script_path,
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "exception_type": type(error).__name__,
        "missing_module": getattr(error, "name", None) if isinstance(error, ModuleNotFoundError) else None,
        "system_exit_code": exit_code,
        "plain": "".join(te.format()),
        "chain": chain,
        "has_group": any(entry["group"] for entry in chain),
        "variables": variables,
    }


def save_report(
    error: BaseException,
    script_path: str,
    output_path: str,
    app_root: Optional[str] = None,
    context_lines: Tuple[int, int] = (3, 3),
) -> Dict[str, Any]:
    """Write the report atomically (temporary file + replace)."""
    report = build_report(error, script_path, app_root, context_lines)
    temporary = output_path + ".tmp"
    with Path(temporary).open("w", encoding="utf-8") as stream:
        json.dump(report, stream)
    Path(temporary).replace(output_path)
    return report


def exit_code_is_success(code: object) -> bool:
    """Only None and integer zero (including False) count as a successful SystemExit."""
    return code is None or (isinstance(code, int) and code == 0)
