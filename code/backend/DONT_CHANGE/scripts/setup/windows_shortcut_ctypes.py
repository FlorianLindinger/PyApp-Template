"""Create Windows shortcut files with Windows COM through ctypes."""

import ctypes
import os
import uuid
from ctypes import wintypes


HRESULT = ctypes.c_long
STDMETHOD = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)

CLSCTX_INPROC_SERVER = 0x1
RPC_E_CHANGED_MODE = 0x80010106
S_FALSE = 1
S_OK = 0
SW_SHOWMINNOACTIVE = 7
SW_SHOWNORMAL = 1
VT_LPWSTR = 31


class GUID(ctypes.Structure):
    """Windows GUID structure used by COM APIs."""

    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


class PROPERTYKEY(ctypes.Structure):
    """Windows PROPERTYKEY structure."""

    _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]


class PROPVARIANT(ctypes.Structure):
    """Minimal PROPVARIANT layout for VT_LPWSTR string values."""

    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("wReserved1", ctypes.c_ushort),
        ("wReserved2", ctypes.c_ushort),
        ("wReserved3", ctypes.c_ushort),
        ("pwszVal", ctypes.c_wchar_p),
    ]


class IShellLinkW(ctypes.Structure):
    """COM IShellLinkW interface."""


IShellLinkWPtr = ctypes.POINTER(IShellLinkW)


class IShellLinkWVtbl(ctypes.Structure):
    """COM IShellLinkW vtable layout."""

    _fields_ = [
        (
            "QueryInterface",
            STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)),
        ),
        ("AddRef", STDMETHOD(ctypes.c_ulong, IShellLinkWPtr)),
        ("Release", STDMETHOD(ctypes.c_ulong, IShellLinkWPtr)),
        (
            "GetPath",
            STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD),
        ),
        ("GetIDList", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.POINTER(ctypes.c_void_p))),
        ("SetIDList", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_void_p)),
        ("GetDescription", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p, ctypes.c_int)),
        ("SetDescription", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p)),
        ("GetWorkingDirectory", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p, ctypes.c_int)),
        ("SetWorkingDirectory", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p)),
        ("GetArguments", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p, ctypes.c_int)),
        ("SetArguments", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p)),
        ("GetHotkey", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.POINTER(ctypes.c_short))),
        ("SetHotkey", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_short)),
        ("GetShowCmd", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.POINTER(ctypes.c_int))),
        ("SetShowCmd", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_int)),
        (
            "GetIconLocation",
            STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)),
        ),
        ("SetIconLocation", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p, ctypes.c_int)),
        ("SetRelativePath", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p, wintypes.DWORD)),
        ("Resolve", STDMETHOD(HRESULT, IShellLinkWPtr, wintypes.HWND, wintypes.DWORD)),
        ("SetPath", STDMETHOD(HRESULT, IShellLinkWPtr, ctypes.c_wchar_p)),
    ]


IShellLinkW._fields_ = [("lpVtbl", ctypes.POINTER(IShellLinkWVtbl))]


class IPersistFile(ctypes.Structure):
    """COM IPersistFile interface."""


IPersistFilePtr = ctypes.POINTER(IPersistFile)


class IPersistFileVtbl(ctypes.Structure):
    """COM IPersistFile vtable layout."""

    _fields_ = [
        (
            "QueryInterface",
            STDMETHOD(HRESULT, IPersistFilePtr, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)),
        ),
        ("AddRef", STDMETHOD(ctypes.c_ulong, IPersistFilePtr)),
        ("Release", STDMETHOD(ctypes.c_ulong, IPersistFilePtr)),
        ("GetClassID", STDMETHOD(HRESULT, IPersistFilePtr, ctypes.POINTER(GUID))),
        ("IsDirty", STDMETHOD(HRESULT, IPersistFilePtr)),
        ("Load", STDMETHOD(HRESULT, IPersistFilePtr, ctypes.c_wchar_p, wintypes.DWORD)),
        ("Save", STDMETHOD(HRESULT, IPersistFilePtr, ctypes.c_wchar_p, wintypes.BOOL)),
        ("SaveCompleted", STDMETHOD(HRESULT, IPersistFilePtr, ctypes.c_wchar_p)),
        ("GetCurFile", STDMETHOD(HRESULT, IPersistFilePtr, ctypes.POINTER(ctypes.c_wchar_p))),
    ]


