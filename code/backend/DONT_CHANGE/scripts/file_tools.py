"""Filesystem helpers and path utilities."""

from __future__ import annotations

import os
from pathlib import Path


def remove_tree_inside(path: str, base: str) -> None:
    """Delete a folder tree only if it lies strictly inside base and is not a link."""
    import shutil

    target = os.path.realpath(path)
    root = os.path.realpath(base)
    if os.path.normcase(os.path.commonpath([target, root])) != os.path.normcase(root) or os.path.normcase(
        target
    ) == os.path.normcase(root):
        raise ValueError(f'Refusing to delete "{path}": it is not inside "{base}".')
    if Path(path).is_symlink() or _is_junction(path):
        Path(path).rmdir() if Path(path).is_dir() else Path(path).unlink()
        return
    shutil.rmtree(target)


def _is_junction(path: str) -> bool:
    """True for Windows junctions/reparse-point folders (works on Python 3.8)."""
    try:
        return bool(os.lstat(path).st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except (OSError, AttributeError):
        return False


def set_hidden_in_explorer(paths: list[str], hidden: bool = True):
    """Hide (or unhide) existing files and folders in Explorer; missing paths and failures are skipped."""

    import ctypes

    FILE_ATTRIBUTE_HIDDEN = 0x02
    INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    kernel32.GetFileAttributesW.restype = ctypes.c_uint32
    kernel32.SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
    kernel32.SetFileAttributesW.restype = ctypes.c_int

    for path in paths:
        path = os.path.normpath(str(Path(path).absolute()))

        attributes = kernel32.GetFileAttributesW(path)

        if attributes == INVALID_FILE_ATTRIBUTES:
            continue

        if hidden:
            new_attributes = attributes | FILE_ATTRIBUTE_HIDDEN
        else:
            new_attributes = attributes & ~FILE_ATTRIBUTE_HIDDEN

        # Avoid an unnecessary filesystem operation.
        if new_attributes != attributes:
            kernel32.SetFileAttributesW(path, new_attributes)


def make_abs_path_relative_to_file(path: str, file: str) -> str:
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    # Keep os.path.isabs: rooted Windows paths have different pathlib semantics on Python 3.8-3.12.
    if not os.path.isabs(path):  # noqa: PTH117
        return os.path.normpath(str(Path(file).parent) + "\\" + path)
    else:
        return path


def sanitize_filename(filename: str, replacement: str = "_", *, max_length: int = 255) -> str:
    """Return a Windows-safe filename bounded in UTF-16 units, including device-name checks."""
    import re

    if max_length < 1:
        raise ValueError("Filename length must be positive")
    # 1. Characters illegal in Windows: < > : " / \ | ? *
    # Also handles control characters (0-31)
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    filename = re.sub(illegal_chars, replacement, filename)
    # 2. Windows reserved filenames (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    # These cannot be filenames even with an extension (e.g., CON.txt is bad)
    reserved_names = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}  # fmt: skip
    filename = filename.rstrip(". ") or "unnamed_file"
    # Windows reserves the first component even when multiple extensions follow.
    base_name = filename.split(".", 1)[0].rstrip(" ").upper()
    if base_name in reserved_names:
        filename = f"{replacement}{filename}"
    # 3. Strip trailing dots and spaces (Windows ignores/removes these)
    filename = filename.rstrip(". ")
    # Non-BMP characters consume two UTF-16 code units; never split a surrogate pair.
    filename = filename.encode("utf-16-le")[: max_length * 2].decode("utf-16-le", errors="ignore").rstrip(". ")
    if filename.split(".", 1)[0].rstrip(" ").upper() in reserved_names:
        filename = (
            ("_" + filename).encode("utf-16-le")[: max_length * 2].decode("utf-16-le", errors="ignore").rstrip(". ")
        )
    # 5. Handle empty strings (if sanitization removed everything)
    return filename or "_"
