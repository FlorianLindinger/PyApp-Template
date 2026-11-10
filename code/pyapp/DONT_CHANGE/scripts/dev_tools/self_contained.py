"""Dev tool that makes the project self-contained: uv, Python and all packages inside the folder.

Such a folder runs on another PC without internet and without installing anything. uv and Python
are copied or installed into pyapp/generated (the shared ones stay where they are, other projects
use them); the environment is then rebuilt on the local Python.
"""

from __future__ import annotations

import os
import shutil
import types
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import List, Union

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.config import display_path, edit_settings, settings
from pyapp.DONT_CHANGE.scripts.console_tools import (
    print_fields,
    print_heading,
    print_info,
    print_settings_diff,
    print_step,
    print_success,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.common import confirm, prepare
from pyapp.DONT_CHANGE.scripts.env.pyproject import set_requires_python
from pyapp.DONT_CHANGE.scripts.env.pythons import (
    find_python,
    install_python,
    interpreter_version,
    invalidate_runtime_cache,
    newest_stable_minor,
    read_python_version_file,
    write_python_version_file,
)
from pyapp.DONT_CHANGE.scripts.env.uv import uv_exe, uv_version
from pyapp.DONT_CHANGE.scripts.env.venv import (
    build_venv,
    ensure_lock,
    read_venv_config,
    refuse_mutation_while_running,
    sync,
)
from pyapp.DONT_CHANGE.scripts.errors import SetupError


def _settings_copy(s: Union[ModuleType, SimpleNamespace], **overrides: object):
    values = {name: getattr(s, name) for name in dir(s) if not name.startswith("_")}
    values.update(overrides)
    return types.SimpleNamespace(**values)


# The settings that make every start use the copies inside the folder. The uv cache can stay
# global: the packages are copied into .venv, not linked to the cache (uv.py sets UV_LINK_MODE).
SELF_CONTAINED_SETTINGS = {
    "uv_prefer": "local",
    "uv_install_if_missing": "local",
    "python_source": "local",
}


def _inside(path: str, folder: str) -> bool:
    full = os.path.normcase(os.path.normpath(str(Path(path).absolute())))
    return full.startswith(os.path.normcase(os.path.normpath(folder)) + os.sep)


def is_self_contained(s: Union[ModuleType, SimpleNamespace]) -> bool:
    """The settings use the local copies, and uv, Python and the environment are inside the folder."""
    return (
        all(getattr(s, name) == value for name, value in SELF_CONTAINED_SETTINGS.items())
        and Path(paths.LOCAL_UV_EXE).is_file()
        and _inside(read_venv_config().get("home", "") or "?", paths.LOCAL_PYTHONS_DIR)
    )


def cmd_make_self_contained(arguments: List[str]):
    """Put uv, Python and all packages inside this folder, so it runs offline on other PCs."""
    s = settings()
    changes = {name: value for name, value in SELF_CONTAINED_SETTINGS.items() if getattr(s, name) != value}
    print_heading("Make self-contained")
    print_info("This puts everything the app needs to run into this folder, so it works on another PC")
    print_info("without internet and without installing anything:")
    print_fields(
        [
            ("uv", f"copied into {display_path(paths.LOCAL_UV_DIR)}"),
            ("Python", f"installed into {display_path(paths.LOCAL_PYTHONS_DIR)}"),
            ("Packages", f"reinstalled into {display_path(paths.VENV_DIR)} for that Python"),
        ]
    )
    print_info("The shared uv and Python stay where they are; other projects may use them.")
    # Ask before doing anything: with the old settings the next start would re-link the
    # environment to the shared Python and the local copies would go unused.
    if changes:
        print()
        print("So that every start uses these copies, these settings in developer_settings.py change:")
        print_fields([(name, f'"{getattr(s, name)}"  ->  "{value}"') for name, value in changes.items()])
    if not confirm("Continue?"):
        print_info("Nothing was changed.")
        return
    refuse_mutation_while_running()
    prepare(s)
    local = _settings_copy(s, python_source="local")

    # 1. uv
    current_uv = uv_exe()
    if not _inside(current_uv, paths.LOCAL_UV_DIR):
        staging = paths.LOCAL_UV_DIR + ".staging"
        shutil.rmtree(staging, ignore_errors=True)
        Path(staging).mkdir(parents=True)
        for name in ("uv.exe", "uvx.exe", "uvw.exe"):
            source = str((Path(current_uv).parent) / name)
            if Path(source).is_file():
                shutil.copy2(source, staging)
        if Path(paths.LOCAL_UV_DIR).is_dir():
            shutil.rmtree(paths.LOCAL_UV_DIR)
        Path(staging).rename(paths.LOCAL_UV_DIR)
        print_step(f"Copied uv {uv_version()} into {display_path(paths.LOCAL_UV_DIR)}")
    os.environ["PYAPP_UV"] = paths.LOCAL_UV_EXE

    # 2. Python
    request = read_python_version_file() or s.python_version or newest_stable_minor(local)
    python = find_python(request, local) or install_python(request, local)
    if not _inside(python, paths.LOCAL_PYTHONS_DIR):
        raise SetupError(f"uv did not install Python {request} into {paths.LOCAL_PYTHONS_DIR}.")
    print_step(f"Local Python: {display_path(python)}")

    # 3. packages
    if read_python_version_file() is None:
        write_python_version_file(request)
    set_requires_python(interpreter_version(python))
    ensure_lock(local)
    if not _inside(read_venv_config().get("home", "") or "?", paths.LOCAL_PYTHONS_DIR):
        build_venv(python, locked=True, s=local)
    else:
        sync(paths.VENV_PYTHON_EXE, exact=True, s=local)
    invalidate_runtime_cache()

    # 4. settings (accepted above)
    if changes:
        print_settings_diff(edit_settings(changes))
    print()
    print_success("The project is self-contained: uv, Python and all packages are inside this folder.")
    print_info("To use it on another PC:")
    print_info("  1. Copy the whole project folder, e.g. as a zip. A Git clone is not enough: Git ignores")
    print_info("     the copies in pyapp/generated (uv, pythons, .venv).")
    print_info("  2. On the other PC, run 'Setup - run first and after moving folder.cmd' once. It makes the")
    print_info("     shortcuts for the new location and needs no internet.")
    print_info("To go back to the shared uv and Python, change the settings above back; the local copies in")
    print_info("pyapp/generated can then be deleted.")
