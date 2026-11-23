"""Windows shortcuts: create .lnk files, their targets and taskbar identity, and remove stale ones.

Used by scripts/actions/setup.py (Setup), start_program.py (outdated-target hint) and the dev tools.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple, Union

from pyapp.DONT_CHANGE.pyapp_settings import (
    BROWSER_APP_ID_SUFFIX,
    CRASH_LOG_ICON_PATH,
    CREATED_SHORTCUTS_LIST_PATH,
    DEV_SETTINGS_PATH,
    ENTRY_BATCHES_DIR,
    ICON_PATH,
    LAUNCHER_BROWSER_TERMINAL,
    LAUNCHER_NO_TERMINAL,
    LAUNCHER_OPEN_CODE,
    LAUNCHER_OPEN_CRASH_LOG_DIR,
    LAUNCHER_OPEN_LOG_DIR,
    LAUNCHER_OPEN_SETTINGS,
    LAUNCHER_STOP,
    LAUNCHER_TERMINAL,
    LOG_ICON_PATH,
    NO_TERMINAL_APP_ID_SUFFIX,
    OPEN_CODE_ICON_PATH,
    SETTINGS_ICON_PATH,
    SHORTCUT_OUTPUT_DIR,
    SHORTCUT_SIGNATURE,
    STOP_ICON_PATH,
)
from pyapp.DONT_CHANGE.scripts.console_tools import print_warn
from pyapp.DONT_CHANGE.scripts.standalone.file_tools import (
    make_abs_path_relative_to_file,
    sanitize_filename,
)
from pyapp.DONT_CHANGE.scripts.standalone.shortcut_files import create_shortcut


class TextPathLike(Protocol):
    """A filesystem path returning text, including os.PathLike implementations on 3.8."""

    def __fspath__(self) -> str: ...


def generate_shortcut(
    shortcut_name: str,
    icon_path: Optional[Union[str, TextPathLike]],
    launcher_path: Union[str, TextPathLike],
    args: Optional[Union[str, TextPathLike]] = "",
    app_id: Optional[str] = None,
    description: Optional[Union[str, TextPathLike]] = "",
    start_minimized: bool = False,
    wdir: Union[str, TextPathLike] = "",
    output_dir: str = SHORTCUT_OUTPUT_DIR,
) -> str:
    """Create one of the launcher's shortcuts: conhost.exe runs ``launcher_path`` (a batch file).

    conhost opens the classic console for the batch file, which can then start minimized.
    Without an explicit wdir, "Start in" is empty and Windows chooses the starting folder.
    The .lnk itself is written by standalone/shortcut_files.py.
    """

    def _quote(value: Union[str, TextPathLike]) -> str:
        """Quote one filesystem argument for the command string stored in a shortcut."""
        return '"' + os.fspath(value).replace('"', '""') + '"'

    output_path = str(Path(output_dir) / shortcut_filename(os.fspath(shortcut_name)))
    launcher_args = [_quote(launcher_path)]
    if args not in ("", None):
        launcher_args.append(_quote(args))
    icon = os.path.normpath(str(Path(os.fspath(icon_path)).absolute())) if icon_path else None
    if icon and not Path(icon).exists():
        print_warn(f'Icon not found at "{icon}"')
        icon = None
    return create_shortcut(
        output_path,
        "conhost.exe",
        " ".join(launcher_args),
        icon_path=icon,
        working_dir=os.fspath(wdir) if wdir else "",
        description="" if description is None else os.fspath(description),
        show_minimized=start_minimized,
        app_id=app_id,
    )


def project_app_id(program_name: str, project_dir: str = SHORTCUT_OUTPUT_DIR) -> str:
    """Taskbar identity (AppUserModelID) of this copy of the project.

    The readable program name plus a hash of name and project folder: copies of the project in
    other folders, and other apps that kept the template's name, get their own taskbar group
    and pinned shortcut. After moving the folder, Setup creates shortcuts with the new identity
    (shortcuts pinned to the taskbar before must be pinned again; their old path is gone anyway).
    """
    name = unicodedata.normalize("NFKD", program_name).encode("ascii", "ignore").decode("ascii").lower()
    name = re.sub("[\\s_.]+", "-", name)
    name = re.sub("[^a-z0-9-]", "", name)
    name = re.sub("-+", "-", name).strip("-")[:40] or "pyapp"
    key = program_name + "|" + os.path.normcase(os.path.normpath(str(Path(project_dir).absolute())))
    return name + "." + hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]


def shortcut_filename(name: str) -> str:
    """Reserve the .lnk suffix and keep truncated names distinct with a stable digest."""
    safe = sanitize_filename(name)
    if len(safe.encode("utf-16-le")) // 2 > 251:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        safe = sanitize_filename(name, max_length=242) + "-" + digest
    return safe + ".lnk"


def special_folder(csidl: int) -> str:
    """Return a Windows shell folder (handles OneDrive-redirected Desktops)."""
    buffer = ctypes.create_unicode_buffer(32768)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
    if result != 0 or not buffer.value:
        raise OSError(f"Could not locate the Windows shell folder {csidl:#x} (HRESULT {result & 0xFFFFFFFF:#010x}).")
    return buffer.value


CSIDL_PROGRAMS = 0x02  # Start Menu\Programs of the current user
CSIDL_STARTUP = 0x07  # This user's Startup folder, not the machine-wide Startup folder.
CSIDL_DESKTOPDIRECTORY = 0x10


def is_generated_shortcut(path: str) -> bool:
    """True for .lnk files created by Setup of THIS project, or of a project folder that no longer exists.

    Shortcuts of another existing copy of the template (e.g. a copied project with the same
    shortcut list) are never deleted.
    """
    if not path.lower().endswith(".lnk") or not Path(path).is_file():
        return False
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(65536)
    except OSError:
        return False
    text = data.decode("utf-16-le", errors="ignore") + data[1:].decode("utf-16-le", errors="ignore")
    targets = re.findall(r'"([^"]*' + re.escape(SHORTCUT_SIGNATURE) + r'[A-Za-z]\.bat)"', text, flags=re.IGNORECASE)
    for target in targets:
        if (
            os.path.normcase(str(Path(target).parent)) == os.path.normcase(ENTRY_BATCHES_DIR)
            or not Path(target).exists()
        ):
            return True
    return False


def _read_created_shortcuts_file() -> Dict[str, Any]:
    try:
        with Path(CREATED_SHORTCUTS_LIST_PATH).open(encoding="utf-8") as stream:
            data = json.load(stream)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def read_created_shortcuts() -> List[str]:
    return list(_read_created_shortcuts_file().get("shortcuts", []))


def create_windows_startup_shortcut(s: Union[ModuleType, SimpleNamespace], app_id: str) -> Optional[str]:
    """Create the opt-in sign-in shortcut; Setup records it with its other owned shortcuts.

    A project-specific suffix keeps copies with the same display name from overwriting each
    other. The existing shortcut record removes stale names/locations or a disabled entry.
    """
    if not getattr(s, "start_on_windows_start", False):
        return None
    launchers = {
        "terminal": (LAUNCHER_TERMINAL, app_id),
        "no_terminal": (LAUNCHER_NO_TERMINAL, app_id + NO_TERMINAL_APP_ID_SUFFIX),
        "browser": (LAUNCHER_BROWSER_TERMINAL, app_id + BROWSER_APP_ID_SUFFIX),
    }
    launcher, identity = launchers[s.windows_startup_launch_mode]
    name = f"{s.program_name} ({app_id.rsplit('.', 1)[-1]})"
    folder = special_folder(CSIDL_STARTUP)
    destination = Path(folder) / shortcut_filename(name)
    if destination.exists() and not is_generated_shortcut(str(destination)):
        raise FileExistsError(f'Windows Startup shortcut would replace an unrelated file: "{destination}"')
    return generate_shortcut(
        name,
        ICON_PATH,
        launcher,
        args=app_id,
        app_id=identity,
        output_dir=folder,
        description=f"Start {s.program_name} when signing in to Windows",
        start_minimized=True,
    )


def read_start_link() -> str:
    """The URL scheme of the browser terminal's start link that Setup registered ("" for none)."""
    link = _read_created_shortcuts_file().get("start_link", "")
    return link if isinstance(link, str) else ""


