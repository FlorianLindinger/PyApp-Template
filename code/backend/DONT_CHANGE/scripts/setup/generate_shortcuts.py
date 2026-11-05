"""Generate Windows shortcuts (project folder, Start Menu, Desktop) and remove stale ones."""

from __future__ import annotations

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

import ctypes
import hashlib
import json
import os
import re
import time
import unicodedata
import uuid
from ctypes import wintypes

from backend.DONT_CHANGE.scripts.config import settings, validate
from backend.DONT_CHANGE.scripts.filesystem_tools import (
    make_abs_path_relative_to_file,
    sanitize_filename,
)
from backend.DONT_CHANGE.backend_settings import (
    CRASH_LOG_ICON_PATH,
    DEV_SETTINGS_PATH,
    ENTRY_BATCHES_DIR,
    ICON_PATH,
    LAUNCHER_NO_TERMINAL,
    LAUNCHER_OPEN_CRASH_LOG_DIR,
    LAUNCHER_OPEN_LOG_DIR,
    LAUNCHER_OPEN_MAIN_PY,
    LAUNCHER_OPEN_SETTINGS,
    LAUNCHER_STOP,
    LAUNCHER_TERMINAL,
    LOG_ICON_PATH,
    NO_TERMINAL_APP_ID_SUFFIX,
    OPEN_MAIN_PY_ICON_PATH,
    SETTINGS_ICON_PATH,
    CREATED_SHORTCUTS_LIST_PATH,
    SHORTCUT_OUTPUT_DIR,
    SHORTCUT_SIGNATURE,
    STOP_ICON_PATH,
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
    _hresult = ctypes.c_long
    _method = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
    _unused_method = ctypes.c_void_p

    class _Guid(ctypes.Structure):
        """Represent a native Windows GUID for shortcut COM calls."""

        _fields_ = (
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        )

    class _PropertyKey(ctypes.Structure):
        """Identify a Windows shortcut property by its format GUID and numeric ID."""

        _fields_ = (("fmtid", _Guid), ("pid", wintypes.DWORD))

    class _PropVariant(ctypes.Structure):
        """Hold a string-valued COM variant for the shortcut's taskbar identity."""

        _fields_ = (
            ("vt", ctypes.c_ushort),
            ("reserved1", ctypes.c_ushort),
            ("reserved2", ctypes.c_ushort),
            ("reserved3", ctypes.c_ushort),
            ("string_value", ctypes.c_wchar_p),
        )

    class _ShellLink(ctypes.Structure):
        """Declare the native shell-link interface before assigning its method table."""

        pass

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

        pass

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
                _method(
                    _hresult, _persist_file_pointer, ctypes.c_wchar_p, wintypes.BOOL
                ),
            ),
            ("SaveCompleted", _unused_method),
            ("GetCurFile", _unused_method),
        )

    _PersistFile._fields_ = [("vtable", ctypes.POINTER(_PersistFileVTable))]

    class _PropertyStore(ctypes.Structure):
        """Declare the COM interface used to store shortcut properties."""

        pass

    _property_store_pointer = ctypes.POINTER(_PropertyStore)

    class _PropertyStoreVTable(ctypes.Structure):
        """Describe the COM property-store methods used to persist the app identity."""

        _fields_ = (
            (
                "QueryInterface",
                _method(
                    _hresult,
                    _property_store_pointer,
                    ctypes.POINTER(_Guid),
                    ctypes.POINTER(ctypes.c_void_p),
                ),
            ),
            ("AddRef", _unused_method),
            ("Release", _method(ctypes.c_ulong, _property_store_pointer)),
            ("GetCount", _unused_method),
            ("GetAt", _unused_method),
            ("GetValue", _unused_method),
            (
                "SetValue",
                _method(
                    _hresult,
                    _property_store_pointer,
                    ctypes.POINTER(_PropertyKey),
                    ctypes.POINTER(_PropVariant),
                ),
            ),
            ("Commit", _method(_hresult, _property_store_pointer)),
        )

    _PropertyStore._fields_ = [("vtable", ctypes.POINTER(_PropertyStoreVTable))]

    def _guid(value: str) -> _Guid:
        """Convert a UUID string to the native GUID structure expected by Windows COM."""
        parsed = uuid.UUID(value)
        return _Guid(
            parsed.time_low,
            parsed.time_mid,
            parsed.time_hi_version,
            (wintypes.BYTE * 8)(*parsed.bytes[8:]),
        )

    def _check_hresult(result: int, action: str) -> None:
        """Raise OSError with the failed COM action and formatted Windows error code."""
        if result >= 0:
            return
        code = result & 4294967295
        try:
            message = ctypes.FormatError(code).strip()
        except Exception:
            message = "unknown error"
        raise OSError(f"{action} failed with HRESULT 0x{code:08X}: {message}")

    def _wait_for_file(output_path: str, should_exist: bool) -> None:
        """Wait for shortcut creation or retry its deletion, reporting failure after five seconds."""
        timeout = 5.0
        deadline = time.monotonic() + timeout
        last_error = None
        while os.path.exists(output_path) != should_exist:
            if not should_exist:
                try:
                    os.remove(output_path)
                except FileNotFoundError:
                    return
                except OSError as error:
                    last_error = error
            if os.path.exists(output_path) == should_exist:
                return
            if time.monotonic() >= deadline:
                action = "create" if should_exist else "delete existing"
                detail = f" Last Windows error: {last_error}" if last_error else ""
                raise RuntimeError(
                    f'Failed to {action} shortcut within {timeout:.1f} seconds: "{output_path}".{detail}'
                )
            time.sleep(0.1)

    def _quote(value: str | os.PathLike[str]) -> str:
        """Quote one filesystem argument for the command string stored in a shortcut."""
        return '"' + os.fspath(value).replace('"', '""') + '"'

    _shell_link_class_id = _guid("00021401-0000-0000-C000-000000000046")
    _shell_link_interface_id = _guid("000214F9-0000-0000-C000-000000000046")
    _persist_file_interface_id = _guid("0000010B-0000-0000-C000-000000000046")
    _property_store_interface_id = _guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
    _app_id_key = _PropertyKey(_guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5)
    output_path = os.path.abspath(
        os.path.join(output_dir, _shortcut_filename(os.fspath(shortcut_name)))
    )
    launcher_args = (
        [_quote(launcher_path)]
        if classic_terminal
        else ["/d", "/c", "call", _quote(launcher_path)]
    )
    if args not in ("", None):
        launcher_args.append(_quote(args))
    icon_path = os.path.abspath(os.fspath(icon_path)) if icon_path else None
    if icon_path and (not os.path.exists(icon_path)):
        print(f'[Warning] icon not existing at "{icon_path}"')
        icon_path = None
    wdir = os.path.abspath(wdir) if wdir else SHORTCUT_OUTPUT_DIR
    description = "" if description is None else os.fspath(description)
    print(f"[Info] Creating: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    _wait_for_file(output_path, should_exist=False)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CoInitialize.argtypes = [ctypes.c_void_p]
    ole32.CoInitialize.restype = _hresult
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(_Guid),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_Guid),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    ole32.CoCreateInstance.restype = _hresult
    result = ole32.CoInitialize(None)
    should_uninitialize = result in (0, 1)
    if result < 0 and result & 4294967295 != 2147549446:
        _check_hresult(result, "CoInitialize")
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
            _check_hresult(
                interface.SetPath(shell_link, target), f'SetPath("{target}")'
            )
            _check_hresult(
                interface.SetArguments(shell_link, " ".join(launcher_args)),
                "SetArguments",
            )
            _check_hresult(
                interface.SetWorkingDirectory(shell_link, wdir), "SetWorkingDirectory"
            )
            _check_hresult(
                interface.SetDescription(shell_link, description), "SetDescription"
            )
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
                    ctypes.byref(_property_store_interface_id),
                    ctypes.byref(property_store_pointer),
                )
                _check_hresult(result, "QueryInterface(IPropertyStore)")
                property_store = ctypes.cast(
                    property_store_pointer, _property_store_pointer
                )
                try:
                    app_id_value = _PropVariant()
                    app_id_value.vt = 31
                    app_id_value.string_value = app_id
                    result = property_store.contents.vtable.contents.SetValue(
                        property_store,
                        ctypes.byref(_app_id_key),
                        ctypes.byref(app_id_value),
                    )
                    _check_hresult(result, "SetValue(System.AppUserModel.ID)")
                    _check_hresult(
                        property_store.contents.vtable.contents.Commit(property_store),
                        "Commit(IPropertyStore)",
                    )
                finally:
                    property_store.contents.vtable.contents.Release(property_store)
            persist_file_pointer = ctypes.c_void_p()
            result = interface.QueryInterface(
                shell_link,
                ctypes.byref(_persist_file_interface_id),
                ctypes.byref(persist_file_pointer),
            )
            _check_hresult(result, "QueryInterface(IPersistFile)")
            persist_file = ctypes.cast(persist_file_pointer, _persist_file_pointer)
            try:
                result = persist_file.contents.vtable.contents.Save(
                    persist_file, output_path, True
                )
                _check_hresult(result, f'Save shortcut "{output_path}"')
            finally:
                persist_file.contents.vtable.contents.Release(persist_file)
        finally:
            shell_link.contents.vtable.contents.Release(shell_link)
    finally:
        if should_uninitialize:
            ole32.CoUninitialize()
    _wait_for_file(output_path, should_exist=True)
    return output_path


