"""Shared helpers: a writable copy of developer_settings.py that the template modules use."""

import contextlib
import importlib.util
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from project_location import CODE

# isort: split

from backend.DONT_CHANGE.scripts import config
from backend.DONT_CHANGE.scripts.env import pyproject, pythons, uv, venv


def load_settings_file(path):
    """Import a developer_settings.py copy as a fresh module (raises what the file raises)."""
    spec = importlib.util.spec_from_file_location("developer_settings_under_test", str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def temporary_settings(transform=None):
    """Yield (settings path, loader) for a temporary copy that config and scripts/environment read and write.

    transform(text) -> text changes the copy first. pyproject.toml and uv.lock also point into the
    temporary folder, so nothing in the checkout is touched.
    """
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "developer_settings.py"
        shutil.copyfile(CODE / "backend" / "developer_settings.py", path)
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
