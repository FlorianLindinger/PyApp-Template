"""Shared helpers: a writable copy of developer_settings.py that the template modules use."""

from __future__ import annotations

import contextlib
import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Optional
from unittest import mock

from project_location import CODE, DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE.scripts import config
from pyapp.DONT_CHANGE.scripts.env import pyproject, pythons, uv, venv


def load_settings_file(path: Path):
    """Import a developer_settings.py copy as a fresh module (raises what the file raises)."""
    spec = importlib.util.spec_from_file_location("developer_settings_under_test", str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load test settings from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def temporary_settings(transform: Optional[Callable[[str], str]] = None):
    """Yield (settings path, loader) for a temporary copy that config and scripts/env read and write.

    transform(text) -> text changes the copy first. pyproject.toml and uv.lock also point into the
    temporary folder, so nothing in the checkout is touched.
    """
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "developer_settings.py"
        shutil.copyfile(CODE / "pyapp" / "developer_settings.py", path)
        if transform is not None:
            text = path.read_bytes().decode("utf-8")
            path.write_bytes(transform(text).encode("utf-8"))

        def load():
            return load_settings_file(path)

        replacements = {
            "DEV_SETTINGS_PATH": str(path),
            "settings": load,
            "PYPROJECT_PATH": str(Path(folder) / "pyproject.toml"),
            "UV_LOCK_PATH": str(Path(folder) / "uv.lock"),
            "DEFAULT_SETTINGS_PATH": str(DONT_CHANGE / "data" / "dev_settings_default.py"),
        }
        patches = [
            mock.patch.object(module, name, value)
            for module in (config, uv, pythons, pyproject, venv)
            for name, value in replacements.items()
            if hasattr(module, name)
        ]
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            yield path, load
