import os
import re
import sys
import time
import unicodedata

import win32com.propsys.propsys as propsys  # type:ignore #noqa
import win32com.propsys.pscon as pscon  # type:ignore #noqa
from win32com.client import Dispatch  # type:ignore
from win32com.shell import shellcon  # type:ignore

# add root dir for debug cases where this script is called on its own:
root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# =============================
# imports

import developer_settings
from developer_settings import (
    no_terminal_shortcut_name,
    open_settings_shortcut_name,
    program_name,
    stop_running_shortcut_name,
    terminal_emulator_shortcut_name,
    user_settings_path,
    windows_terminal_shortcut_name,
)

browser_shortcut_name = getattr(developer_settings, "browser_shortcut_name", "")  # backwards compatible
from DONT_CHANGE.specific_scripts.common_code import (
    close_terminal,
    make_abs_path_relative_to_file,
    print_traceback,
    sanitize_filename,
)
from DONT_CHANGE.specific_scripts.common_variables import (
    developer_settings_path,
    icon_path,
    launcher_browser,
    launcher_emulator,
    launcher_no_terminal,
    launcher_settings,
    launcher_stop,
    launcher_terminal,
    settings_icon_path,
    shortcut_output_dir,
    stop_icon_path,
)

# =============================
# local variables:

SHORTCUT_DELETE_TIMEOUT_SECONDS = 5.0
SHORTCUT_CREATE_TIMEOUT_SECONDS = 5.0
SHORTCUT_RETRY_DELAY_SECONDS = 0.1

# =============================


def quote_cmd_argument(value):
    text = os.fspath(value)
    return '"' + text.replace('"', '""') + '"'


def sanitize_app_id(input_string):
    # 1. Convert to lowercase and normalize unicode (e.g., convert 'é' to 'e')
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


def delete_existing_shortcut(output):
    if not os.path.exists(output):
        return

    deadline = time.monotonic() + SHORTCUT_DELETE_TIMEOUT_SECONDS
    last_error = None

    while os.path.exists(output):
        try:
            os.remove(output)
        except FileNotFoundError:
            return
        except OSError as e:
            last_error = e

        if not os.path.exists(output):
            return

        if time.monotonic() >= deadline:
            detail = f" Last Windows error: {last_error}" if last_error else ""
            raise RuntimeError(
                f'Failed to delete existing shortcut within {SHORTCUT_DELETE_TIMEOUT_SECONDS:.1f} seconds: "{output}". '
                f"Close the shortcut Properties window or any program using the file and try again.{detail}"
            )

        time.sleep(SHORTCUT_RETRY_DELAY_SECONDS)


def check_shortcut_was_created(output):
    deadline = time.monotonic() + SHORTCUT_CREATE_TIMEOUT_SECONDS

    while not os.path.exists(output):
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f'Failed to create shortcut within {SHORTCUT_CREATE_TIMEOUT_SECONDS:.1f} seconds: "{output}".'
            )

        time.sleep(SHORTCUT_RETRY_DELAY_SECONDS)


def create_shortcut_with_appid(output, target, args="", icon_path=None, wdir="", app_id=None, description=""):

    if (icon_path is not None) and (not os.path.exists(icon_path)):
        print('[Warning] icon not existing at "{icon_path}"')
        icon_path = None

    if icon_path and not os.path.isabs(icon_path):
        icon_path = os.path.abspath(icon_path)
    if output and not os.path.isabs(output):
        output = os.path.abspath(output)
    if wdir != "" and not os.path.isabs(wdir):
        wdir = os.path.abspath(wdir)

    # Delete first so a locked shortcut fails with a clear timeout instead of hanging.
    delete_existing_shortcut(output)

    # 1. Create the shortcut file via WScript.Shell (Standard)
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(output)
    shortcut.TargetPath = target
    shortcut.Arguments = args
    shortcut.WorkingDirectory = wdir
    shortcut.Description = description
    if icon_path:
        shortcut.IconLocation = icon_path
    try:
        shortcut.Save()
    except Exception as e:
        raise RuntimeError(
            f'Failed to save shortcut: "{output}". Close the shortcut Properties window or any program using the file '
            f"and try again. Windows error: {e}"
        ) from e
    check_shortcut_was_created(output)

    # 2. Add AppUserModelID via IPropertyStore (Advanced)
    if app_id is not None:
        # Wait for Windows to release file lock before property store access
        time.sleep(1.0)
        try:
            pStore = propsys.SHGetPropertyStoreFromParsingName(
                output, None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
            )
            key = pscon.PKEY_AppUserModel_ID
            prop_var = propsys.PROPVARIANTType(app_id)
            pStore.SetValue(key, prop_var)
            pStore.Commit()
        except Exception:
            # try again
            time.sleep(1.0)
            try:
                pStore = propsys.SHGetPropertyStoreFromParsingName(
                    output, None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
                )
                key = pscon.PKEY_AppUserModel_ID
                prop_var = propsys.PROPVARIANTType(app_id)
                pStore.SetValue(key, prop_var)
                pStore.Commit()
            except Exception as e:
                print(f"[Warning] Failed to set AppID: {e}")


