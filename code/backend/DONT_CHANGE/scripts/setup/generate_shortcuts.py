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

# =============================

HRESULT = ctypes.c_long
STDMETHOD = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)

CLSCTX_INPROC_SERVER = 0x1
RPC_E_CHANGED_MODE = 0x80010106
S_FALSE = 1
S_OK = 0
SHORTCUT_DELETE_TIMEOUT_SECONDS = 5.0
SHORTCUT_CREATE_TIMEOUT_SECONDS = 5.0
SHORTCUT_RETRY_DELAY_SECONDS = 0.1
SW_SHOWMINNOACTIVE = 7
SW_SHOWNORMAL = 1
VT_LPWSTR = 31

# =============================


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
        (wintypes.BYTE * 8)(*parsed.bytes[8:]),
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


def delete_existing_shortcut(output: str) -> None:
    """Delete a shortcut before saving so locked files fail with a clear timeout."""
    if not os.path.exists(output):
        return

    deadline = time.monotonic() + SHORTCUT_DELETE_TIMEOUT_SECONDS
    last_error = None

    while os.path.exists(output):
        try:
            os.remove(output)
        except FileNotFoundError:
            return
        except OSError as error:
            last_error = error

        if not os.path.exists(output):
            return

        if time.monotonic() >= deadline:
            detail = f" Last Windows error: {last_error}" if last_error else ""
            raise RuntimeError(
                f'Failed to delete existing shortcut within {SHORTCUT_DELETE_TIMEOUT_SECONDS:.1f} seconds: "{output}". '
                f"Close the shortcut Properties window or any program using the file and try again.{detail}"
            )

        time.sleep(SHORTCUT_RETRY_DELAY_SECONDS)


def check_shortcut_was_created(output: str) -> None:
    """Verify the shortcut appeared on disk after COM save returned success."""
    deadline = time.monotonic() + SHORTCUT_CREATE_TIMEOUT_SECONDS

    while not os.path.exists(output):
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f'Failed to create shortcut within {SHORTCUT_CREATE_TIMEOUT_SECONDS:.1f} seconds: "{output}".'
            )

        time.sleep(SHORTCUT_RETRY_DELAY_SECONDS)


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
        if not os.path.exists(icon_path):
            print(f'[Warning] icon not existing at "{icon_path}"')
            icon_path = None

    if wdir:
        wdir = os.path.abspath(wdir)

    parent_dir = os.path.dirname(output)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    delete_existing_shortcut(output)

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
                check_hresult(
                    shell_link_vtbl.SetIconLocation(shell_link, icon_path, 0), f'SetIconLocation("{icon_path}")'
                )

            if app_id is not None:
                set_app_user_model_id(shell_link, app_id)

            save_shell_link(shell_link, output)
        finally:
            shell_link.contents.lpVtbl.contents.Release(shell_link)

    check_shortcut_was_created(output)


def quote_cmd_argument(value):
    """Quote the cmd argument."""
    text = os.fspath(value)
    return '"' + text.replace('"', '""') + '"'


def sanitize_app_id(input_string):
    # 1. Convert to lowercase and normalize unicode (e.g., convert 'é' to 'e')
    """Sanitize the program name into a compact Windows AppUserModelID."""
    name = unicodedata.normalize("NFKD", input_string).encode("ascii", "ignore").decode("ascii").lower()
    # 2. Replace spaces and underscores with hyphens
    name = re.sub(r"[\s_]+", "-", name)
    # 3. Remove any character that isn't lowercase a-z, 0-9, a hyphen, or a dot
    name = re.sub(r"[^a-z0-9\-\.]", "", name)
    # 4. Remove duplicate hyphens or dots (e.g., "my--app" becomes "my-app")
    name = re.sub(r"-+", "-", name)
    name = re.sub(r"\.+", ".", name)
    # 5. Trim hyphens/dots from the start and end
    name = name.strip("-.")
    return name


