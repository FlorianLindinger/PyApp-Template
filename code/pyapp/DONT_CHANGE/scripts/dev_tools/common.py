"""Helpers shared by the dev tools."""

from __future__ import annotations

import re
from types import ModuleType, SimpleNamespace
from typing import List, Optional, Union

from pyapp.DONT_CHANGE.scripts.config import settings, validate
from pyapp.DONT_CHANGE.scripts.console_tools import ask
from pyapp.DONT_CHANGE.scripts.env.venv import ensure_environment

COMMIT_HINT = "Commit developer_settings.py and pyapp/generated/uv.lock."


def confirm(question: str) -> bool:
    """A yes/no question; only "y"/"yes" (or German "j"/"ja") means yes."""
    return ask(question + " [y/N]").strip().lower() in ("y", "yes", "j", "ja")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return normalized(match.group(1)) if match else normalized(requirement)


def prepare(s: Optional[Union[ModuleType, SimpleNamespace]] = None):
    """Validate settings and make sure the environment exists before changing it."""
    s = s or settings()
    validate(s)
    return ensure_environment(interactive=True)


def ask_package_names(prompt: str) -> List[str]:
    return split_package_entries(ask(prompt))


# A comma, or a word with its quoted texts and [extras] lists, which may contain spaces and commas.
_ENTRY_TOKEN = re.compile(r"""(?:"[^"]*"|'[^']*'|\[[^\]]*\]|[^\s\[\]'",])+|,""")
_SPEC_START = re.compile(r"""^[<>=!~;@,(]""")
_SPEC_OPEN_END = re.compile(r"""[<>=!~;@(]$""")
# Inside an environment marker (after ";") these words also continue the requirement.
_MARKER_WORD = re.compile(r"""^(?:and|or|not|in)$|^['"]""")
_MARKER_OPEN_END = re.compile(r"""\b(?:and|or|not|in)$""")


def split_package_entries(text: str) -> List[str]:
    """Requirements typed on one line, e.g. 'numpy>=1,<2 requests[socks,security], pkg @ https://...'.

    Spaces and commas separate requirements, but only between complete ones: a part that starts
    with a version operator, ";" or "@", or that follows one, belongs to the previous requirement.
    Version specifiers after a comma always start with an operator, so "a>=1,<2" stays whole
    while "a, b" is two entries.
    """
    entries: List[str] = []
    end = 0
    for match in _ENTRY_TOKEN.finditer(text):
        part, gap, end = match.group(), text[end : match.start()], match.end()
        previous = entries[-1] if entries else ""
        in_marker = ";" in previous and (_MARKER_WORD.match(part) or _MARKER_OPEN_END.search(previous))
        # A comma is attached for now; it stays only if a specifier follows (see _SPEC_START).
        if previous and (part == "," or _SPEC_START.match(part) or _SPEC_OPEN_END.search(previous) or in_marker):
            entries[-1] = previous + gap + part  # the typed spacing is kept
        elif part != ",":
            entries.append(part)
    return [entry for entry in (entry.strip(" ,") for entry in entries) if entry]