def _sanitize_app_id(value: str) -> str:
    """Return a stable compact taskbar identity, including non-Latin and long app names."""
    name = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    name = re.sub("[\\s_]+", "-", name)
    name = re.sub("[^a-z0-9.-]", "", name)
    name = re.sub("-+", "-", name)
    name = re.sub("\\.+", ".", name)
    name = name.strip("-.")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    if not name:
        return "pyapp-" + digest[:9]
    if len(name) > 15:
        return name[:7] + "-" + digest[:7]
    return name


def _shortcut_filename(name: str) -> str:
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
    if not path.lower().endswith(".lnk") or not os.path.isfile(path):
        return False
    try:
        with open(path, "rb") as stream:
            data = stream.read(65536)
    except OSError:
        return False
    text = data.decode("utf-16-le", errors="ignore") + data[1:].decode("utf-16-le", errors="ignore")
    targets = re.findall(r'"([^"]*' + re.escape(SHORTCUT_SIGNATURE) + r'[A-Za-z]\.bat)"', text, flags=re.IGNORECASE)
    for target in targets:
        if os.path.normcase(os.path.dirname(target)) == os.path.normcase(ENTRY_BATCHES_DIR) or not os.path.exists(target):
            return True
    return False


def read_created_shortcuts() -> list:
    try:
        with open(CREATED_SHORTCUTS_LIST_PATH, encoding="utf-8") as stream:
            return list(json.load(stream).get("shortcuts", []))
    except (OSError, ValueError, AttributeError):
        return []


