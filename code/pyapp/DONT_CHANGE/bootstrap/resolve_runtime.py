"""Find or install uv and the Python that runs the launcher, and record both in tmp/runtime.cmd.

Started by resolve_runtime.bat when that cache is missing or stale, with any working uv and Python
(-I -S: standard library only). Standalone on purpose: it has to work before the launcher's own
Python environment exists. The launcher also runs it with --install-newer-than.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import msvcrt
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
import uuid
import winreg
import zipfile
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

BOOTSTRAP_DIR = Path(__file__).resolve().parent
DONT_CHANGE_DIR = BOOTSTRAP_DIR.parent
BACKEND_DIR = DONT_CHANGE_DIR.parent
SETTINGS_PATH = BACKEND_DIR / "developer_settings.py"
TEMPORARY_DIR = DONT_CHANGE_DIR / "tmp"
CACHE_PATH = TEMPORARY_DIR / "runtime.cmd"
GENERATED_DIR = BACKEND_DIR / "generated"
LOCAL_UV_DIR = GENERATED_DIR / "uv"
LOCAL_UV_EXE = LOCAL_UV_DIR / "uv.exe"
# A per-user uv shared by projects, never on PATH: used when the usual uv is too old for a Python.
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA") or Path(os.environ.get("USERPROFILE", "~")) / "AppData" / "Local")
SHARED_UV_DIR = USER_DATA_DIR / "PyApp-Template" / "uv"
SHARED_UV_EXE = SHARED_UV_DIR / "uv.exe"
BOOTSTRAP_UV_DIR = USER_DATA_DIR / "PyApp-Template" / "uv-bootstrap"  # from resolve_runtime.bat; removed when done
LOCAL_PYTHONS_DIR = GENERATED_DIR / "pythons"
LOCAL_CACHE_DIR = GENERATED_DIR / "uv-cache"
VERSION_FILE = GENERATED_DIR / ".python-version"
MINIMUM_PYTHON = (3, 8)
DOWNLOAD_TIMEOUT_SECONDS = 300
OWN_UV_VARIABLES = (
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
    "VIRTUAL_ENV",
)
# Windows error codes of a program that was refused rather than broken.
POLICY_ERRORS = {5, 225, 1260, 4551}
Settings = Dict[str, object]

_start_problems: List[str] = []


class BootstrapError(Exception):
    """A problem with a message for the user; no traceback needed."""


# ---------------------------------------------------------------- output


def _enable_colors() -> None:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except (AttributeError, OSError):
        pass  # plain escape codes are only a cosmetic problem


def step(message: str) -> None:
    """Same look as the Python side (scripts/console_tools.py)."""
    marker = "\x1b[1;36m»\x1b[0m" if sys.stdout.isatty() else "»"
    print(f"{marker} {message}", flush=True)


def show_error(message: str) -> None:
    badge = "\x1b[1;37;41m ERROR \x1b[0m" if sys.stdout.isatty() else " ERROR "
    print(f"\n{badge} {message}\n", flush=True)
    show_failure_dialog(message)


def show_failure_dialog(message: str) -> None:
    """Shortcuts start this window minimized, where an error could go unnoticed."""
    if os.environ.get("PYAPP_ENTRYPOINT_NO_PAUSE") == "1":
        return  # Setup's window is visible
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "PyApp launcher", 0x10 | 0x10000)
    except (AttributeError, OSError):
        pass  # the window has the message too


def explain_start_failure(path: object, error: OSError) -> str:
    """Why a program would not start, in words that tell the user what to do."""
    if getattr(error, "winerror", None) in POLICY_ERRORS:
        return (
            f'Windows refused to start "{path}". A company policy (AppLocker, Windows Defender Application Control) '
            "or an antivirus program may block programs in this folder. Ask your IT department to allow it, or use a "
            'Python they installed with python_source = "system" in developer_settings.py.'
        )
    return f'"{path}" could not be started: {error}'


# ---------------------------------------------------------------- settings


def read_settings(text: str) -> Settings:
    """The [bootstrap] settings: top-level, one-line plain literals only. Like Python, the last definition wins."""
    result: Settings = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]*)?=\s*(.*)$", line)
        if not match:
            continue
        name, raw = match.group(1), match.group(2).strip()
        if raw[:1] in ('"', "'"):
            end = raw.find(raw[0], 1)
            if end < 0:
                result.pop(name, None)
            else:
                result[name] = raw[1:end]
        else:
            token = re.split(r"[\s#]", raw, maxsplit=1)[0]
            if token in ("True", "False", "None"):
                result[name] = {"True": True, "False": False, "None": None}[token]
            else:
                result.pop(name, None)  # not a plain literal: use the default
    return result


def setting(settings: Settings, name: str, default: object) -> object:
    return settings.get(name, default) if name in settings else default


def assert_choice(name: str, value: object, choices: Tuple[str, ...]) -> None:
    if value not in choices:
        raise BootstrapError(
            f"developer_settings.py: {name} = '{value}' is not valid. Use one of: {', '.join(choices)}."
        )


# ---------------------------------------------------------------- versions


def version_tuple(text: str) -> Optional[Tuple[int, ...]]:
    """Numbers of a version, padded to four, so that 0.11 and 0.11.0 are equal; None if there are none."""
    clean = re.sub(r"[^0-9.].*$", "", text).strip(".")
    if not clean:
        return None
    parts = [int(part) for part in clean.split(".")[:4]]
    return tuple(parts + [0] * (4 - len(parts)))


def version_satisfies(version: Optional[str], spec: str) -> bool:
    """ "" = any; "0.11.32" = exact; ">=0.9,<1" etc.; "~=0.11" = compatible release."""
    if not spec.strip():
        return True
    actual = version_tuple(version or "")
    if actual is None:
        return False
    for clause in spec.split(","):
        clause = clause.strip()
        if not clause:
            continue
        match = re.fullmatch(r"(>=|<=|==|!=|~=|>|<)?\s*([0-9][0-9.]*)", clause)
        if not match:
            raise BootstrapError(f"developer_settings.py: uv_version clause '{clause}' is not understood.")
        operator, text = match.group(1), match.group(2)
        wanted = version_tuple(text) or ()
        if operator == "~=":
            prefix = text.split(".")[:-1]
            if actual < wanted or list(map(str, actual[: len(prefix)])) != prefix:
                return False
        elif not {
            ">=": actual >= wanted,
            "<=": actual <= wanted,
            ">": actual > wanted,
            "<": actual < wanted,
            "!=": actual != wanted,
        }.get(operator or "==", actual == wanted):
            return False
    return True


def exact_version(spec: str) -> Optional[str]:
    match = re.fullmatch(r"\s*(?:==)?\s*([0-9]+\.[0-9]+\.[0-9]+)\s*", spec)
    return match.group(1) if match else None


# ---------------------------------------------------------------- running programs


def run_captured(executable: object, arguments: List[str]) -> Tuple[int, List[str]]:
    """(exit code, non-empty output lines). A program that cannot start counts as failed and is remembered."""
    try:
        # The uv and Python chosen by this bootstrap, with fixed arguments.
        completed = subprocess.run([str(executable), *arguments], capture_output=True, check=False)  # noqa: S603
    except OSError as error:
        _start_problems.append(explain_start_failure(executable, error))
        return 1, []
    output = completed.stdout.decode("utf-8", "replace").splitlines()
    return completed.returncode, [line for line in output if line.strip()]


def run_live(executable: object, arguments: List[str]) -> int:
    try:
        # The uv chosen by this bootstrap, with fixed arguments.
        return subprocess.run([str(executable), *arguments], check=False).returncode  # noqa: S603
    except OSError as error:
        raise BootstrapError(explain_start_failure(executable, error)) from error


def download(url: str, target: Path) -> None:
    """Uses Windows' proxy settings and certificate store, which also suits company networks."""
    try:
        # A fixed https://github.com address for uv's releases.
        request = urllib.request.Request(url, headers={"User-Agent": "PyApp-Template"})  # noqa: S310
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response, target.open("wb") as stream:  # noqa: S310
            shutil.copyfileobj(response, stream)
    except (urllib.error.URLError, OSError) as error:
        raise BootstrapError(
            f"Could not download {url}: {error}. A firewall or proxy may block it. Ask your IT department to allow "
            "github.com, or copy a folder made with the make_portable dev tool to this PC."
        ) from error


