"""Helpers shared by the dev tools."""

from __future__ import annotations

import re

from backend.DONT_CHANGE.scripts.config import settings, validate
from backend.DONT_CHANGE.scripts.console_tools import ask
from backend.DONT_CHANGE.scripts.env.venv import ensure_environment

COMMIT_HINT = "Commit developer_settings.py and backend/environment/uv.lock."


def confirm(question: str) -> bool:
    """A yes/no question; only "y"/"yes" (or German "j"/"ja") means yes."""
    return ask(question + " [y/N]").strip().lower() in ("y", "yes", "j", "ja")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return normalized(match.group(1)) if match else normalized(requirement)


def prepare(s=None):
    """Validate settings and make sure the environment exists before changing it."""
    s = s or settings()
    validate(s)
    return ensure_environment(interactive=True)


def ask_package_names(prompt: str) -> list:
    return ask(prompt).replace(",", " ").split()
