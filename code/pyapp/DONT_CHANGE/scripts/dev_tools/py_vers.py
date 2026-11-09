"""Dev tools for the project's Python version: change it, update it."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import List

from pyapp.DONT_CHANGE.scripts.config import describe_python_request, edit_settings, python_version_problem, settings
from pyapp.DONT_CHANGE.scripts.console_tools import (
    ask,
    print_fields,
    print_heading,
    print_info,
    print_settings_diff,
    print_step,
    print_success,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.common import confirm, prepare
from pyapp.DONT_CHANGE.scripts.env.pythons import (
    available_summary,
    find_python,
    interpreter_version,
    invalidate_runtime_cache,
    newest_stable_minor,
    read_python_version_file,
    version_key,
    version_text,
)
from pyapp.DONT_CHANGE.scripts.env.uv import run_uv
from pyapp.DONT_CHANGE.scripts.env.venv import (
    build_venv,
    read_venv_config,
    refuse_mutation_while_running,
    switch_python,
)
from pyapp.DONT_CHANGE.scripts.errors import SettingsError


def cmd_change_python(arguments: List[str]):
    """Set a new python_version and migrate the project to it."""
    s = settings()
    current = read_python_version_file()
    print_heading("Change Python")
    print_fields(
        [
            ("Project Python", current or "(not set up yet)"),
            ("python_version", describe_python_request(s.python_version)),
        ]
    )
    print_info(available_summary(s))
    new = (
        arguments[0]
        if arguments
        else ask('New python_version (e.g. "3.13", "3.14t", empty = newest stable):').strip().strip('"')
    )
    problem = python_version_problem(new)
    if problem:
        raise SettingsError(problem)
    print_settings_diff(edit_settings({"python_version": new}))
    if not new:
        print_info(
            "python_version is now empty (newest stable, chosen once). Use update_python to move to a newer Python."
        )
        return
    prepare()  # offers the migration menu because the setting now differs from pyapp/generated/.python-version


def cmd_update_python(arguments: List[str]):
    """Newest patch release of the project's Python; with python_version = "" also a newer minor version."""
    s = settings()
    prepare(s)
    current = read_python_version_file()
    if not s.python_version:
        newest = newest_stable_minor(s)
        if (current and newest != current and version_key(newest) > version_key(current)) and confirm(
            f"Python {newest} is available (the project uses {current}). Switch now?"
        ):
            switch_python(newest, s=s)
            return
    request = current or s.python_version
    print_step(f"Updating Python {request} to its newest patch release...")
    run_uv(["python", "install", "--upgrade", request], cwd=tempfile.gettempdir())
    newest_exe = find_python(request, s)
    in_use = str(Path(read_venv_config().get("home", "")) / "python.exe")
    current_version = interpreter_version(in_use) if Path(in_use).is_file() else None
    if newest_exe and current_version != interpreter_version(newest_exe):
        refuse_mutation_while_running()
        build_venv(newest_exe, locked=True, s=s)
    invalidate_runtime_cache()
    print_success(f"Python {version_text(interpreter_version(newest_exe or sys.executable))} is ready.")
