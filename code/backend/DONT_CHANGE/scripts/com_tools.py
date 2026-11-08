"""Minimal Windows COM helpers (ctypes, no pywin32): GUIDs, HRESULTs and the AppUserModelID.

Shared by scripts/shortcuts.py (the ID stored in a .lnk) and console_tools.py (the ID
of the console window), so pinned shortcuts and their windows group together in the taskbar.
"""

from __future__ import annotations

import ctypes
import uuid
from ctypes import wintypes
from typing import Protocol

HRESULT = ctypes.c_long
# COM method pointer type (stdcall); CFUNCTYPE only so the module imports on non-Windows tools.
METHOD = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
UNUSED_METHOD = ctypes.c_void_p  # vtable slot that is never called
VT_LPWSTR = 31
RPC_E_CHANGED_MODE = 0x80010106


class GUID(ctypes.Structure):
    _fields_ = (
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    )


def guid(text: str) -> GUID:
    """GUID structure from its text form, e.g. "886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"."""
    parsed = uuid.UUID(text)
    return GUID(parsed.time_low, parsed.time_mid, parsed.time_hi_version, (ctypes.c_ubyte * 8)(*parsed.bytes[8:]))


class PROPERTYKEY(ctypes.Structure):
    _fields_ = (("fmtid", GUID), ("pid", wintypes.DWORD))


class PROPVARIANT(ctypes.Structure):
    """String-valued PROPVARIANT (VT_LPWSTR), the only kind used here."""

    _fields_ = (
        ("vt", ctypes.c_ushort),
        ("reserved1", ctypes.c_ushort),
        ("reserved2", ctypes.c_ushort),
        ("reserved3", ctypes.c_ushort),
        ("string_value", ctypes.c_wchar_p),
    )


class IPropertyStore(ctypes.Structure):
    pass


PropertyStorePointer = ctypes.POINTER(IPropertyStore)


class PropertyStoreReference(Protocol):
    """Public structural type for a pointer exposing an IPropertyStore."""

    @property
    def contents(self) -> IPropertyStore: ...


class _IPropertyStoreVTable(ctypes.Structure):
    _fields_ = (
        ("QueryInterface", UNUSED_METHOD),
        ("AddRef", UNUSED_METHOD),
        ("Release", METHOD(ctypes.c_ulong, PropertyStorePointer)),
        ("GetCount", UNUSED_METHOD),
        ("GetAt", UNUSED_METHOD),
        ("GetValue", UNUSED_METHOD),
        ("SetValue", METHOD(HRESULT, PropertyStorePointer, ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))),
        ("Commit", METHOD(HRESULT, PropertyStorePointer)),
    )


IPropertyStore._fields_ = [("vtable", ctypes.POINTER(_IPropertyStoreVTable))]

IID_PROPERTY_STORE = guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
PKEY_APP_USER_MODEL_ID = PROPERTYKEY(guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5)


def check_hresult(result: int, action: str) -> None:
    """Raise OSError naming the failed COM call and the Windows error message."""
    if result >= 0:
        return
    code = result & 0xFFFFFFFF
    try:
        message = ctypes.FormatError(code).strip()
    except Exception:
        message = "unknown error"
    raise OSError(f"{action} failed with HRESULT 0x{code:08X}: {message}")


def co_initialize() -> bool:
    """CoInitialize this thread; returns whether co_uninitialize() must be called afterwards."""
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CoInitialize.argtypes = [ctypes.c_void_p]
    ole32.CoInitialize.restype = HRESULT
    result = ole32.CoInitialize(None)
    if result < 0 and (result & 0xFFFFFFFF) != RPC_E_CHANGED_MODE:
        check_hresult(result, "CoInitialize")
    return result in (0, 1)  # S_OK, S_FALSE


def co_uninitialize(needed: bool) -> None:
    if needed:
        ctypes.WinDLL("ole32", use_last_error=True).CoUninitialize()


def set_app_user_model_id(store: PropertyStoreReference, app_id: str) -> None:
    """Write System.AppUserModel.ID into a property store, commit it and release the store."""
    try:
        value = PROPVARIANT()
        value.vt = VT_LPWSTR
        value.string_value = app_id
        check_hresult(
            store.contents.vtable.contents.SetValue(store, ctypes.byref(PKEY_APP_USER_MODEL_ID), ctypes.byref(value)),
            "SetValue(System.AppUserModel.ID)",
        )
        check_hresult(store.contents.vtable.contents.Commit(store), "Commit(IPropertyStore)")
    finally:
        store.contents.vtable.contents.Release(store)