# ---------------------------------------------------------------- uv


def uv_version_of(executable: object) -> Optional[str]:
    code, lines = run_captured(executable, ["--version"])
    fields = lines[0].split() if code == 0 and lines else []
    return fields[1] if len(fields) > 1 else None


def is_inside(path: Path, folder: Path) -> bool:
    return os.path.normcase(str(path)).startswith(os.path.normcase(str(folder)) + os.sep)


def find_global_uv() -> Optional[Path]:
    candidates = [Path(folder) / "uv.exe" for folder in os.environ.get("PATH", "").split(os.pathsep) if folder]
    home = Path(os.environ.get("USERPROFILE", "~"))
    install_dirs = [
        os.environ.get("UV_INSTALL_DIR"),
        os.environ.get("XDG_BIN_HOME"),
        home / ".local" / "bin",
        home / ".cargo" / "bin",
    ]
    candidates += [Path(folder) / "uv.exe" for folder in install_dirs if folder]
    for candidate in candidates:
        if candidate.is_file() and not is_inside(candidate.absolute(), LOCAL_UV_DIR):
            return candidate.absolute()
    return None


def uv_release_target() -> str:
    architecture = os.environ.get("PROCESSOR_ARCHITEW6432") or os.environ.get("PROCESSOR_ARCHITECTURE", "")
    targets = {"AMD64": "x86_64-pc-windows-msvc", "ARM64": "aarch64-pc-windows-msvc", "x86": "i686-pc-windows-msvc"}
    if architecture not in targets:
        raise BootstrapError(f"Unsupported Windows architecture '{architecture}' for uv.")
    return targets[architecture]


