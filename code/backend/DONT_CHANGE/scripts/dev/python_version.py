"""Dev tools for the project's Python version: change it, update it."""

from __future__ import annotations

import os
import sys
import tempfile

from backend.DONT_CHANGE.scripts.config import describe_python_request, edit_settings, python_version_problem, settings
from backend.DONT_CHANGE.scripts.console_tools import (
    ask,
    print_fields,
    print_heading,
    print_info,
    print_step,
    print_success,
)
from backend.DONT_CHANGE.scripts.dev.common import confirm, prepare
from backend.DONT_CHANGE.scripts.env.pythons import (
    available_summary,
    find_python,
    interpreter_version,
    invalidate_runtime_cache,
    newest_stable_minor,
    read_python_version_file,
    version_key,
    version_text,
)
from backend.DONT_CHANGE.scripts.env.uv import run_uv
from backend.DONT_CHANGE.scripts.env.venv import (
    build_venv,
    read_venv_config,
    refuse_mutation_while_running,
    switch_python,
)
from backend.DONT_CHANGE.scripts.errors import SettingsError


def cmd_change_python(arguments):
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
    for line in edit_settings({"python_version": new}):
        print(line)
    if not new:
        print_info(
            "python_version is now empty (newest stable, chosen once). Use update_python to move to a newer Python."
        )
        return
    prepare()  # offers the migration menu because the setting now differs from backend/generated/.python-version


def cmd_update_python(arguments):
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
    in_use = os.path.join(read_venv_config().get("home", ""), "python.exe")
    current_version = interpreter_version(in_use) if os.path.isfile(in_use) else None
    if newest_exe and current_version != interpreter_version(newest_exe):
        refuse_mutation_while_running()
        build_venv(newest_exe, locked=True, s=s)
    invalidate_runtime_cache()
    print_success(f"Python {version_text(interpreter_version(newest_exe or sys.executable))} is ready.")
