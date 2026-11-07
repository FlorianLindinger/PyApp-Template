"""Render traceback reports (runtime/_pyapp.py) as plain or ANSI-colored text.

Frames of your own code get source lines around the failing line (traceback_lines_before /
traceback_lines_after); library frames are one line each, like CPython's. In color, every line
is drawn on a black background so the colors stay readable on any terminal color scheme
(terminal_colors_after_failure etc. may make the rest of the window red or green).
"""

from __future__ import annotations

import os
from datetime import datetime

RESET = "\x1b[0m"
BLACK_BACKGROUND = "\x1b[40m"
CLEAR_TO_END_OF_LINE = "\x1b[K"  # fills the rest of the row with the current (black) background
STYLES = {
    "rule": "\x1b[90m",
    "title": "\x1b[1;91m",
    "meta": "\x1b[90m",
    "file": "\x1b[96m",
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


def _display_filename(filename: str, script_path: str) -> str:
    if not filename or filename.startswith("<") or not script_path:
        return filename or "?"
    try:
        relative = os.path.relpath(os.path.abspath(filename), os.path.dirname(os.path.abspath(script_path)))
    except ValueError:
        return filename
    return filename if relative.startswith("..") else relative


def metadata_lines(report: dict, date_format: str) -> list:
    lines = []
    if report.get("script_path"):
        lines.append("Script  " + os.path.abspath(str(report["script_path"])))
    lines.append("Time    " + datetime.now().astimezone().strftime(date_format))
    if report.get("python_version"):
        lines.append("Python  " + str(report["python_version"]))
    return lines


def _frame_lines(frame: dict, script_path: str, colors: bool) -> list:
    app = bool(frame.get("app"))
    location = (
        "  "
        + _style(_display_filename(frame.get("filename", ""), script_path), "file" if app else "library_file", colors)
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
            gutter = _style(f"{str(number).rjust(digits)} |", "gutter", colors)
            lines.append(f"  {marker} {gutter} {_style(text, 'current' if current else 'context', colors)}")
    elif frame.get("line"):
        lines.append("      " + _style(frame["line"], "library_code", colors))
    return lines


def render(
    report: dict | None,
    *,
    colors: bool = False,
    date_format: str = "%Y-%m-%d %H:%M:%S",
    width: int = 100,
) -> list:
    """Return the report as a list of lines (without newlines)."""
    if not report:
        return []
    script_path = str(report.get("script_path") or "")
    rule = _style("-" * width, "rule", colors)
    lines = [rule, _style(f"Traceback of {os.path.basename(script_path) or 'the program'}", "title", colors)]
    lines += [_style(line, "meta", colors) for line in metadata_lines(report, date_format)]
    lines.append(rule)

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
                lines += _frame_lines(frame, script_path, colors)
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
    lines.append(rule)
    if colors:
        # Keep the black background through every color change and to the end of each row.
        lines = [
            BLACK_BACKGROUND + line.replace(RESET, RESET + BLACK_BACKGROUND) + CLEAR_TO_END_OF_LINE + RESET
            for line in lines
        ]
    return lines