def make_lnk(
    output_path,
    icon_path,
    launcher_path,
    args="",
    appid=None,
    description="",
    start_minimized=False,
    classic_terminal=True,
    wdir="",
):
    """Create one configured launcher shortcut file.

    Note that classic_terminal will be forced by Windows when start_minimized == True -> raise if start_minimized==True and classic_terminal==False,"""
    print(f"[Info] Generating: {output_path}")

    if classic_terminal:
        launcher_args = [quote_cmd_argument(launcher_path)]
        target = "conhost.exe"
    else:
        launcher_args = ["/d", "/k", "call", quote_cmd_argument(launcher_path)]
        target = "cmd.exe"

    if args not in ["", None]:
        launcher_args.append(quote_cmd_argument(args))

    if start_minimized == True and classic_terminal == False:
        raise ValueError(
            "classic_terminal will be forced by Windows when start_minimized == True but start_minimized==True + classic_terminal==False"
        )

    create_shortcut_with_appid(
        args=" ".join(launcher_args),
        output=output_path,
        app_id=appid,
        icon_path=icon_path,
        target=target,
        wdir=wdir,
        description=description,
        start_minimized=start_minimized,
    )


def main():
    # generate app-id
    appid = sanitize_app_id(program_name)
    # replace and shorten if too long which might cause path length limit problems (10 is arbitrary)
    if len(appid) > 15:
        appid = appid.replace("-", "").replace(".", "")
    if len(appid) > 15:
        appid = appid[:7] + appid[-7:]

    # install frontend python and packages if install_python_when_generating_shortcuts==True
    if install_python_when_generating_shortcuts and not use_global_python:
        ensure_frontend_packages(
            appid
        )  # appid probably doesnt matter but it still triggers icon change and title change when appid!=""

    # prints:
    print()
    print("="*30)
    print()

    # Shortcut: normal start
    if windows_terminal_shortcut_name not in [None, False, ""]:
        out = shortcut_output_dir + "\\" + sanitize_filename(windows_terminal_shortcut_name) + ".lnk"
        make_lnk(
            out,
            icon_path,
            launcher_terminal,
            args=appid,
            appid=appid,
            description=f"Start {program_name} in Windows Terminal",
            start_minimized=True,
        )

    # Shortcut: start without terminal
    if no_terminal_shortcut_name not in [False, None, ""]:
        out = shortcut_output_dir + "\\" + sanitize_filename(no_terminal_shortcut_name) + ".lnk"
        make_lnk(
            out,
            icon_path,
            launcher_no_terminal,
            args=appid,
            appid=appid
            + "W",  # add "W" for windowless to allow both launchers to pin to taskbar because different app-id (for same shortcut target)
            description=f"Start {program_name} without opening a terminal window",
            start_minimized=True,
        )

    # Shortcut: stop program started by any generated launcher mode
    if stop_running_shortcut_name not in ["", False, None]:
        out = shortcut_output_dir + "\\" + sanitize_filename(stop_running_shortcut_name) + ".lnk"
        make_lnk(
            out,
            stop_icon_path,
            launcher_stop,
            description=f"Stop running {program_name} processes",
            start_minimized=False,
        )

    # Shortcut: open current log file
    if log_path_rel_to_start_folder not in [None, False, ""] and open_log_shortcut_name not in [None, False, ""]:
        out = shortcut_output_dir + "\\" + sanitize_filename(open_log_shortcut_name) + ".lnk"
        make_lnk(
            out,
            log_icon_path,
            launcher_log,
            description=f"Open the current {program_name} log file",
            start_minimized=True,
        )

    # Shortcut: open settings
    if user_settings_path not in [None, False, ""] and open_settings_shortcut_name not in [None, False, ""]:
        settings_file_path_abs = make_abs_path_relative_to_file(user_settings_path, developer_settings_path)
        if not os.path.exists(settings_file_path_abs):
            print(
                f'[Warning] User settings file does not exist at "{settings_file_path_abs}". '
                f"The settings shortcut will still be created, but it will show an error until the file exists. "
                f'Disable the settings shortcut by setting user_settings_path = None in "{developer_settings_path}".'
            )
        out = shortcut_output_dir + "\\" + sanitize_filename(open_settings_shortcut_name) + ".lnk"
        make_lnk(
            out,
            settings_icon_path,
            launcher_settings,
            description=f"Open the {program_name} settings file",
            start_minimized=True,
        )

    print()
    print(f"Shortcut(s) created in: {shortcut_output_dir}")
    print()
    print("=============================")
    input("[Success] Press enter to exit")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print_traceback(f"[Error] {e}")
        input("[Success] Press enter to exit")
    close_terminal()
