"""Generate Windows shortcuts for the configured PyApp Template launch modes."""

import ctypes
import os
import re
import sys
import time
import unicodedata
import uuid
from ctypes import wintypes

# =============================
# import from files

# add root dir for debug cases where this script is called on its own:
root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.developer_settings import (
    install_python_when_generating_shortcuts,
    log_path_rel_to_start_folder,
    no_terminal_shortcut_name,
    open_log_shortcut_name,
    open_settings_shortcut_name,
    program_name,
    stop_running_shortcut_name,
    use_global_python,
    user_settings_path,
    windows_terminal_shortcut_name,
)
from backend.DONT_CHANGE.scripts._common_code import (
    close_terminal,
    ensure_frontend_packages,
    make_abs_path_relative_to_file,
    print_traceback,
    sanitize_filename,
)
from backend.DONT_CHANGE.scripts._common_variables import (
    developer_settings_path,
    icon_path,
    launcher_log,
    launcher_no_terminal,
    launcher_settings,
    launcher_stop,
    launcher_terminal,
    log_icon_path,
    settings_icon_path,
    shortcut_output_dir,
    stop_icon_path,
)


def generate_shortcut(
    shortcut_name: str | bool | None,
    icon_path: str | os.PathLike[str] | None,
    launcher_path: str | os.PathLike[str],
    args: str | os.PathLike[str] | None = "",
    app_id: str | None = None,
    description: str | os.PathLike[str] | None = "",
    start_minimized: bool = False,
    classic_terminal: bool = True,
    wdir: str | os.PathLike[str] = "",
    enabled: bool = True,
) -> None:
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
    if not enabled or shortcut_name in (None, False, ""):
        return
    if os.name != "nt":
        raise OSError("Windows shortcut creation is only available on Windows.")
    if start_minimized and not classic_terminal:
        raise ValueError("A minimized shortcut requires classic_terminal=True")

    _hresult = ctypes.c_long
    _method = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
    _unused_method = ctypes.c_void_p

    class _Guid(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    class _PropertyKey(ctypes.Structure):
        _fields_ = [("fmtid", _Guid), ("pid", wintypes.DWORD)]

    class _PropVariant(ctypes.Structure):
        _fields_ = [
            ("vt", ctypes.c_ushort),
            ("reserved1", ctypes.c_ushort),
            ("reserved2", ctypes.c_ushort),
            ("reserved3", ctypes.c_ushort),
            ("string_value", ctypes.c_wchar_p),
        ]

    class _ShellLink(ctypes.Structure):
        pass

    _shell_link_pointer = ctypes.POINTER(_ShellLink)

    class _ShellLinkVTable(ctypes.Structure):
        _fields_ = [
            (
                "QueryInterface",
                _method(_hresult, _shell_link_pointer, ctypes.POINTER(_Guid), ctypes.POINTER(ctypes.c_void_p)),
            ),
            ("AddRef", _unused_method),
            ("Release", _method(ctypes.c_ulong, _shell_link_pointer)),
            ("GetPath", _unused_method),
            ("GetIDList", _unused_method),
            ("SetIDList", _unused_method),
            ("GetDescription", _unused_method),
            ("SetDescription", _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p)),
            ("GetWorkingDirectory", _unused_method),
            ("SetWorkingDirectory", _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p)),
            ("GetArguments", _unused_method),
            ("SetArguments", _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p)),
            ("GetHotkey", _unused_method),
            ("SetHotkey", _unused_method),
            ("GetShowCmd", _unused_method),
            ("SetShowCmd", _method(_hresult, _shell_link_pointer, ctypes.c_int)),
            ("GetIconLocation", _unused_method),
            ("SetIconLocation", _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p, ctypes.c_int)),
            ("SetRelativePath", _unused_method),
            ("Resolve", _unused_method),
            ("SetPath", _method(_hresult, _shell_link_pointer, ctypes.c_wchar_p)),
        ]

    _ShellLink._fields_ = [("vtable", ctypes.POINTER(_ShellLinkVTable))]

    class _PersistFile(ctypes.Structure):
        pass

    _persist_file_pointer = ctypes.POINTER(_PersistFile)

    class _PersistFileVTable(ctypes.Structure):
        _fields_ = [
            (
                "QueryInterface",
                _method(_hresult, _persist_file_pointer, ctypes.POINTER(_Guid), ctypes.POINTER(ctypes.c_void_p)),
            ),
            ("AddRef", _unused_method),
            ("Release", _method(ctypes.c_ulong, _persist_file_pointer)),
            ("GetClassID", _unused_method),
            ("IsDirty", _unused_method),
            ("Load", _unused_method),
            ("Save", _method(_hresult, _persist_file_pointer, ctypes.c_wchar_p, wintypes.BOOL)),
            ("SaveCompleted", _unused_method),
            ("GetCurFile", _unused_method),
        ]

    _PersistFile._fields_ = [("vtable", ctypes.POINTER(_PersistFileVTable))]

    class _PropertyStore(ctypes.Structure):
        pass

    _property_store_pointer = ctypes.POINTER(_PropertyStore)

    class _PropertyStoreVTable(ctypes.Structure):
        _fields_ = [
            (
                "QueryInterface",
                _method(_hresult, _property_store_pointer, ctypes.POINTER(_Guid), ctypes.POINTER(ctypes.c_void_p)),
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
        ]

    _PropertyStore._fields_ = [("vtable", ctypes.POINTER(_PropertyStoreVTable))]

    def _guid(value: str) -> _Guid:
        parsed = uuid.UUID(value)
        return _Guid(
            parsed.time_low,
            parsed.time_mid,
            parsed.time_hi_version,
            (wintypes.BYTE * 8)(*parsed.bytes[8:]),
        )

    def _check_hresult(result: int, action: str) -> None:
        if result >= 0:
            return
        code = result & 0xFFFFFFFF
        try:
            message = ctypes.FormatError(code).strip()
        except Exception:
            message = "unknown error"
        raise OSError(f"{action} failed with HRESULT 0x{code:08X}: {message}")

    def _wait_for_file(output_path: str, should_exist: bool) -> None:
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
        return '"' + os.fspath(value).replace('"', '""') + '"'

    _shell_link_class_id = _guid("00021401-0000-0000-C000-000000000046")
    _shell_link_interface_id = _guid("000214F9-0000-0000-C000-000000000046")
    _persist_file_interface_id = _guid("0000010B-0000-0000-C000-000000000046")
    _property_store_interface_id = _guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
    _app_id_key = _PropertyKey(_guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5)

    output_path = os.path.abspath(os.path.join(shortcut_output_dir, sanitize_filename(shortcut_name) + ".lnk"))
    launcher_args = [_quote(launcher_path)] if classic_terminal else ["/d", "/k", "call", _quote(launcher_path)]
    if args not in ("", None):
        launcher_args.append(_quote(args))

    icon_path = os.path.abspath(os.fspath(icon_path)) if icon_path else None
    if icon_path and not os.path.exists(icon_path):
        print(f'[Warning] icon not existing at "{icon_path}"')
        icon_path = None
    wdir = os.path.abspath(wdir) if wdir else ""
    description = "" if description is None else os.fspath(description)

    print(f"[Info] Generating: {output_path}")
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
    if result < 0 and (result & 0xFFFFFFFF) != 0x80010106:
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
            _check_hresult(interface.SetPath(shell_link, target), f'SetPath("{target}")')
            _check_hresult(interface.SetArguments(shell_link, " ".join(launcher_args)), "SetArguments")
            _check_hresult(interface.SetWorkingDirectory(shell_link, wdir), "SetWorkingDirectory")
            _check_hresult(interface.SetDescription(shell_link, description), "SetDescription")
            _check_hresult(interface.SetShowCmd(shell_link, 7 if start_minimized else 1), "SetShowCmd")

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
                property_store = ctypes.cast(property_store_pointer, _property_store_pointer)
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
                result = persist_file.contents.vtable.contents.Save(persist_file, output_path, True)
                _check_hresult(result, f'Save shortcut "{output_path}"')
            finally:
                persist_file.contents.vtable.contents.Release(persist_file)
        finally:
            shell_link.contents.vtable.contents.Release(shell_link)
    finally:
        if should_uninitialize:
            ole32.CoUninitialize()

    _wait_for_file(output_path, should_exist=True)


def _sanitize_app_id(value: str) -> str:
    name = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"[^a-z0-9.-]", "", name)
    name = re.sub(r"-+", "-", name)
    name = re.sub(r"\.+", ".", name)
    return name.strip("-.")