def make_lnk(output_path, icon_path, launcher_path, args="", appid=None, description=""):

    print(f"[Info] Generating: {output_path}")

    launcher_args = ["/d", "/k", "call", quote_cmd_argument(launcher_path)]
    if args not in ["", None]:
        launcher_args.append(quote_cmd_argument(args))

    create_shortcut_with_appid(
        args=" ".join(launcher_args),
        output=output_path,
        app_id=appid,
        icon_path=icon_path,
        target=os.environ.get("COMSPEC", "cmd.exe"),
        wdir="",
        description=description,
    )


def main():

    # generate app-id
    appid = sanitize_app_id(program_name)
    # replace and shorten if too long which might cause path length limit problems (10 is arbitrary)
    if len(appid) > 15:
        appid.replace("-", "").replace(".", "")
    if len(appid) > 15:
        appid = appid[:7] + appid[-7:]

    # Shortcut: normal start
    if windows_terminal_shortcut_name not in [None, False, ""]:
        out = shortcut_output_dir + "\\" + sanitize_filename(windows_terminal_shortcut_name) + ".lnk"
        make_lnk(
            out,
            icon_path,
            launcher_terminal,
            args=appid,
            appid=appid,
            description=f"Start {program_name} in Windows Terminal.",
        )

    # Shortcut: start in terminal emulator
    if terminal_emulator_shortcut_name not in [None, False, ""]:
        out = shortcut_output_dir + "\\" + sanitize_filename(terminal_emulator_shortcut_name) + ".lnk"
        make_lnk(
            out,
            icon_path,
            launcher_emulator,
            args=appid,
            appid=appid + "E",  # use a separate AppID so the terminal emulator can be pinned separately
            description=f"Start {program_name} in the bundled terminal emulator.",
        )

    # Shortcut: start in browser terminal
    if browser_shortcut_name not in [None, False, ""]:
        out = shortcut_output_dir + "\\" + sanitize_filename(browser_shortcut_name) + ".lnk"
        make_lnk(
            out,
            icon_path,
            launcher_browser,
            args=appid,
            appid=appid
            + "B",  # use a separate AppID so the browser launcher can be pinned separately from terminal mode
            description=f"Start {program_name} with the browser terminal.",
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
            description=f"Start {program_name} without opening a terminal window.",
        )

    # Shortcut: stop program started by any generated launcher mode
    if stop_running_shortcut_name not in ["", False, None]:
        out = shortcut_output_dir + "\\" + sanitize_filename(stop_running_shortcut_name) + ".lnk"
        make_lnk(out, stop_icon_path, launcher_stop, description=f"Stop running {program_name} processes.")

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
            description=f"Open the {program_name} settings file.",
        )


if __name__ == "__main__":
    try:
        main()
        print()
        print(f"Shortcut(s) created in: {shortcut_output_dir}")
        print()
        print("=============================")
        input("[Success] Press enter to exit")
        close_terminal()
    except Exception as e:
        print_traceback(f"[Error] {e}", add_press_enter_to_exit=True)
