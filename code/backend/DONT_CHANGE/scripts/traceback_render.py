"""Render traceback reports (runtime/_pyapp.py) as plain or ANSI-colored text.

Frames of your own code get a few lines of context; library frames look like CPython's.
"""

from __future__ import annotations

import os
from datetime import datetime

RESET = "\x1b[0m"
STYLES = {
    "rule": "\x1b[1;91m",
    "meta": "\x1b[90m",
    "heading": "\x1b[1;97m",
    "file": "\x1b[96m",
    "lineno": "\x1b[93m",
    "function": "\x1b[92m",
    "context": "\x1b[37m",
    "current": "\x1b[1;97m",
    "marker": "\x1b[1;91m",
    "relation": "\x1b[93m",
    "error_type": "\x1b[1;91m",
    "error": "\x1b[91m",
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
        lines.append("Script: " + os.path.abspath(str(report["script_path"])))
    lines.append("Error date: " + datetime.now().astimezone().strftime(date_format))
    if report.get("python_version"):
        lines.append("Python: " + str(report["python_version"]))
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
    title = f" {os.path.basename(script_path) or 'Traceback'} "
    side = max(3, (width - len(title)) // 2)
    lines = [_style("=" * side + title + "=" * side, "rule", colors)]
    lines += [_style(line, "meta", colors) for line in metadata_lines(report, date_format)]
    lines.append("")

    chain = report.get("chain") or []
    if report.get("has_group") or not chain:
        body = str(report.get("plain") or "").rstrip("\n").splitlines()
        lines += [_style(line, "error", colors) if index == len(body) - 1 else line for index, line in enumerate(body)]
        lines.append(_style("=" * (2 * side + len(title)), "rule", colors))
        return lines

    for entry in chain:
        if entry.get("relation"):
            lines += ["", _style(entry["relation"], "relation", colors), ""]
        frames = entry.get("frames") or []
        if frames:
            lines.append(_style("Traceback (most recent call last):", "heading", colors))
        for frame in frames:
            location = (
                "  File "
                + _style(
                    '"' + _display_filename(frame.get("filename", ""), script_path) + '"',
                    "file",
                    colors,
                )
                + ", line "
                + _style(str(frame.get("lineno") or "?"), "lineno", colors)
                + ", in "
                + _style(str(frame.get("name") or "?"), "function", colors)
            )
            lines.append(location)
            context = frame.get("context") or []
            if context:
                digits = len(str(context[-1][0]))
                for number, text in context:
                    current = number == frame.get("lineno")
                    marker = _style(">", "marker", colors) if current else " "
                    code = _style(text, "current" if current else "context", colors)
                    lines.append(f"  {marker} {str(number).rjust(digits)} | {code}")
            elif frame.get("line"):
                lines.append("    " + frame["line"])
        error_line_done = False
        for text in entry.get("exception_only") or []:
            if not error_line_done and not text.startswith(" "):
                # "Type: message" (later unindented lines are exception notes)
                error_line_done = True
                name, sep, message = text.partition(":")
                lines.append(_style(name, "error_type", colors) + _style(sep + message, "error", colors))
            else:
                lines.append(_style(text, "detail", colors))
    lines.append(_style("=" * (2 * side + len(title)), "rule", colors))
    return lines
