"""Create Windows shortcut (.lnk) files with icon, arguments and taskbar identity, without pywin32.

Standalone: copy this file anywhere, together with com_tools.py (needs com_tools.py next to it,
in one package folder). Standard library only (ctypes); Windows only.

A .lnk is a Windows COM format, not text: the standard library has no shortcut API, and the
AppUserModelID (which groups a pinned shortcut with its window in the taskbar) is not reachable
through the simpler WScript interface. So the COM interfaces are declared here with ctypes.
"""

from __future__ import annotations

import ctypes
import os
import time
import uuid
from ctypes import wintypes
from pathlib import Path
from typing import Optional

from . import com_tools as com


def create_shortcut(
    path: str,
    target: str,
    arguments: str = "",
    *,
    icon_path: Optional[str] = None,
    working_dir: str = "",
    description: str = "",
    show_minimized: bool = False,
    app_id: Optional[str] = None,
) -> str:
    """Write the shortcut ``path`` (a .lnk file) that runs ``target`` with ``arguments``.

    An existing file is replaced only by a complete new one (saved under a temporary name first).
    An empty ``working_dir`` leaves "Start in" empty, so Windows picks the folder. ``app_id`` sets
    the AppUserModelID. Returns the absolute path.
    """
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

    output_path = os.path.normpath(str(Path(path).absolute()))
    working_dir = os.path.normpath(str(Path(working_dir).absolute())) if working_dir else ""
    _shell_link_class_id = _guid("00021401-0000-0000-C000-000000000046")
    _shell_link_interface_id = _guid("000214F9-0000-0000-C000-000000000046")
    _persist_file_interface_id = _guid("0000010B-0000-0000-C000-000000000046")
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
            _check_hresult(interface.SetPath(shell_link, target), f'SetPath("{target}")')
            _check_hresult(
                interface.SetArguments(shell_link, arguments),
                "SetArguments",
            )
            _check_hresult(interface.SetWorkingDirectory(shell_link, working_dir), "SetWorkingDirectory")
            _check_hresult(interface.SetDescription(shell_link, description), "SetDescription")
            _check_hresult(
                interface.SetShowCmd(shell_link, 7 if show_minimized else 1),
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