def main() -> None:
    app_id = _sanitize_app_id(program_name)
    if len(app_id) > 15:
        app_id = app_id.replace("-", "").replace(".", "")
    if len(app_id) > 15:
        app_id = app_id[:7] + app_id[-7:]

    if install_python_when_generating_shortcuts and not use_global_python:
        ensure_frontend_packages(app_id)

    print()
    print("=" * 30)
    print()

    generate_shortcut(
        windows_terminal_shortcut_name,
        icon_path,
        launcher_terminal,
        args=app_id,
        app_id=app_id,
        description=f"Start {program_name} in Windows Terminal",
        start_minimized=True,
    )
    generate_shortcut(
        no_terminal_shortcut_name,
        icon_path,
        launcher_no_terminal,
        args=app_id,
        app_id=app_id + "W",
        description=f"Start {program_name} without opening a terminal window",
        start_minimized=True,
    )
    generate_shortcut(
        stop_running_shortcut_name,
        stop_icon_path,
        launcher_stop,
        description=f"Stop running {program_name} processes",
    )
    generate_shortcut(
        open_log_folder_shortcut_name,
        log_icon_path,
        launcher_log,
        description=f"Open the current {program_name} log file",
        start_minimized=True,
        enabled=log_path not in (None, False, ""),
    )

    if user_settings_path not in (None, False, "") and open_settings_shortcut_name not in (None, False, ""):
        settings_file_path_abs = make_abs_path_relative_to_file(user_settings_path, developer_settings_path)
        if not os.path.exists(settings_file_path_abs):
            print(
                f'[Warning] User settings file does not exist at "{settings_file_path_abs}". '
                "The settings shortcut will still be created, but it will show an error until the file exists. "
                f'Disable the settings shortcut by setting user_settings_path = None in "{developer_settings_path}".'
            )
    generate_shortcut(
        open_settings_shortcut_name,
        settings_icon_path,
        launcher_settings,
        description=f"Open the {program_name} settings file",
        start_minimized=True,
        enabled=user_settings_path not in (None, False, ""),
    )

    print()
    print(f"Shortcut(s) created in: {shortcut_output_dir}")
    print()
    print("=" * 30)
    input("[Success] Press enter to exit")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print_traceback(f"[Error] {error}")
        input("[Success] Press enter to exit")
    close_terminal()
