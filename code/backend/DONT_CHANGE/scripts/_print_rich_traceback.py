"""Render a serialized traceback snapshot with Rich.

This script is run by backend_python_exe which has rich installed. It reads JSON from stdin.
"""

import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

data = json.loads(sys.stdin.read())
console = Console()


def render_source(source, line_number):
    if not source:
        return Text("")
    try:
        start_line = int(line_number)
    except Exception:
        start_line = 1
    return Syntax(source, "python", line_numbers=True, start_line=start_line, word_wrap=True)


for error_data in data.get("errors", []):
    relation = error_data.get("relation") or ""
    if relation:
        console.print(Panel(Text(relation, style="bold white"), border_style="magenta"))

    title = error_data.get("title") or error_data.get("type") or "Exception"
    syntax = error_data.get("syntax")
    frames = error_data.get("frames") or []

    if syntax:
        body = Table.grid(padding=(0, 1))
        body.add_column(style="cyan", no_wrap=True)
        body.add_column()
        body.add_row("File", str(syntax.get("filename") or "<unknown>"))
        body.add_row("Line", str(syntax.get("lineno") or "?"))
        body.add_row("Source", render_source(syntax.get("text") or "", syntax.get("lineno") or 1))
        offset = syntax.get("offset")
        if offset:
            try:
                caret = " " * (int(offset) - 1) + "^"
            except Exception:
                caret = "^"
            body.add_row("", Text(caret, style="bold red"))
    else:
        body = Table(show_header=True, header_style="bold cyan", expand=True)
        body.add_column("#", style="magenta", no_wrap=True)
        body.add_column("Function", style="green", no_wrap=True)
        body.add_column("Location", style="cyan")
        body.add_column("Source")
        for index, frame in enumerate(frames, 1):
            location = "{}:{}".format(frame.get("filename") or "<unknown>", frame.get("lineno") or "?")
            body.add_row(
                str(index),
                frame.get("function") or "<module>",
                location,
                render_source(frame.get("source") or "", frame.get("lineno") or 1),
            )

    console.print(Panel(body, title="Python child script traceback", subtitle=title, border_style="red"))
