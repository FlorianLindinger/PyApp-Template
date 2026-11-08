"""Running uv for the launcher: which uv, its environment variables (mirrors resolve_runtime.ps1) and calls."""

from __future__ import annotations

import os
import shutil
import subprocess

from backend.DONT_CHANGE.backend_settings import (
    LOCAL_PYTHONS_DIR,
    LOCAL_UV_CACHE_DIR,
    LOCAL_UV_EXE,
    PROJECT_DIR,
    RESOLVE_RUNTIME_PATH,
    SHARED_UV_EXE,
)
from backend.DONT_CHANGE.scripts.config import settings
from backend.DONT_CHANGE.scripts.errors import SetupError


def uv_exe() -> str:
    """Return the uv chosen by the bootstrap, or the best available fallback."""
    path = os.environ.get("PYAPP_UV", "")
    if path and os.path.isfile(path):
        return path
    if os.path.isfile(LOCAL_UV_EXE):
        return LOCAL_UV_EXE
    found = shutil.which("uv")
    if found:
        return found
    raise SetupError(
        "uv was not found. Start the app through a shortcut or 'Setup - run first and after moving folder.cmd' so the bootstrap can install it."
    )


def install_newer_uv() -> bool:
    """Fetch the newest uv into the per-user folder; True when this process now uses a newer uv."""
    arguments = [
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        RESOLVE_RUNTIME_PATH,
    ]
    code = subprocess.run(["powershell.exe", *arguments, "-InstallNewerThan", uv_exe()], check=False).returncode
    if code:
        return False
    os.environ["PYAPP_UV"] = SHARED_UV_EXE
    return True


_OWN_UV_VARIABLES = (
    "UV_PYTHON",
    "UV_PYTHON_INSTALL_DIR",
    "UV_MANAGED_PYTHON",
    "UV_NO_MANAGED_PYTHON",
    "UV_PYTHON_PREFERENCE",
    "UV_PYTHON_INSTALL_BIN",
    "UV_PYTHON_INSTALL_REGISTRY",
    "UV_PROJECT_ENVIRONMENT",
    "UV_PROJECT",
    "UV_WORKING_DIR",
    "UV_NO_SYNC",
    "UV_FROZEN",
    "UV_LOCKED",
    "UV_OFFLINE",
    "UV_CACHE_DIR",
    "UV_PYTHON_DOWNLOADS",
)


def uv_environment(s=None, project_environment: str | None = None, python_command: bool = True) -> dict:
    """Environment for uv calls. Mirrors Set-UvEnvironment in bootstrap/resolve_runtime.ps1.

    The user's other UV_* settings (index URLs, proxies, ...) are kept on purpose.
    """
    s = s or settings()
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("PYTHON", "PIP_", "CONDA_"))
        and key.upper() not in ("VIRTUAL_ENV", "PYAPP_ENTRY_SCRIPT")
        and key.upper() not in _OWN_UV_VARIABLES
    }
    if s.python_source == "uv_user":
        visible = "1" if s.uv_user_python_visible_globally else "0"
        env.update(UV_MANAGED_PYTHON="1", UV_PYTHON_INSTALL_BIN=visible, UV_PYTHON_INSTALL_REGISTRY=visible)
    else:
        env.update(
            UV_PYTHON_INSTALL_DIR=LOCAL_PYTHONS_DIR,
            UV_MANAGED_PYTHON="1",
            UV_PYTHON_INSTALL_BIN="0",
            UV_PYTHON_INSTALL_REGISTRY="0",
        )
    if s.uv_cache == "local":
        env["UV_CACHE_DIR"] = LOCAL_UV_CACHE_DIR
    if s.use_system_certificates:
        env["UV_SYSTEM_CERTS"] = "1"
    env["UV_PYTHON_DOWNLOADS"] = "automatic"
    # The uv cache is often on another drive than the project; copying avoids uv's hard-link warning.
    env.setdefault("UV_LINK_MODE", "copy")
    if project_environment:
        env["UV_PROJECT_ENVIRONMENT"] = project_environment
    if not python_command and env.pop("UV_MANAGED_PYTHON", None):
        # Project commands always get an explicit --python. "Only managed" would make uv re-check
        # the venv against interpreter details it cached before a move/re-link and rebuild the venv.
        env["UV_PYTHON_PREFERENCE"] = "managed"
    return env


def _run(arguments, capture: bool, check: bool, cwd, project_environment, s) -> subprocess.CompletedProcess:
    if not cwd:
        os.makedirs(PROJECT_DIR, exist_ok=True)
    result = subprocess.run(
        [uv_exe(), *arguments],
        check=False,
        cwd=cwd or PROJECT_DIR,
        env=uv_environment(s, project_environment, python_command=arguments[:1] == ["python"]),
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True if capture else None,
        encoding="utf-8" if capture else None,
        errors="replace" if capture else None,
    )
    if check and result.returncode:
        detail = (result.stderr or "").strip() if capture else ""
        raise SetupError(
            "uv "
            + " ".join(arguments[:2])
            + f" failed (exit code {result.returncode})."
            + ("\n" + detail if detail else "")
        )
    return result


def run_uv(arguments, *, check=True, cwd=None, project_environment=None, s=None) -> int:
    """Run uv with its output shown; return the exit code (check=True raises SetupError on failure)."""
    return _run(arguments, False, check, cwd, project_environment, s).returncode


def run_uv_captured(arguments, *, check=True, cwd=None, project_environment=None, s=None) -> tuple[int, str, str]:
    """Run uv quietly; return (exit code, stdout, stderr)."""
    result = _run(arguments, True, check, cwd, project_environment, s)
    return result.returncode, result.stdout or "", result.stderr or ""


def uv_version() -> str:
    """Return the uv version string, e.g. "0.11.32"."""
    _, out, _ = run_uv_captured(["--version"], check=False)
    parts = out.split()
    return parts[1] if len(parts) > 1 else "?"


def uv_succeeds(arguments, project_environment=None, s=None) -> bool:
    """Try a uv command without printing anything (used for offline-first attempts)."""
    code, _, _ = run_uv_captured(arguments, check=False, project_environment=project_environment, s=s)
    return code == 0