def write_created_shortcuts(paths: List[str], start_link: str = "") -> None:
    """Record the created .lnk files (to remove stale ones later) and the browser terminal's start link."""
    record = {"version": 2, "shortcuts": sorted(set(paths)), "start_link": start_link}
    with Path(CREATED_SHORTCUTS_LIST_PATH).open("w", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)


def leftover_shortcuts(paths: Iterable[str], removed: Iterable[str]) -> List[str]:
    """The recorded shortcuts that remove_shortcuts could not delete and that are still Setup's own."""
    gone = set(removed)
    return [path for path in paths if path not in gone and is_generated_shortcut(path)]


def remove_shortcuts(paths: Iterable[str], keep: Iterable[str] = ()) -> List[str]:
    """Delete generated shortcuts that are no longer wanted; returns the removed paths."""
    keep_keys = {os.path.normcase(os.path.normpath(str(Path(p).absolute()))) for p in keep}
    removed = []
    for path in paths:
        if os.path.normcase(os.path.normpath(str(Path(path).absolute()))) in keep_keys:
            continue
        if is_generated_shortcut(path):
            try:
                Path(path).unlink()
                removed.append(path)
            except OSError as error:
                print_warn(f'Could not remove the old shortcut "{path}": {error}')
        folder = str(Path(path).parent)
        try:
            # Remove our now-empty Start Menu folder (never the Start Menu or Desktop itself).
            if (
                folder
                not in (special_folder(CSIDL_PROGRAMS), special_folder(CSIDL_DESKTOPDIRECTORY), SHORTCUT_OUTPUT_DIR)
                and Path(folder).is_dir()
                and not [entry.name for entry in Path(folder).iterdir()]
            ):
                Path(folder).rmdir()
        except OSError:
            pass
    return removed