def fetch_uv_folder(spec: str, stage: Path) -> Path:
    """A folder with a checked uv.exe: the one the batch stage already fetched if it fits, else a verified download."""
    extracted = stage / "extracted"
    bootstrap_uv = os.environ.get("PYAPP_BOOT_UV", "")
    if (
        bootstrap_uv
        and is_inside(Path(bootstrap_uv), BOOTSTRAP_UV_DIR)
        and version_satisfies(uv_version_of(bootstrap_uv), spec)
    ):
        shutil.copytree(str(Path(bootstrap_uv).parent), str(extracted))
        return extracted
    exact = exact_version(spec)
    file_name = f"uv-{uv_release_target()}.zip"
    base = (
        f"https://github.com/astral-sh/uv/releases/download/{exact}"
        if exact
        else "https://github.com/astral-sh/uv/releases/latest/download"
    )
    archive = stage / file_name
    checksum = stage / (file_name + ".sha256")
    download(f"{base}/{file_name}", archive)
    download(f"{base}/{file_name}.sha256", checksum)
    expected = checksum.read_text(encoding="utf-8").split()[0].lower()
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise BootstrapError("The downloaded uv archive does not match its published SHA-256 checksum.")
    with zipfile.ZipFile(archive) as stream:
        stream.extractall(extracted)
    return extracted


def install_uv(spec: str, destination: Path) -> Path:
    """Put uv into its own folder (replacing an earlier one) and return uv.exe."""
    exact = exact_version(spec)
    step(f"Getting uv {exact or '(latest)'} for {destination} ...")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Next to the destination: a rename cannot cross drives.
    stage = destination.parent / ("uv-download-" + uuid.uuid4().hex)
    stage.mkdir()
    try:
        extracted = fetch_uv_folder(spec, stage)
        found = next(extracted.rglob("uv.exe"), None)
        if found is None:
            raise BootstrapError("The uv archive did not contain uv.exe.")
        version = uv_version_of(found)
        if not version_satisfies(version, spec):
            raise BootstrapError(
                f"The latest uv ({version}) does not satisfy uv_version '{spec}'. Use an exact version in uv_version."
            )
        previous = Path(str(destination) + ".previous")
        shutil.rmtree(previous, ignore_errors=True)
        if destination.exists():
            destination.rename(previous)
        found.parent.rename(destination)
        shutil.rmtree(previous, ignore_errors=True)
        step(f"uv {version} installed in {destination}")
        return destination / "uv.exe"
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def user_bin_folder() -> Path:
    """The folders Astral's own installer uses, in the same order."""
    for variable in ("UV_INSTALL_DIR", "XDG_BIN_HOME"):
        if os.environ.get(variable):
            return Path(os.environ[variable])
    return Path(os.environ.get("USERPROFILE", "~")) / ".local" / "bin"


def add_to_user_path(folder: Path, key_path: str = "Environment") -> None:
    """Works on the stored value, so that entries such as %USERPROFILE% stay as they are."""
    access = winreg.KEY_READ | winreg.KEY_SET_VALUE
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, access) as key:
        try:
            current = str(winreg.QueryValueEx(key, "Path")[0])
        except FileNotFoundError:
            current = ""
        entries = [entry for entry in current.split(";") if entry]
        if str(folder) not in entries:
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join([*entries, str(folder)]))


