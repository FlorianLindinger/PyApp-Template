"""Windows shortcuts: create .lnk files, their targets and taskbar identity, and remove stale ones.

Used by actions/setup.py (Setup), start_program.py (outdated-target hint) and the dev tools.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import time
import unicodedata
import uuid
from ctypes import wintypes
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Iterable

from backend.DONT_CHANGE.backend_settings import (
    CRASH_LOG_ICON_PATH,
    CREATED_SHORTCUTS_LIST_PATH,
    DEV_SETTINGS_PATH,
    ENTRY_BATCHES_DIR,
    ICON_PATH,
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
from backend.DONT_CHANGE.scripts import com_tools as com
from backend.DONT_CHANGE.scripts.console_tools import print_warn
from backend.DONT_CHANGE.scripts.file_tools import (
    make_abs_path_relative_to_file,
    sanitize_filename,
)


def generate_shortcut(
    shortcut_name: str,
    icon_path: str | os.PathLike[str] | None,
    launcher_path: str | os.PathLike[str],
    args: str | os.PathLike[str] | None = "",
    app_id: str | None = None,
    description: str | os.PathLike[str] | None = "",
    start_minimized: bool = False,
    classic_terminal: bool = True,
    wdir: str | os.PathLike[str] = "",
    output_dir: str = SHORTCUT_OUTPUT_DIR,
) -> str:
    """Create one configured Windows ``.lnk`` shortcut.

    The function builds the launcher command, applies the icon, description,
    working directory, window mode, and optional AppUserModelID, then saves the
    shortcut after safely replacing an existing file.

    This is more complicated than ordinary file creation because ``.lnk`` is a
    Windows COM format, not a text format. Python's standard library has no
    shortcut API, and the AppUserModelID is unavailable through the simpler
    WScript shortcut interface. The private ctypes structures below therefore
    expose the required Windows COM interfaces directly. This keeps shortcut
    generation dependency-free instead of requiring pywin32 or comtypes.
    """
    if start_minimized and (not classic_terminal):
        raise ValueError("A minimized shortcut requires classic_terminal=True")
    _hresult = com.HRESULT
    _method = com.METHOD
    _unused_method = com.UNUSED_METHOD
    _Guid = com.GUID
    _guid = com.guid
    _check_hresult = com.check_hresult

    class _ShellLink(ctypes.Structure):
        """Declare the native shell-link interface before assigning its method table."""

    _shell_link_pointer = ctypes.POINTER(_ShellLink)

    class _ShellLinkVTable(ctypes.Structure):
        """Describe the COM shell-link methods used to configure generated shortcuts."""

        _fields_ = (
            (
                "QueryInterface",
                _method(
                    _hresult,
                    _shell_link_pointer,
                    ctypes.POINTER(_Guid),
                    ctypes.POINTER(ctypes.c_void_p),
                ),
            ),
            ("AddRef", _unused_method),
            ("Release", _method(ctypes.c_ulong, _shell_link_pointer)),
            ("GetPath", _unused_method),
            ("GetIDList", _unused_method),
            ("SetIDList", _unused_method),
            ("GetDescription", _unused_method),
            (
                "SetDescription",
                _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p),
            ),
            ("GetWorkingDirectory", _unused_method),
            (
                "SetWorkingDirectory",
                _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p),
            ),
            ("GetArguments", _unused_method),
            ("SetArguments", _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p)),
            ("GetHotkey", _unused_method),
            ("SetHotkey", _unused_method),
            ("GetShowCmd", _unused_method),
            ("SetShowCmd", _method(_hresult, _shell_link_pointer, ctypes.c_int)),
            ("GetIconLocation", _unused_method),
            (
                "SetIconLocation",
                _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p, ctypes.c_int),
            ),
            ("SetRelativePath", _unused_method),
            ("Resolve", _unused_method),
            ("SetPath", _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p)),
        )

    _ShellLink._fields_ = [("vtable", ctypes.POINTER(_ShellLinkVTable))]

    class _PersistFile(ctypes.Structure):
        """Declare the COM persistence interface used to save shortcut files."""

    _persist_file_pointer = ctypes.POINTER(_PersistFile)

    class _PersistFileVTable(ctypes.Structure):
        """Describe the COM persistence methods used to write shortcut files."""

        _fields_ = (
            (
                "QueryInterface",
                _method(
                    _hresult,
                    _persist_file_pointer,
                    ctypes.POINTER(_Guid),
                    ctypes.POINTER(ctypes.c_void_p),
                ),
            ),
            ("AddRef", _unused_method),
            ("Release", _method(ctypes.c_ulong, _persist_file_pointer)),
            ("GetClassID", _unused_method),
            ("IsDirty", _unused_method),
            ("Load", _unused_method),
            (
                "Save",
                _method(_hresult, _persist_file_pointer, ctypes.c_wchar_p, wintypes.BOOL),
            ),
            ("SaveCompleted", _unused_method),
            ("GetCurFile", _unused_method),
        )

    _PersistFile._fields_ = [("vtable", ctypes.POINTER(_PersistFileVTable))]

    def _move_into_place(temporary_path: str, output_path: str) -> None:
        """Replace the shortcut in one step; retry for five seconds while Explorer holds it open."""
        timeout = 5.0
        deadline = time.monotonic() + timeout
        while True:
            try:
                Path(temporary_path).replace(output_path)
                return
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f'Failed to replace the shortcut within {timeout:.1f} seconds: "{output_path}". Windows error: {error}'
                    ) from error
                time.sleep(0.1)

    def _quote(value: str | os.PathLike[str]) -> str:
        """Quote one filesystem argument for the command string stored in a shortcut."""
        return '"' + os.fspath(value).replace('"', '""') + '"'

    _shell_link_class_id = _guid("00021401-0000-0000-C000-000000000046")
    _shell_link_interface_id = _guid("000214F9-0000-0000-C000-000000000046")
    _persist_file_interface_id = _guid("0000010B-0000-0000-C000-000000000046")
    output_path = os.path.normpath(str((Path(output_dir) / shortcut_filename(os.fspath(shortcut_name))).absolute()))
    launcher_args = [_quote(launcher_path)] if classic_terminal else ["/d", "/c", "call", _quote(launcher_path)]
    if args not in ("", None):
        launcher_args.append(_quote(args))
    icon_path = os.path.normpath(str(Path(os.fspath(icon_path)).absolute())) if icon_path else None
    if icon_path and (not Path(icon_path).exists()):
        print_warn(f'icon not existing at "{icon_path}"')
        icon_path = None
    wdir = os.path.normpath(str(Path(wdir).absolute())) if wdir else SHORTCUT_OUTPUT_DIR
    description = "" if description is None else os.fspath(description)
    (Path(output_path).parent).mkdir(parents=True, exist_ok=True)
    # Saved under a temporary name first: an existing shortcut is only replaced by a complete one.
    temporary_path = str((Path(output_path).parent) / (f"~{uuid.uuid4().hex[:8]}.tmp.lnk"))
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(_Guid),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_Guid),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    ole32.CoCreateInstance.restype = _hresult
    should_uninitialize = com.co_initialize()
    try:
        shell_link_pointer = ctypes.c_void_p()
        result = ole32.CoCreateInstance(
            ctypes.byref(_shell_link_class_id),
            None,
            1,
            ctypes.byref(_shell_link_interface_id),
            ctypes.byref(shell_link_pointer),
        )
        _check_hresult(result, "CoCreateInstance(CLSID_ShellLink)")
        shell_link = ctypes.cast(shell_link_pointer, _shell_link_pointer)
        try:
            interface = shell_link.contents.vtable.contents
            target = "conhost.exe" if classic_terminal else "cmd.exe"
            _check_hresult(interface.SetPath(shell_link, target), f'SetPath("{target}")')
            _check_hresult(
                interface.SetArguments(shell_link, " ".join(launcher_args)),
                "SetArguments",
            )
            _check_hresult(interface.SetWorkingDirectory(shell_link, wdir), "SetWorkingDirectory")
            _check_hresult(interface.SetDescription(shell_link, description), "SetDescription")
            _check_hresult(
                interface.SetShowCmd(shell_link, 7 if start_minimized else 1),
                "SetShowCmd",
            )
            if icon_path:
                _check_hresult(
                    interface.SetIconLocation(shell_link, icon_path, 0),
                    f'SetIconLocation("{icon_path}")',
                )
            if app_id is not None:
                property_store_pointer = ctypes.c_void_p()
                result = interface.QueryInterface(
                    shell_link,
                    ctypes.byref(com.IID_PROPERTY_STORE),
                    ctypes.byref(property_store_pointer),
                )
                _check_hresult(result, "QueryInterface(IPropertyStore)")
                com.set_app_user_model_id(ctypes.cast(property_store_pointer, com.PropertyStorePointer), app_id)
            persist_file_pointer = ctypes.c_void_p()
            result = interface.QueryInterface(
                shell_link,
                ctypes.byref(_persist_file_interface_id),
                ctypes.byref(persist_file_pointer),
            )
            _check_hresult(result, "QueryInterface(IPersistFile)")
            persist_file = ctypes.cast(persist_file_pointer, _persist_file_pointer)
            try:
                result = persist_file.contents.vtable.contents.Save(persist_file, temporary_path, True)
                _check_hresult(result, f'Save shortcut "{output_path}"')
            finally:
                persist_file.contents.vtable.contents.Release(persist_file)
        finally:
            shell_link.contents.vtable.contents.Release(shell_link)
        _move_into_place(temporary_path, output_path)
    finally:
        com.co_uninitialize(should_uninitialize)
        if Path(temporary_path).exists():
            Path(temporary_path).unlink()
    return output_path


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


def _read_created_shortcuts_file() -> dict[str, Any]:
    try:
        with Path(CREATED_SHORTCUTS_LIST_PATH).open(encoding="utf-8") as stream:
            data = json.load(stream)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def read_created_shortcuts() -> list[str]:
    return list(_read_created_shortcuts_file().get("shortcuts", []))


def write_created_shortcuts(paths: list[str], targets: dict[str, str] | None = None) -> None:
    """Record the created .lnk files (to remove stale ones later) and the targets they open."""
    with Path(CREATED_SHORTCUTS_LIST_PATH).open("w", encoding="utf-8") as stream:
        json.dump({"version": 2, "shortcuts": sorted(set(paths)), "targets": targets or {}}, stream, indent=2)


def remove_shortcuts(paths: Iterable[str], keep: Iterable[str] = ()) -> list[str]:
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


def shortcut_targets(s: ModuleType | SimpleNamespace) -> dict[str, str]:
    """Folder/file each "open" shortcut passes to its B\\*.bat, which then opens it without Python.

    "" means the target can only be resolved at click time (a path relative to the start folder
    or with date codes in the folder part); the B\\*.bat then runs the Python action instead.
    """
    from backend.DONT_CHANGE.scripts.config import main_script_path
    from backend.DONT_CHANGE.scripts.launcher_ui import get_log_folder_path

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
    s: ModuleType | SimpleNamespace, app_id: str, targets: dict[str, str]
) -> list[tuple[str, str, str, str, str, str | None, str]]:
    """(kind, name, icon, launcher, args, app_id, description) for every enabled shortcut."""
    name = s.program_name
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
            targets["logs"],
            None,
            f"Open the {name} log folder",
        ),
        (
            "crash_logs",
            s.open_crash_log_folder_shortcut_name,
            CRASH_LOG_ICON_PATH,
            LAUNCHER_OPEN_CRASH_LOG_DIR,
            targets["crash_logs"],
            None,
            f"Open the {name} crash log folder",
        ),
        (
            "open_code",
            s.open_code_shortcut_name,
            OPEN_CODE_ICON_PATH,
            LAUNCHER_OPEN_CODE,
            targets["open_code"],
            None,
            f"Open the {name} main script",
        ),
    ]
    if s.user_settings_path:
        definitions.append(
            (
                "settings",
                s.open_settings_shortcut_name,
                SETTINGS_ICON_PATH,
                LAUNCHER_OPEN_SETTINGS,
                targets["settings"],
                None,
                f"Open the {name} settings file",
            )
        )
    return [
        (kind, label, icon, launcher, arguments, identity, description)
        for kind, label, icon, launcher, arguments, identity, description in definitions
        if label
    ]


def outdated_shortcut_targets(s: ModuleType | SimpleNamespace) -> list[str]:
    """Kinds of "open" shortcuts whose recorded target no longer matches the settings (run Setup)."""
    recorded = _read_created_shortcuts_file().get("targets")
    if not isinstance(recorded, dict):
        return []
    current = shortcut_targets(s)
    return [
        kind
        for kind, path in recorded.items()
        if kind in current and os.path.normcase(path) != os.path.normcase(current[kind])
    ]
