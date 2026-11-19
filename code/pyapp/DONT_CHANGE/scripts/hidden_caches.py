"""Give tool cache folders (__pycache__, .ruff_cache, ...) the Windows "hidden" attribute.

Python creates __pycache__ beside an imported module, and ruff, pytest and mypy create their caches
in the folder they run from, at any time and again after a deletion. A new folder is visible, while
an existing hidden one stays hidden when its files change. So instead of recording that this ran
once, every start checks the few known places: one attribute read per existing folder, no walk.
"""

from __future__ import annotations

import ctypes
import os
from typing import Iterator

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

CACHE_FOLDER_NAMES = ("__pycache__", ".ruff_cache", ".pytest_cache", ".mypy_cache")
FILE_ATTRIBUTE_HIDDEN = 0x2
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF


def _parents() -> Iterator[str]:
    """The folders a developer browses: project root, code, code/pyapp and the test folders."""
    yield paths.SHORTCUT_OUTPUT_DIR
    yield paths.PYTHON_SCRIPTS_DIR
    yield paths.PYTHON_SCRIPTS_DIR + "\\tests"
    yield paths.BACKEND_DIR
    yield paths.BACKEND_DIR + "\\tests"


def hide_cache_folders() -> None:
    """Hide the cache folders that exist in the known places; never raises."""
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.GetFileAttributesW.restype = ctypes.c_uint32
        for parent in _parents():
            for name in CACHE_FOLDER_NAMES:
                folder = parent + "\\" + name
                attributes = kernel32.GetFileAttributesW(folder)
                if attributes == INVALID_FILE_ATTRIBUTES or attributes & FILE_ATTRIBUTE_HIDDEN:
                    continue  # missing, or already hidden
                kernel32.SetFileAttributesW(folder, attributes | FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        note_ignored("hide cache folders")  # cosmetic only; must never stop a launch