def write_created_shortcuts(paths: list) -> None:
    with open(CREATED_SHORTCUTS_LIST_PATH, "w", encoding="utf-8") as stream:
        json.dump({"version": 1, "shortcuts": sorted(set(paths))}, stream, indent=2)


def remove_shortcuts(paths, keep=()) -> list:
    """Delete generated shortcuts that are no longer wanted; returns the removed paths."""
    keep_keys = {os.path.normcase(os.path.abspath(p)) for p in keep}
    removed = []
    for path in paths:
        if os.path.normcase(os.path.abspath(path)) in keep_keys:
            continue
        if is_generated_shortcut(path):
            try:
                os.remove(path)
                removed.append(path)
            except OSError as error:
                print(f'[Warning] Could not remove the old shortcut "{path}": {error}')
        folder = os.path.dirname(path)
        try:
            # Remove our now-empty Start Menu folder (never the Start Menu or Desktop itself).
            if folder not in (special_folder(CSIDL_PROGRAMS), special_folder(CSIDL_DESKTOPDIRECTORY), SHORTCUT_OUTPUT_DIR) and os.path.isdir(folder) and not os.listdir(folder):
                os.rmdir(folder)
        except OSError:
            pass
    return removed


def shortcut_definitions(s, app_id: str) -> list:
    """(kind, name, icon, launcher, args, app_id, description) for every enabled shortcut."""
    name = s.program_name
    definitions = [
        ("terminal", s.terminal_shortcut_name, ICON_PATH, LAUNCHER_TERMINAL, app_id, app_id, f"Start {name}"),
        ("no_terminal", s.no_terminal_shortcut_name, ICON_PATH, LAUNCHER_NO_TERMINAL, app_id, app_id + NO_TERMINAL_APP_ID_SUFFIX, f"Start {name} without opening a terminal window"),
        ("stop", s.stop_running_shortcut_name, STOP_ICON_PATH, LAUNCHER_STOP, "", None, f"Stop running {name} processes"),
        ("logs", s.open_log_folder_shortcut_name, LOG_ICON_PATH, LAUNCHER_OPEN_LOG_DIR, "", None, f"Open the {name} log folder"),
        ("crash_logs", s.open_crash_log_folder_shortcut_name, CRASH_LOG_ICON_PATH, LAUNCHER_OPEN_CRASH_LOG_DIR, "", None, f"Open the {name} crash log folder"),
        ("main_py", s.open_main_py_shortcut_name, OPEN_MAIN_PY_ICON_PATH, LAUNCHER_OPEN_MAIN_PY, "", None, f"Open the {name} main.py file"),
    ]
    if s.user_settings_path:
        definitions.append(("settings", s.open_settings_shortcut_name, SETTINGS_ICON_PATH, LAUNCHER_OPEN_SETTINGS, "", None, f"Open the {name} settings file"))
    return [d for d in definitions if d[1]]


