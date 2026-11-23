"""The project's Python: find or install it with uv, and the pyapp/generated/.python-version file."""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Dict, List, Optional, Tuple, Union

from pyapp.DONT_CHANGE.pyapp_settings import MINIMUM_PYTHON, PYTHON_VERSION_FILE, RUNTIME_CACHE_PATH
from pyapp.DONT_CHANGE.scripts.banner import show_setup_window
from pyapp.DONT_CHANGE.scripts.config import settings
from pyapp.DONT_CHANGE.scripts.console_tools import print_step
from pyapp.DONT_CHANGE.scripts.env.uv import install_newer_uv, run_uv, run_uv_captured
from pyapp.DONT_CHANGE.scripts.errors import SetupError
from pyapp.DONT_CHANGE.scripts.standalone.python_request import allows, recorded_request, uv_request


def interpreter_version(exe: str) -> Tuple[int, ...]:
    """Return (major, minor, micro) of an interpreter without running site or user code."""
    # Probe the configured Python interpreter with fixed isolated Python source.
    try:
        output = subprocess.check_output(  # noqa: S603
            [exe, "-I", "-S", "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
            universal_newlines=True,
            timeout=30,
        )
        return tuple(int(part) for part in output.strip().split("."))
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        # Blocked by a policy, crashed, hung, or printed something else: a message, not a traceback.
        raise SetupError(f'The Python at "{exe}" could not be started or did not report its version: {error}') from None


def version_text(version: Tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version)


def find_python(request: str, s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> Optional[str]:
    """Return the interpreter uv would use for a request ("" = system default), or None."""
    arguments = ["python", "find", "--no-project"] + ([uv_request(request)] if request else [])
    # Run outside the project, otherwise uv returns the project .venv's interpreter.
    code, out, _ = run_uv_captured(arguments, check=False, cwd=tempfile.gettempdir(), s=s)
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return lines[-1] if code == 0 and lines else None


def python_downloads(
    all_versions: bool = False, s: Optional[Union[ModuleType, SimpleNamespace]] = None
) -> List[Dict[str, str]]:
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


def version_key(text: str) -> Tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", text)[:3])


def newest_stable_minor(s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> str:
    """Return "X.Y" of the newest stable CPython uv offers."""
    stable = [e["version"] for e in python_downloads(s=s) if re.fullmatch(r"\d+\.\d+\.\d+", e.get("version", ""))]
    if not stable:
        raise SetupError(
            'uv could not list downloadable Python versions (no internet?). Set python_version, e.g. "3.14".'
        )
    newest = max(stable, key=version_key)
    return ".".join(newest.split(".")[:2])


def newest_allowed(value: str, s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> Optional[str]:
    """The .python-version text for the newest stable CPython a loose python_version allows, or None."""
    allowed = [
        version_key(e["version"])
        for e in python_downloads(True, s)
        if re.fullmatch(r"\d+\.\d+\.\d+", e.get("version", "")) and allows(value, version_key(e["version"]))
    ]
    return recorded_request(value, max(allowed)) if allowed else None


def python_offered(request: str, s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> Optional[bool]:
    """Whether this uv has a download for request: True, False, or None when its answer is unclear.

    uv matches the request itself, so free-threaded, PyPy and range requests count too. The list is
    built into uv, so it also answers offline. An older uv that does not accept a request here
    gives None.
    """
    arguments = ["python", "list", uv_request(request), "--only-downloads", "--all-versions", "--output-format", "json"]
    code, out, _ = run_uv_captured(arguments, check=False, cwd=tempfile.gettempdir(), s=s)
    if code:
        return None
    try:
        entries = json.loads(out)
    except ValueError:
        return None
    return bool(entries) if isinstance(entries, list) else None


def available_summary(s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> str:
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


def install_python(request: str, s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> str:
    """Install a Python with uv (location per python_source) and return its executable."""
    s = s or settings()
    if s.python_source == "system":
        raise SetupError(
            f"python_source is \"system\", but no Python '{request}' is installed on this PC. Install one, "
            "or change python_version in developer_settings.py."
        )
    show_setup_window()
    print_step(f"Installing Python {request} with uv...")
    arguments = ["python", "install", uv_request(request)]
    failed = run_uv(arguments, check=False, cwd=tempfile.gettempdir(), s=s)
    # A newer uv only helps when this one does not know the requested Python; when it does, the
    # download itself failed (offline, proxy) and fetching another uv would fail the same way.
    # An unclear answer keeps the retry.
    if failed and python_offered(request, s) is not True and install_newer_uv():
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


def find_or_install_python(request: str, s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> str:
    """Return a usable interpreter for request, installing it if needed, and check the 3.8 minimum."""
    exe = find_python(request, s) or install_python(request, s)
    version = interpreter_version(exe)
    if version[:2] < MINIMUM_PYTHON:
        raise SetupError(
            f"Python {version_text(version)} is older than 3.8, which the launcher needs. Choose python_version 3.8 or newer."
        )
    return exe


def read_python_version_file() -> Optional[str]:
    """Return the request stored in pyapp/generated/.python-version, or None."""
    try:
        with Path(PYTHON_VERSION_FILE).open(encoding="utf-8") as stream:
            for raw_line in stream:
                line = raw_line.strip()
                if line and not line.startswith("#"):
                    return line
    except OSError:
        pass
    return None


def write_python_version_file(request: str) -> None:
    with Path(PYTHON_VERSION_FILE).open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(request + "\n")


def invalidate_runtime_cache() -> None:
    """Make the next batch bootstrap look up uv and Python again."""
    with contextlib.suppress(OSError):
        Path(RUNTIME_CACHE_PATH).unlink()