def shortcut_targets(s: Union[ModuleType, SimpleNamespace]) -> Dict[str, str]:
    """The file or folder each "open" shortcut opens with the current settings (for Setup and the browser page).

    The shortcuts themselves carry no path: their B\\*.bat resolves it from the settings on every
    click. "" means the folder can only be resolved at click time (a path relative to the start
    folder, or with date codes in its folder part) or there is no settings file.
    """
    from pyapp.DONT_CHANGE.scripts.config import main_script_path
    from pyapp.DONT_CHANGE.scripts.launcher_ui import get_log_folder_path

    targets = {"open_code": main_script_path(s), "settings": ""}
    for kind, path, relative in (
        ("logs", s.log_path, s.log_path_is_relative_to_start_folder_if_relative),
        ("crash_logs", s.crash_log_path, s.crash_log_path_is_relative_to_start_folder_if_relative),
    ):
        fixed_folder = path and not relative and "%" not in str(Path(path).parent)
        targets[kind] = (get_log_folder_path(path, False) or "") if fixed_folder else ""
    if s.user_settings_path:
        targets["settings"] = make_abs_path_relative_to_file(s.user_settings_path, DEV_SETTINGS_PATH)
    return targets


def shortcut_definitions(
    s: Union[ModuleType, SimpleNamespace], app_id: str
) -> List[Tuple[str, str, str, str, str, Optional[str], str]]:
    """(kind, name, icon, launcher, args, app_id, description) for every enabled shortcut.

    In this order, which Setup also creates and lists them in: the ways to start the app, then
    settings, stop, logs, crash logs and the code.
    """
    name = s.program_name
    # Without a settings file (user_settings_path empty) there is no settings shortcut.
    settings_name = s.open_settings_shortcut_name if s.user_settings_path else ""
    definitions = [
        ("terminal", s.terminal_shortcut_name, ICON_PATH, LAUNCHER_TERMINAL, app_id, app_id, f"Start {name}"),
        (
            "no_terminal",
            s.no_terminal_shortcut_name,
            ICON_PATH,
            LAUNCHER_NO_TERMINAL,
            app_id,
            app_id + NO_TERMINAL_APP_ID_SUFFIX,
            f"Start {name} without opening a terminal window",
        ),
        (
            "browser_terminal",
            s.browser_terminal_shortcut_name,
            ICON_PATH,  # the same app, so the same icon as the terminal shortcut
            LAUNCHER_BROWSER_TERMINAL,
            app_id,
            app_id + BROWSER_APP_ID_SUFFIX,
            f"Start {name} in a terminal in the browser",
        ),
        (
            "settings",
            settings_name,
            SETTINGS_ICON_PATH,
            LAUNCHER_OPEN_SETTINGS,
            "",
            None,
            f"Open the {name} settings file",
        ),
        (
            "stop",
            s.stop_running_shortcut_name,
            STOP_ICON_PATH,
            LAUNCHER_STOP,
            "",
            None,
            f"Stop running {name} processes",
        ),
        (
            "logs",
            s.open_log_folder_shortcut_name,
            LOG_ICON_PATH,
            LAUNCHER_OPEN_LOG_DIR,
            "",
            None,
            f"Open the {name} log folder",
        ),
        (
            "crash_logs",
            s.open_crash_log_folder_shortcut_name,
            CRASH_LOG_ICON_PATH,
            LAUNCHER_OPEN_CRASH_LOG_DIR,
            "",
            None,
            f"Open the {name} crash log folder",
        ),
        (
            "open_code",
            s.open_code_shortcut_name,
            OPEN_CODE_ICON_PATH,
            LAUNCHER_OPEN_CODE,
            "",
            None,
            f"Open the {name} main script",
        ),
    ]
    return [
        (kind, label, icon, launcher, arguments, identity, description)
        for kind, label, icon, launcher, arguments, identity, description in definitions
        if label
    ]
