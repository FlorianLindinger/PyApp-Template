"""Render traceback reports (runtime/_pyapp.py) as plain or ANSI-colored text.

Frames of your own code get source lines around the failing line (traceback_lines_before /
traceback_lines_after); library frames are one line each, like CPython's. In color, every line
is drawn on a black background so the colors stay readable on any terminal color scheme.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

RESET = "\x1b[0m"
BLACK_BACKGROUND = "\x1b[40m"
CLEAR_TO_END_OF_LINE = "\x1b[K"  # fills the rest of the row with the current (black) background
STYLES = {
    "rule": "\x1b[1;91m",
    "meta": "\x1b[90m",
    "folder": "\x1b[90m",
    "file": "\x1b[1;96m",
    "library_file": "\x1b[36m",
    "lineno": "\x1b[93m",
    "function": "\x1b[92m",
    "gutter": "\x1b[90m",
    "context": "\x1b[37m",
    "library_code": "\x1b[90m",
    "current": "\x1b[1;97m",
    "marker": "\x1b[1;91m",
    "relation": "\x1b[33m",
    "error_type": "\x1b[1;91m",
    "error": "\x1b[97m",
    "detail": "\x1b[33m",
}


def _style(text: str, style: str, colors: bool) -> str:
    return f"{STYLES[style]}{text}{RESET}" if colors and text else text


def _display_filename(filename: str) -> str:
    """The full path: editors and Windows Terminal recognize "path:line" for jumping there."""
    if not filename or filename.startswith("<"):
        return filename or "?"
    return os.path.normpath(str(Path(filename).absolute()))


def on_black(line: str) -> str:
    """Draw a colored line on a black background up to the end of the row."""
    return BLACK_BACKGROUND + line.replace(RESET, RESET + BLACK_BACKGROUND) + CLEAR_TO_END_OF_LINE + RESET


def rule_line(width: int = 100, colors: bool = False) -> str:
    """The separator line around tracebacks (bold red in color)."""
    line = _style("─" * width, "rule", colors)
    return on_black(line) if colors else line


def metadata_lines(report: Dict[str, Any], date_format: str) -> List[str]:
    lines = []
    if report.get("script_path"):
        lines.append("Script  " + os.path.normpath(str(Path(str(report["script_path"])).absolute())))
    lines.append("Time    " + datetime.now().astimezone().strftime(date_format))
    if report.get("python_version"):
        executable = report.get("python_executable")
        lines.append("Python  " + str(report["python_version"]) + (f"  {executable}" if executable else ""))
    return lines


def _frame_lines(frame: Dict[str, Any], colors: bool) -> List[str]:
    app = bool(frame.get("app"))
    path = _display_filename(frame.get("filename", ""))
    name_start = len(path) - len(Path(path).name)
    location = (
        "  "
        + _style(path[:name_start], "folder", colors)
        + _style(path[name_start:], "file" if app else "library_file", colors)
        + _style(":", "gutter", colors)
        + _style(str(frame.get("lineno") or "?"), "lineno", colors)
        + _style(" in ", "gutter", colors)
        + _style(str(frame.get("name") or "?"), "function", colors)
    )
    lines = [location]
    context = frame.get("context") or []
    if context:
        digits = len(str(context[-1][0]))
        for number, text in context:
            current = number == frame.get("lineno")
            marker = _style(">", "marker", colors) if current else " "
            gutter = _style(f"{str(number).rjust(digits)} │", "marker" if current else "gutter", colors)
            lines.append(f"  {marker} {gutter} {_style(text, 'current' if current else 'context', colors)}".rstrip())
    elif frame.get("line"):
        lines.append("      " + _style(frame["line"], "library_code", colors))
    return lines


def render(
    report: Optional[Dict[str, Any]],
    *,
    colors: bool = False,
    date_format: str = "%Y-%m-%d %H:%M:%S",
    width: int = 100,
) -> List[str]:
    """Return the report as a list of lines (without newlines): frames, the error, then metadata."""
    if not report:
        return []
    lines = [""]  # the caller prints the headline right above

    chain = report.get("chain") or []
    if report.get("has_group") or not chain:
        # Exception groups: CPython's own nested layout.
        body = str(report.get("plain") or "").rstrip("\n").splitlines()
        lines += [
            _style(line, "error_type", colors) if index == len(body) - 1 else line for index, line in enumerate(body)
        ]
    else:
        for entry in chain:
            if entry.get("relation"):
                lines += ["", _style(entry["relation"], "relation", colors), ""]
            for frame in entry.get("frames") or []:
                if frame.get("context") and lines[-1]:
                    lines.append("")  # space around frames that show source lines
                lines += _frame_lines(frame, colors)
                if frame.get("context"):
                    lines.append("")
            error_line_done = False
            for text in entry.get("exception_only") or []:
                if not error_line_done and not text.startswith(" "):
                    # "Type: message" (later unindented lines are exception notes)
                    error_line_done = True
                    name, sep, message = text.partition(":")
                    lines.append(_style(name, "error_type", colors) + _style(sep + message, "error", colors))
                else:
                    lines.append(_style(text, "detail", colors))
    lines.append("")
    lines += [_style(line, "meta", colors) for line in metadata_lines(report, date_format)]
    lines.append(_style("─" * width, "rule", colors))
    if colors:
        # Keep the black background through every color change and to the end of each row.
        lines = [on_black(line) for line in lines]
    return lines
