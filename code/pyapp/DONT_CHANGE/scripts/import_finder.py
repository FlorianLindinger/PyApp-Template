"""Offline import finder with the launcher's defaults: the app's code folder, the project's
environment, the bundled mapping (data/import_to_package.txt) and the folders it skips.

The finder itself is standalone/find_imports.py. Like any static finder it cannot see dynamic
imports (importlib.import_module("x")); imports inside try/except ImportError are optional.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from pyapp.DONT_CHANGE.backend_settings import (
    BACKEND_DIR,
    EXCLUDED_FOLDERS_FOR_IMPORT_SEARCH,
    IMPORT_MAPPING_PATH,
    PYTHON_SCRIPTS_DIR,
    VENV_DIR,
)
from pyapp.DONT_CHANGE.scripts.standalone import find_imports as core
from pyapp.DONT_CHANGE.scripts.standalone.find_imports import Requirement, standard_library_names

__all__ = ["Requirement", "standard_library_names"]

# The launcher (code/pyapp) is skipped only directly below the code folder.
LAUNCHER_FOLDER = Path(BACKEND_DIR).name


def _main_script_folder(root: str) -> Tuple[str, ...]:
    """The main script's folder is on sys.path too, so its modules are local (only for the app's folder)."""
    if root != PYTHON_SCRIPTS_DIR:
        return ()
    from pyapp.DONT_CHANGE.scripts.config import main_script_path

    return (str(Path(main_script_path()).parent),)


def _site(site_packages: Optional[str]) -> str:
    return str(Path(VENV_DIR) / "Lib" / "site-packages") if site_packages is None else site_packages


def python_files(root: str = PYTHON_SCRIPTS_DIR) -> Iterator[str]:
    return core.python_files(root, EXCLUDED_FOLDERS_FOR_IMPORT_SEARCH, (LAUNCHER_FOLDER,))


def local_module_names(root: str = PYTHON_SCRIPTS_DIR) -> Set[str]:
    return core.local_module_names(root, _main_script_folder(root), EXCLUDED_FOLDERS_FOR_IMPORT_SEARCH)


def imports_in_project(root: str = PYTHON_SCRIPTS_DIR) -> Tuple[Dict[str, Tuple[Set[str], bool]], List[str]]:
    return core.imports_in_project(
        root, EXCLUDED_FOLDERS_FOR_IMPORT_SEARCH, (LAUNCHER_FOLDER,), _main_script_folder(root)
    )


def installed_import_map(site_packages: Optional[str] = None) -> Dict[str, str]:
    return core.installed_import_map(_site(site_packages))


def installed_providers(site_packages: Optional[str] = None) -> Dict[str, List[str]]:
    return core.installed_providers(_site(site_packages))


def provider_of_module(import_name: str, site_packages: Optional[str] = None) -> Optional[str]:
    return core.provider_of_module(import_name, _site(site_packages))


def bundled_mapping(path: str = IMPORT_MAPPING_PATH) -> Dict[str, str]:
    return core.read_mapping(path)


def find_requirements(
    root: str = PYTHON_SCRIPTS_DIR, site_packages: Optional[str] = None
) -> Tuple[List[Requirement], List[str]]:
    """Return (list of Requirement sorted by distribution, list of unparsable-file messages)."""
    return core.find_requirements(
        root,
        _site(site_packages),
        bundled_mapping(),
        EXCLUDED_FOLDERS_FOR_IMPORT_SEARCH,
        (LAUNCHER_FOLDER,),
        _main_script_folder(root),
    )


def distribution_for_import(import_name: str, site_packages: Optional[str] = None) -> str:
    """Best distribution name for one missing import (used by the missing-package menu)."""
    return core.distribution_for_import(import_name, _site(site_packages), bundled_mapping())