IPersistFile._fields_ = [("lpVtbl", ctypes.POINTER(IPersistFileVtbl))]


class IPropertyStore(ctypes.Structure):
    """COM IPropertyStore interface."""


IPropertyStorePtr = ctypes.POINTER(IPropertyStore)


class IPropertyStoreVtbl(ctypes.Structure):
    """COM IPropertyStore vtable layout."""

    _fields_ = [
        (
            "QueryInterface",
            STDMETHOD(HRESULT, IPropertyStorePtr, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)),
        ),
        ("AddRef", STDMETHOD(ctypes.c_ulong, IPropertyStorePtr)),
        ("Release", STDMETHOD(ctypes.c_ulong, IPropertyStorePtr)),
        ("GetCount", STDMETHOD(HRESULT, IPropertyStorePtr, ctypes.POINTER(wintypes.DWORD))),
        ("GetAt", STDMETHOD(HRESULT, IPropertyStorePtr, wintypes.DWORD, ctypes.POINTER(PROPERTYKEY))),
        ("GetValue", STDMETHOD(HRESULT, IPropertyStorePtr, ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))),
        ("SetValue", STDMETHOD(HRESULT, IPropertyStorePtr, ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))),
        ("Commit", STDMETHOD(HRESULT, IPropertyStorePtr)),
    ]


IPropertyStore._fields_ = [("lpVtbl", ctypes.POINTER(IPropertyStoreVtbl))]


CLSID_SHELL_LINK = None
IID_IPERSIST_FILE = None
IID_IPROPERTY_STORE = None
IID_ISHELL_LINK_W = None
PKEY_APP_USER_MODEL_ID = None


def make_guid(value: str) -> GUID:
    """Convert a canonical GUID string to the binary Windows layout."""
    parsed = uuid.UUID(value)
    return GUID(
        parsed.time_low,
        parsed.time_mid,
        parsed.time_hi_version,
        (ctypes.c_ubyte * 8)(*parsed.bytes[8:]),
    )


def init_constants() -> None:
    """Initialize COM GUID constants lazily."""
    global CLSID_SHELL_LINK
    global IID_IPERSIST_FILE
    global IID_IPROPERTY_STORE
    global IID_ISHELL_LINK_W
    global PKEY_APP_USER_MODEL_ID

    if CLSID_SHELL_LINK is not None:
        return

    CLSID_SHELL_LINK = make_guid("00021401-0000-0000-C000-000000000046")
    IID_ISHELL_LINK_W = make_guid("000214F9-0000-0000-C000-000000000046")
    IID_IPERSIST_FILE = make_guid("0000010B-0000-0000-C000-000000000046")
    IID_IPROPERTY_STORE = make_guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
    PKEY_APP_USER_MODEL_ID = PROPERTYKEY(make_guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5)


def format_hresult(hr: int) -> str:
    """Format a Windows HRESULT as hex plus the system message when available."""
    code = hr & 0xFFFFFFFF
    try:
        message = ctypes.FormatError(code).strip()
    except Exception:
        message = "unknown error"
    return f"0x{code:08X}: {message}"


def check_hresult(hr: int, action: str) -> None:
    """Raise OSError when a COM call failed."""
    if hr < 0:
        raise OSError(f"{action} failed with HRESULT {format_hresult(hr)}")


class ComApartment:
    """Initialize COM for this thread while respecting an existing apartment."""

    def __init__(self) -> None:
        self._ole32 = ctypes.WinDLL("ole32", use_last_error=True)
        self._ole32.CoInitialize.argtypes = [ctypes.c_void_p]
        self._ole32.CoInitialize.restype = HRESULT
        self._ole32.CoUninitialize.argtypes = []
        self._ole32.CoUninitialize.restype = None
        self._should_uninitialize = False

    def __enter__(self) -> "ComApartment":
        hr = self._ole32.CoInitialize(None)
        self._should_uninitialize = hr in {S_OK, S_FALSE}
        if hr < 0 and (hr & 0xFFFFFFFF) != RPC_E_CHANGED_MODE:
            raise OSError(f"CoInitialize failed with HRESULT {format_hresult(hr)}")
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback) -> None:
        if self._should_uninitialize:
            self._ole32.CoUninitialize()