def main() -> None:
    """Optionally prepare the environment, then create the enabled shortcuts and remove stale ones."""
    s = settings()
    validate(s)
    app_id = _sanitize_app_id(s.program_name)
    definitions = shortcut_definitions(s, app_id)
    filenames = [_shortcut_filename(d[1]).casefold() for d in definitions]
    if len(filenames) != len(set(filenames)):
        raise ValueError("Shortcut names collide after Windows filename sanitization; choose distinct names.")
    if s.install_environment_when_generating_shortcuts:
        from backend.DONT_CHANGE.scripts.uv_env import ensure_environment

        ensure_environment(interactive=True, purpose="setup")
    if s.user_settings_path:
        settings_file = make_abs_path_relative_to_file(s.user_settings_path, DEV_SETTINGS_PATH)
        if not os.path.exists(settings_file):
            print(f'[Warning] The user settings file does not exist: "{settings_file}". Its shortcut will show an error until the file exists.')

    targets = [SHORTCUT_OUTPUT_DIR]
    start_menu = None
    if s.start_menu_shortcuts:
        start_menu = os.path.join(special_folder(CSIDL_PROGRAMS), sanitize_filename(s.program_name))
        targets.append(start_menu)
    print()
    print("=" * 30)
    created = []
    for kind, name, icon, launcher, args, shortcut_app_id, description in definitions:
        folders = list(targets)
        if kind in s.desktop_shortcuts:
            folders.append(special_folder(CSIDL_DESKTOPDIRECTORY))
        for folder in folders:
            created.append(
                generate_shortcut(
                    name,
                    icon,
                    launcher,
                    args=args,
                    app_id=shortcut_app_id,
                    description=description,
                    start_minimized=kind != "stop",  # Stop shows a short countdown
                    output_dir=folder,
                )
            )
    removed = remove_shortcuts(read_created_shortcuts(), keep=created)
    write_created_shortcuts(created)
    print()
    for path in removed:
        print(f"[Info] Removed old shortcut: {path}")
    print(f"Shortcuts created in: {SHORTCUT_OUTPUT_DIR}")
    if start_menu:
        print(f"Start Menu folder: {start_menu}")
    if s.desktop_shortcuts:
        print("Desktop: " + ", ".join(s.desktop_shortcuts))
    print("=" * 30)


pause_on_success = True