def announce_environment_change() -> None:
    """Tell running programs such as Explorer that the user's PATH changed."""
    try:
        import ctypes

        result = ctypes.c_size_t()
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002, 1000, ctypes.byref(result))
    except (AttributeError, OSError):
        pass  # new windows after the next sign-in have it anyway


def install_global_uv(spec: str) -> Path:
    folder = user_bin_folder()
    folder.mkdir(parents=True, exist_ok=True)
    # Unpacked into a folder of its own: other programs can live in the destination.
    stage = folder / ("uv-install-" + uuid.uuid4().hex)
    try:
        install_uv(spec, stage)
        for executable in stage.glob("*.exe"):
            shutil.copy2(str(executable), str(folder))
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    if not os.environ.get("UV_NO_MODIFY_PATH"):
        add_to_user_path(folder)
        announce_environment_change()
    uv = find_global_uv()
    if uv is None:
        raise BootstrapError(f"uv was installed in {folder} but could not be found there.")
    step(f"uv is installed for your Windows user in {folder}")
    return uv


def resolve_uv(settings: Settings) -> Path:
    prefer = setting(settings, "uv_prefer", "global")
    install = setting(settings, "uv_install_if_missing", "global")
    spec = str(setting(settings, "uv_version", ""))
    assert_choice("uv_prefer", prefer, ("global", "local"))
    assert_choice("uv_install_if_missing", install, ("global", "local", "never"))
    global_uv = find_global_uv()
    local_uv = LOCAL_UV_EXE if LOCAL_UV_EXE.is_file() else None
    outdated = None
    for candidate in [local_uv, global_uv] if prefer == "local" else [global_uv, local_uv]:
        if candidate is None:
            continue
        version = uv_version_of(candidate)
        if version and version_satisfies(version, spec):
            return candidate
        if candidate == global_uv:
            outdated = f"{candidate} ({version})"
    if install == "never":
        detail = f" (global uv {outdated} does not satisfy uv_version '{spec}')" if outdated else ""
        raise BootstrapError(
            f"No usable uv found{detail} and uv_install_if_missing = 'never'. Install uv or change the uv settings in developer_settings.py."
        )
    if outdated:
        step(
            f"The global uv {outdated} does not satisfy uv_version '{spec}'; it is left unchanged and a local uv is installed instead."
        )
        return install_uv(spec, LOCAL_UV_DIR)
    if install == "global":
        return install_global_uv(spec)
    return install_uv(spec, LOCAL_UV_DIR)


def shared_uv_allowed(settings: Settings) -> bool:
    """An exact uv_version is a deliberate pin, and "never" means the launcher must not fetch uv."""
    return setting(settings, "uv_install_if_missing", "global") != "never" and not exact_version(
        str(setting(settings, "uv_version", ""))
    )


def select_newest_uv(settings: Settings, uv: Path) -> Path:
    """The shared uv exists because an older one could not provide a Python: keep using it."""
    if not shared_uv_allowed(settings) or not SHARED_UV_EXE.is_file():
        return uv
    shared = uv_version_of(SHARED_UV_EXE)
    if not shared or not version_satisfies(shared, str(setting(settings, "uv_version", ""))):
        return uv
    return SHARED_UV_EXE if (version_tuple(shared) or ()) > (version_tuple(uv_version_of(uv) or "") or ()) else uv


def install_newer_shared_uv(settings: Settings, current_uv: object) -> Optional[Path]:
    """The shared uv when it is newer than current_uv, otherwise None; never fails the launch."""
    if not shared_uv_allowed(settings):
        return None
    current = uv_version_of(current_uv)
    step(f"uv {current} cannot provide this Python. Getting the newest uv; the uv on PATH stays as it is.")
    try:
        new = install_uv(str(setting(settings, "uv_version", "")), SHARED_UV_DIR)
    except BootstrapError as error:
        step(f"Could not get a newer uv: {error}")
        return None
    return new if (version_tuple(uv_version_of(new) or "") or ()) > (version_tuple(current or "") or ()) else None


# ---------------------------------------------------------------- Python


