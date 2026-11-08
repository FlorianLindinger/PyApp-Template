"""Dev tool that makes the project portable (uv, Python and packages inside the folder)."""

from __future__ import annotations

import os
import shutil
import types
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import List, Union

from backend.DONT_CHANGE import backend_settings as paths
from backend.DONT_CHANGE.scripts.config import display_path, edit_settings, settings
from backend.DONT_CHANGE.scripts.console_tools import print_fields, print_heading, print_info, print_step, print_success
from backend.DONT_CHANGE.scripts.dev.common import confirm, prepare
from backend.DONT_CHANGE.scripts.env.pyproject import set_requires_python
from backend.DONT_CHANGE.scripts.env.pythons import (
    find_python,
    install_python,
    interpreter_version,
    invalidate_runtime_cache,
    newest_stable_minor,
    read_python_version_file,
    write_python_version_file,
)
from backend.DONT_CHANGE.scripts.env.uv import uv_exe, uv_version
from backend.DONT_CHANGE.scripts.env.venv import (
    build_venv,
    ensure_lock,
    read_venv_config,
    refuse_mutation_while_running,
    sync,
)
from backend.DONT_CHANGE.scripts.errors import SetupError


def _settings_copy(s: Union[ModuleType, SimpleNamespace], **overrides: object):
    values = {name: getattr(s, name) for name in dir(s) if not name.startswith("_")}
    values.update(overrides)
    return types.SimpleNamespace(**values)


PORTABLE_SETTINGS = {
    "uv_prefer": "local",
    "uv_install_if_missing": "local",
    "python_source": "local",
}


def cmd_make_portable(arguments: List[str]):
    """Put uv, Python and all packages inside this folder so it runs offline on other PCs."""
    s = settings()
    # Ask before doing anything: with the old settings the next start would re-link the
    # environment to the non-local Python and the local copies would go unused.
    changes = {name: value for name, value in PORTABLE_SETTINGS.items() if getattr(s, name) != value}
    if changes:
        print_heading("Make portable")
        print("These settings in developer_settings.py change:")
        print_fields([(name, f'"{getattr(s, name)}"  ->  "{value}"') for name, value in changes.items()])
        if not confirm("Continue?"):
            print_info("Nothing was changed.")
            return
    prepare(s)
    refuse_mutation_while_running()
    local = _settings_copy(s, python_source="local")

    # 1. uv
    current_uv = uv_exe()
    if os.path.normcase(str(Path(os.path.normpath(str(Path(current_uv).absolute()))).parent)) != os.path.normcase(
        paths.LOCAL_UV_DIR
    ):
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
    if not os.path.normcase(os.path.normpath(str(Path(python).absolute()))).startswith(
        os.path.normcase(paths.LOCAL_PYTHONS_DIR)
    ):
        raise SetupError(f"uv did not install Python {request} into {paths.LOCAL_PYTHONS_DIR}.")
    print_step(f"Local Python: {display_path(python)}")

    # 3. packages
    if read_python_version_file() is None:
        write_python_version_file(request)
    set_requires_python(interpreter_version(python))
    ensure_lock(local)
    home = read_venv_config().get("home", "")
    if not os.path.normcase(home).startswith(os.path.normcase(paths.LOCAL_PYTHONS_DIR)):
        build_venv(python, locked=True, s=local)
    else:
        sync(paths.VENV_PYTHON_EXE, exact=True, s=local)
    invalidate_runtime_cache()

    # 4. settings (accepted above)
    if changes:
        for line in edit_settings(changes):
            print(line)
    print()
    print_success("uv, Python and all packages are now inside this folder, and developer_settings.py uses them.")
    print_info("Copy the whole project folder. After moving it, run 'Setup - run first and after moving folder.cmd'")
    print_info("to refresh the shortcuts; the environment adapts to the new location by itself.")
