"""The project's Python: find or install it with uv, and the backend/environment/.python-version file."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile

from backend.DONT_CHANGE.backend_settings import MINIMUM_PYTHON, PYTHON_VERSION_FILE, RUNTIME_CACHE_PATH
from backend.DONT_CHANGE.scripts.banner import show_setup_window
from backend.DONT_CHANGE.scripts.config import settings
from backend.DONT_CHANGE.scripts.console_tools import print_step
from backend.DONT_CHANGE.scripts.env.uv import install_newer_uv, run_uv, run_uv_captured
from backend.DONT_CHANGE.scripts.errors import SetupError


def interpreter_version(exe: str) -> tuple:
    """Return (major, minor, micro) of an interpreter without running site or user code."""
    output = subprocess.check_output(
        [exe, "-I", "-S", "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
        universal_newlines=True,
        timeout=30,
    )
    return tuple(int(part) for part in output.strip().split("."))


def version_text(version: tuple) -> str:
    return ".".join(str(part) for part in version)


def find_python(request: str, s=None) -> str | None:
    """Return the interpreter uv would use for a request ("" = system default), or None."""
    arguments = ["python", "find", "--no-project"] + ([request] if request else [])
    # Run outside the project, otherwise uv returns the project .venv's interpreter.
    code, out, _ = run_uv_captured(arguments, check=False, cwd=tempfile.gettempdir(), s=s)
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return lines[-1] if code == 0 and lines else None


def python_downloads(all_versions=False, s=None) -> list:
    """Downloadable CPython builds for this PC as uv reports them."""
    arguments = ["python", "list", "--only-downloads", "--output-format", "json"]
    if all_versions:
        arguments.append("--all-versions")
    code, out, _ = run_uv_captured(arguments, check=False, cwd=tempfile.gettempdir(), s=s)
    if code:
        return []
    try:
        entries = json.loads(out)
    except ValueError:
        return []
    return [e for e in entries if e.get("implementation") == "cpython" and e.get("variant") == "default"]


def version_key(text: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", text)[:3])


def newest_stable_minor(s=None) -> str:
    """Return "X.Y" of the newest stable CPython uv offers."""
    stable = [e["version"] for e in python_downloads(s=s) if re.fullmatch(r"\d+\.\d+\.\d+", e.get("version", ""))]
    if not stable:
        raise SetupError(
            'uv could not list downloadable Python versions (no internet?). Set python_version, e.g. "3.14".'
        )
    newest = max(stable, key=version_key)
    return ".".join(newest.split(".")[:2])


def available_summary(s=None) -> str:
    """One line describing which Python versions uv can install here."""
    versions = sorted({e["version"] for e in python_downloads(True, s)}, key=version_key)
    if not versions:
        return "uv could not list the downloadable versions (no internet?)."
    minors = []
    for v in versions:
        minor = ".".join(v.split(".")[:2])
        if minor not in minors:
            minors.append(minor)
    return f"uv offers {versions[0]} to {versions[-1]} for this PC (minor versions: {', '.join(minors)})."


def install_python(request: str, s=None) -> str:
    """Install a Python with uv (location per python_source) and return its executable."""
    s = s or settings()
    show_setup_window()
    print_step(f"Installing Python {request} with uv...")
    arguments = ["python", "install", request]
    failed = run_uv(arguments, check=False, cwd=tempfile.gettempdir(), s=s)
    if failed and install_newer_uv():
        invalidate_runtime_cache()  # the next launch looks up uv again and finds the newer one
        failed = run_uv(arguments, check=False, cwd=tempfile.gettempdir(), s=s)
    if failed:
        raise SetupError(
            f"uv could not install Python '{request}'. {available_summary(s)} The launcher needs Python 3.8 or newer. "
            "Check python_version in developer_settings.py."
        )
    exe = find_python(request, s)
    if not exe:
        raise SetupError(f"Python {request} was installed but uv cannot find it.")
    return exe


def find_or_install_python(request: str, s=None) -> str:
    """Return a usable interpreter for request, installing it if needed, and check the 3.8 minimum."""
    exe = find_python(request, s) or install_python(request, s)
    version = interpreter_version(exe)
    if version[:2] < MINIMUM_PYTHON:
        raise SetupError(
            f"Python {version_text(version)} is older than 3.8, which the launcher needs. Choose python_version 3.8 or newer."
        )
    return exe


def read_python_version_file() -> str | None:
    """Return the request stored in backend/environment/.python-version, or None."""
    try:
        with open(PYTHON_VERSION_FILE, encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line and not line.startswith("#"):
                    return line
    except OSError:
        pass
    return None


def write_python_version_file(request: str) -> None:
    with open(PYTHON_VERSION_FILE, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(request + "\n")


def request_matches(setting_value: str, file_value: str | None) -> bool:
    """python_version "" accepts the Python chosen earlier; otherwise both requests must be equal."""
    if file_value is None:
        return False
    if not setting_value:
        return True
    return setting_value.strip().lower() == file_value.strip().lower()


def invalidate_runtime_cache() -> None:
    """Make the next batch bootstrap look up uv and Python again."""
    try:
        os.remove(RUNTIME_CACHE_PATH)
    except OSError:
        pass