def set_uv_environment(settings: Settings, source: object) -> None:
    """Mirrors uv_environment in scripts/env/uv.py."""
    for name in OWN_UV_VARIABLES:
        os.environ.pop(name, None)
    visible = "1" if setting(settings, "uv_user_python_visible_globally", True) else "0"
    if source == "uv_user":
        os.environ.update(UV_MANAGED_PYTHON="1", UV_PYTHON_INSTALL_BIN=visible, UV_PYTHON_INSTALL_REGISTRY=visible)
    elif source == "local":
        os.environ.update(
            UV_PYTHON_INSTALL_DIR=str(LOCAL_PYTHONS_DIR),
            UV_MANAGED_PYTHON="1",
            UV_PYTHON_INSTALL_BIN="0",
            UV_PYTHON_INSTALL_REGISTRY="0",
        )
    else:  # "system": only what is already installed on this PC
        os.environ["UV_PYTHON_PREFERENCE"] = "only-system"
    if setting(settings, "uv_cache", "global") == "local":
        os.environ["UV_CACHE_DIR"] = str(LOCAL_CACHE_DIR)
    if setting(settings, "use_system_certificates", False):
        os.environ["UV_SYSTEM_CERTS"] = "1"
    os.environ["UV_PYTHON_DOWNLOADS"] = "never" if source == "system" else "automatic"