def create_shell_link() -> IShellLinkWPtr:
    """Create an empty IShellLinkW COM object."""
    init_constants()

    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(GUID),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    ole32.CoCreateInstance.restype = HRESULT

    shell_link_void = ctypes.c_void_p()
    hr = ole32.CoCreateInstance(
        ctypes.byref(CLSID_SHELL_LINK),
        None,
        CLSCTX_INPROC_SERVER,
        ctypes.byref(IID_ISHELL_LINK_W),
        ctypes.byref(shell_link_void),
    )
    check_hresult(hr, "CoCreateInstance(CLSID_ShellLink)")
    return ctypes.cast(shell_link_void, IShellLinkWPtr)


def query_interface(com_object, iid: GUID, pointer_type, action: str):
    """Query one COM interface pointer for another interface."""
    queried_void = ctypes.c_void_p()
    hr = com_object.contents.lpVtbl.contents.QueryInterface(com_object, ctypes.byref(iid), ctypes.byref(queried_void))
    check_hresult(hr, action)
    return ctypes.cast(queried_void, pointer_type)


def set_app_user_model_id(shell_link: IShellLinkWPtr, app_id: str) -> None:
    """Attach System.AppUserModel.ID to a shell link object."""
    property_store = query_interface(
        shell_link,
        IID_IPROPERTY_STORE,
        IPropertyStorePtr,
        "QueryInterface(IPropertyStore)",
    )
    try:
        prop_var = PROPVARIANT()
        prop_var.vt = VT_LPWSTR
        prop_var.pwszVal = app_id

        hr = property_store.contents.lpVtbl.contents.SetValue(
            property_store,
            ctypes.byref(PKEY_APP_USER_MODEL_ID),
            ctypes.byref(prop_var),
        )
        check_hresult(hr, "SetValue(System.AppUserModel.ID)")

        hr = property_store.contents.lpVtbl.contents.Commit(property_store)
        check_hresult(hr, "Commit(IPropertyStore)")
    finally:
        property_store.contents.lpVtbl.contents.Release(property_store)


def save_shell_link(shell_link: IShellLinkWPtr, output: str) -> None:
    """Save a shell link object as a .lnk file."""
    persist_file = query_interface(
        shell_link,
        IID_IPERSIST_FILE,
        IPersistFilePtr,
        "QueryInterface(IPersistFile)",
    )
    try:
        hr = persist_file.contents.lpVtbl.contents.Save(persist_file, output, True)
        check_hresult(hr, f'Save shortcut "{output}"')
    finally:
        persist_file.contents.lpVtbl.contents.Release(persist_file)


def create_shortcut_with_appid(
    output: str,
    target: str = "cmd.exe",
    args: str = "",
    icon_path: str | None = None,
    wdir: str = "",
    app_id: str | None = None,
    description: str = "",
    start_minimized: bool = False,
) -> None:
    """Create a Windows shortcut and optionally assign an AppUserModelID."""
    if os.name != "nt":
        raise OSError("Windows shortcut creation is only available on Windows.")

    output = os.path.abspath(os.fspath(output))
    target = os.fspath(target)
    args = "" if args is None else os.fspath(args)
    wdir = "" if wdir is None else os.fspath(wdir)
    description = "" if description is None else os.fspath(description)

    if icon_path is not None:
        icon_path = os.path.abspath(os.fspath(icon_path))

    if wdir:
        wdir = os.path.abspath(wdir)

    parent_dir = os.path.dirname(output)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with ComApartment():
        shell_link = create_shell_link()
        try:
            shell_link_vtbl = shell_link.contents.lpVtbl.contents

            check_hresult(shell_link_vtbl.SetPath(shell_link, target), f'SetPath("{target}")')
            check_hresult(shell_link_vtbl.SetArguments(shell_link, args), "SetArguments")
            check_hresult(shell_link_vtbl.SetWorkingDirectory(shell_link, wdir), "SetWorkingDirectory")
            check_hresult(shell_link_vtbl.SetDescription(shell_link, description), "SetDescription")
            check_hresult(
                shell_link_vtbl.SetShowCmd(shell_link, SW_SHOWMINNOACTIVE if start_minimized else SW_SHOWNORMAL),
                "SetShowCmd",
            )

            if icon_path:
                check_hresult(shell_link_vtbl.SetIconLocation(shell_link, icon_path, 0), f'SetIconLocation("{icon_path}")')

            if app_id is not None:
                set_app_user_model_id(shell_link, app_id)

            save_shell_link(shell_link, output)
        finally:
            shell_link.contents.lpVtbl.contents.Release(shell_link)
