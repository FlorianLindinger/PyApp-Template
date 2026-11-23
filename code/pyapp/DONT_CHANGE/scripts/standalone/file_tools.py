"""Filesystem helpers: a cross-process file lock, atomic JSON writes, safe folder removal, paths.

Standalone: copy this file anywhere. Standard library only; FileLock is Windows only (msvcrt).
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Union

_local_locks = threading.local()


# The type of FileLock or a subclass, for __enter__ (typing.Self needs Python 3.11).
_FileLockT = TypeVar("_FileLockT", bound="FileLock")


class FileLock:
    """A reentrant, process-shared lock; Windows releases it after a crash."""

    def __init__(self, path: Union[str, Path], timeout: float = 120) -> None:
        """Store the normalized lock path and acquisition timeout."""
        self.path = str(Path(path).resolve())
        self.timeout = timeout

    def __enter__(self: _FileLockT) -> _FileLockT:
        """Acquire or reenter the checkout's file lock, waiting up to the configured timeout."""
        # msvcrt.locking locks the first byte of the lock file. Windows releases such a lock by itself when
        # the process ends, even after a crash, so a crashed launcher can never block the others forever.
        import msvcrt

        held: Optional[Dict[str, List[Any]]] = getattr(_local_locks, "held", None)
        if held is None:
            held = {}
            _local_locks.held = held
        if self.path in held:
            held[self.path][1] += 1
            return self
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        stream = Path(self.path).open("a+b")
        if stream.seek(0, 2) == 0:
            stream.write(b"\0")
            stream.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                held[self.path] = [stream, 1]
                return self
            except OSError:
                if time.monotonic() >= deadline:
                    stream.close()
                    raise TimeoutError("Another launcher is busy: " + self.path) from None
                time.sleep(0.05)

    def __exit__(self, *exc: object) -> None:
        """Release one acquisition and close the file lock when the final nested context exits."""
        import msvcrt

        stream, count = _local_locks.held[self.path]
        if count > 1:
            _local_locks.held[self.path][1] -= 1
        else:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            stream.close()
            del _local_locks.held[self.path]


def atomic_json(path: Union[str, Path], payload: object) -> None:
    """Write JSON through a unique sibling file and atomically replace the destination."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        Path(temp).replace(path)
    finally:
        temp.unlink(missing_ok=True)


def remove_tree_inside(path: str, base: str) -> None:
    """Delete a folder tree only if it lies strictly inside base; a link is removed, never followed."""
    import shutil

    root = os.path.realpath(base)
    if Path(path).is_symlink() or _is_junction(path):
        # Only the link itself goes, so where it leads does not matter (realpath would follow it and
        # refuse a link to a folder outside base); the place of the link must be inside base.
        link = Path(path).absolute()
        location = str(Path(os.path.realpath(link.parent)) / link.name)
        if not _strictly_inside(location, root):
            raise ValueError(f'Refusing to delete "{path}": it is not inside "{base}".')
        Path(path).rmdir() if Path(path).is_dir() else Path(path).unlink()
        return
    target = os.path.realpath(path)
    if not _strictly_inside(target, root):
        raise ValueError(f'Refusing to delete "{path}": it is not inside "{base}".')
    shutil.rmtree(target)


def _strictly_inside(path: str, root: str) -> bool:
    """True if path is below root (both absolute and resolved), not root itself."""
    try:
        common = os.path.commonpath([path, root])
    except ValueError:  # different drives
        return False
    return os.path.normcase(common) == os.path.normcase(root) and os.path.normcase(path) != os.path.normcase(root)


def _is_junction(path: str) -> bool:
    """True for Windows junctions/reparse-point folders (works on Python 3.8)."""
    try:
        return bool(os.lstat(path).st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except (OSError, AttributeError):
        return False


def make_abs_path_relative_to_file(path: str, file: str) -> str:
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    # Keep os.path.isabs: rooted Windows paths have different pathlib semantics on Python 3.8-3.12.
    if not os.path.isabs(path):  # noqa: PTH117
        return os.path.normpath(str(Path(file).parent) + "\\" + path)
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