def remove_broken_python_links() -> None:
    """uv links minor versions to the newest patch with junctions; after a move they point nowhere."""
    if not LOCAL_PYTHONS_DIR.is_dir():
        return
    for entry in LOCAL_PYTHONS_DIR.iterdir():
        try:
            is_link = bool(entry.lstat().st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
        except OSError:
            continue
        if is_link and not entry.exists():
            entry.rmdir()  # removes only the link


def downloadable_pythons(uv: object, all_versions: bool = False) -> List[Dict[str, str]]:
    arguments = ["python", "list", "--only-downloads", "--output-format", "json"]
    code, lines = run_captured(uv, arguments + (["--all-versions"] if all_versions else []))
    if code:
        return []
    try:
        entries = json.loads("\n".join(lines))
    except ValueError:
        return []
    return [e for e in entries if e.get("implementation") == "cpython" and e.get("variant") == "default"]


def newest_stable_python(uv: object) -> str:
    stable = [
        version_tuple(e["version"]) or ()
        for e in downloadable_pythons(uv)
        if re.fullmatch(r"\d+\.\d+\.\d+", e.get("version", ""))
    ]
    if not stable:
        raise BootstrapError(
            'uv could not list downloadable Python versions (no internet?). Set python_version, e.g. "3.14".'
        )
    newest = max(stable)
    return f"{newest[0]}.{newest[1]}"


def available_summary(uv: object) -> str:
    versions = sorted({e["version"] for e in downloadable_pythons(uv, True)}, key=lambda v: version_tuple(v) or ())
    if not versions:
        return "uv could not list the downloadable versions (no internet?)."
    return f"uv offers {versions[0]} to {versions[-1]} for this PC."


def find_python(uv: object, request: str) -> Optional[str]:
    code, lines = run_captured(uv, ["python", "find", "--no-project", *([request] if request else [])])
    return lines[-1].strip() if code == 0 and lines else None


def project_python_request(settings: Settings) -> str:
    """The project's current Python runs the launcher; the launcher itself offers a migration if the setting differs."""
    try:
        for line in VERSION_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    except OSError:
        pass
    return str(setting(settings, "python_version", "3.14"))


def resolve_python(settings: Settings, uv: Path) -> Tuple[str, Path]:
    """(the launcher's Python, the uv to use from now on)."""
    source = setting(settings, "python_source", "uv_user")
    assert_choice("python_source", source, ("local", "uv_user", "system"))
    set_uv_environment(settings, source)
    remove_broken_python_links()
    request = project_python_request(settings)
    # Outside the project: uv would otherwise discover pyapp/generated/.venv as "the" Python.
    previous_folder = Path.cwd()
    os.chdir(tempfile.gettempdir())
    try:
        if not request:
            request = newest_stable_python(uv)
            step(f"python_version is empty: using the newest stable Python, {request}.")
        python = find_python(uv, request)
        if not python and source == "system":
            raise BootstrapError(
                f"python_source is \"system\", but no Python '{request}' is installed on this PC. Install one, or "
                "change python_version in developer_settings.py."
            )
        if not python:
            step(f"Installing Python {request} with uv...")
            code = run_live(uv, ["python", "install", request])
            if code:
                newer = install_newer_shared_uv(settings, uv)
                if newer is not None:
                    uv = newer
                    code = run_live(uv, ["python", "install", request])
            if code:
                raise BootstrapError(
                    f"uv could not install Python '{request}'. {available_summary(uv)} The launcher needs Python 3.8 or "
                    "newer. Check python_version in developer_settings.py. On a company network, a firewall may block "
                    "the download from github.com; a folder made with the make_portable dev tool needs no download."
                )
            python = find_python(uv, request)
            if not python:
                raise BootstrapError(f"Python {request} was installed but uv cannot find it.")
    finally:
        os.chdir(previous_folder)
    code, lines = run_captured(python, ["-I", "-S", "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"])
    version = version_tuple(lines[0]) if code == 0 and lines else None
    if version is None:
        raise BootstrapError(_start_problems[-1] if _start_problems else f"The Python at '{python}' does not start.")
    if version[:2] < MINIMUM_PYTHON:
        raise BootstrapError(
            f"Python {lines[0]} at '{python}' is older than 3.8, which the launcher needs. Choose python_version 3.8 or newer in developer_settings.py."
        )
    return python, uv


# ---------------------------------------------------------------- project folder


def move_project_files_into_generated() -> None:
    """Creates code/pyapp/generated and moves files from where older versions kept them."""
    old_env = BACKEND_DIR / "env"
    try:
        if old_env.exists() and not GENERATED_DIR.exists():
            old_env.rename(GENERATED_DIR)
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        old_environment = BACKEND_DIR / "environment"
        names = (
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            ".venv",
            "uv",
            "pythons",
            "uv-cache",
            "shortcuts_created_by_setup.json",
        )
        for folder in (old_environment, BACKEND_DIR):
            for name in names:
                if (folder / name).exists() and not (GENERATED_DIR / name).exists():
                    (folder / name).rename(GENERATED_DIR / name)
        if old_environment.is_dir() and not any(old_environment.iterdir()):
            old_environment.rmdir()
    except OSError as error:
        raise BootstrapError(
            f"Could not move the project's files into {GENERATED_DIR}. Close the running app and programs using it, then start again. ({error})"
        ) from error


def cache_text(uv: object, python: str, stamp: str) -> str:
    """ensure_runtime.bat skips its code page switch for caches whose first line is "rem ascii"."""
    ascii_only = all(" " <= character <= "~" for character in f"{uv}{python}{stamp}")
    lines = [
        "rem ascii" if ascii_only else "rem utf-8",
        "rem Generated by resolve_runtime.py. Delete this file to force a new uv/Python lookup.",
        'set "PYAPP_UV=' + str(uv).replace("%", "%%") + '"',
        'set "PYAPP_PYTHON=' + python.replace("%", "%%") + '"',
        'set "PYAPP_CACHED_STAMP=' + stamp.replace("%", "%%") + '"',
    ]
    return "\r\n".join(lines) + "\r\n"


@contextlib.contextmanager
def bootstrap_lock() -> Iterator[None]:
    """Only one launcher at a time prepares uv and Python; Windows releases the lock after a crash."""
    TEMPORARY_DIR.mkdir(parents=True, exist_ok=True)
    with (TEMPORARY_DIR / "bootstrap.lock").open("a+b") as stream:
        deadline = time.monotonic() + 600
        while True:
            try:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError as error:
                if time.monotonic() > deadline:
                    raise BootstrapError("Another launcher is still preparing uv/Python.") from error
                time.sleep(0.1)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def resolve(stamp: str) -> None:
    settings = read_settings(SETTINGS_PATH.read_text(encoding="utf-8"))
    move_project_files_into_generated()
    uv = select_newest_uv(settings, resolve_uv(settings))
    python, uv = resolve_python(settings, uv)
    CACHE_PATH.write_bytes(cache_text(uv, python, stamp).encode("utf-8"))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Find or install uv and the launcher's Python.")
    parser.add_argument("--stamp", default="")
    parser.add_argument(
        "--install-newer-than", default="", help="used by the launcher when changing the project's Python"
    )
    arguments = parser.parse_args(argv)
    _enable_colors()
    try:
        with bootstrap_lock():
            if arguments.install_newer_than:
                settings = read_settings(SETTINGS_PATH.read_text(encoding="utf-8"))
                return 0 if install_newer_shared_uv(settings, arguments.install_newer_than) else 1
            resolve(arguments.stamp)
        shutil.rmtree(BOOTSTRAP_UV_DIR, ignore_errors=True)
        return 0
    except BootstrapError as error:
        show_error(str(error))
        return 1
    except Exception as error:
        traceback.print_exc()
        show_error(f"Preparing uv and Python failed: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
