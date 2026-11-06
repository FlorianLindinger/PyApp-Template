"""Helpers shared by the dev tools."""

from __future__ import annotations

import re

from backend.DONT_CHANGE.scripts.config import settings, validate
from backend.DONT_CHANGE.scripts.console_tools import ask, print_warn
from backend.DONT_CHANGE.scripts.env.venv import (
    app_python_for_tools,
    ensure_environment,
    install_without_recording,
)

COMMIT_HINT = "Commit developer_settings.py and backend/uv.lock."


def confirm(question: str) -> bool:
    """A yes/no question; only "y"/"yes" (or German "j"/"ja") means yes."""
    return ask(question + " [y/N]").strip().lower() in ("y", "yes", "j", "ja")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return normalized(match.group(1)) if match else normalized(requirement)


def global_packages_mode(s) -> bool:
    return s.package_environment == "interpreter_site_packages"


def prepare(s=None):
    """Validate settings and make sure the environment exists before changing it."""
    s = s or settings()
    validate(s)
    return ensure_environment(interactive=True)


def install_into_interpreter(s, names) -> None:
    """package_environment = "interpreter_site_packages": install only when explicitly allowed."""
    python = app_python_for_tools()
    if not s.allow_installing_into_global_python:
        print_warn("The app uses the selected interpreter's own packages; this tool does not change them.")
        print(f'Install them yourself:  "{python}" -m pip install {" ".join(names)}')
        print("(or set allow_installing_into_global_python = True in developer_settings.py)")
        return
    install_without_recording(names, python)


def ask_package_names(prompt: str) -> list:
    return ask(prompt).replace(",", " ").split()
