# todo: docstring

# ====================================

import os
import sys
from datetime import datetime, timezone

# ====================================
# add root dir for debug cases where this script is called on its own:
root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
# ====================================

from developer_settings import (
    classic_terminal_cols,
    classic_terminal_lines,
    close_on_crash,
    close_on_failure,
    close_on_success,
    dark_mode,
    input_prepend,
    log_input_prepend,
    log_path_rel_to_start_folder,
    log_print_prepend,
    modern_terminal_tab_color,
    open_log_file_after_crash,
    open_log_file_after_failure,
    open_log_file_after_success,
    overwrite_log,
    play_sound_on_crash,
    play_sound_on_failure,
    play_sound_on_success,
    print_prepend,
    program_name,
    python_version,
    send_Windows_notification_on_crash,
    send_Windows_notification_on_failure,
    send_Windows_notification_on_success,
    start_in_shortcut_folder,
    start_minimized,
    stylesheet_path,
    taskbar_flashing_on_crash,
    taskbar_flashing_on_failure,
    taskbar_flashing_on_success,
    taskbar_highlight_on_crash,
    taskbar_highlight_on_failure,
    taskbar_highlight_on_success,
    terminal_bg_color,
    terminal_text_color,
    use_global_python,
)
from DONT_CHANGE.specific_scripts.common_variables import (
    CORRECT_START_SIGNAL_FILE_PATH,
    developer_settings_dir,
    env_var_to_signal_startup_time_measurement,
    frontend_python_exe,
    icon_path,
    play_sound_on_crash_default,
    play_sound_on_failure_default,
    play_sound_on_success_default,
    process_id_file_path,
    python_code_path,
    start_time_dummy_main_script,
    windows_dir,
)

# ====================================
# process developer_settings settings

if os.environ.get(env_var_to_signal_startup_time_measurement):
    python_code_path = start_time_dummy_main_script

# raise error if script not found
if not os.path.exists(python_code_path):
    raise FileNotFoundError(f'[Error] Python script not found at "{python_code_path}"')

if use_global_python == True:
    python_exe_for_script_path = "py"
else:
    python_exe_for_script_path = frontend_python_exe

if start_in_shortcut_folder == True:
    wdir_is_script_dir = False
else:
    wdir_is_script_dir = True

if log_path_rel_to_start_folder in [None, False, ""]:
    log_path = ""
else:
    if wdir_is_script_dir:
        log_path = os.path.normpath(os.path.join(os.path.dirname(python_code_path), log_path_rel_to_start_folder))
    else:
        log_path = os.path.normpath(os.path.join(os.getcwd(), log_path_rel_to_start_folder))
    log_path = datetime.now(tz=timezone.utc).strftime(log_path)

if dark_mode is None:
    dark_mode = "auto"
elif dark_mode is True:
    dark_mode = "1"
elif dark_mode is False:  # type:ignore
    dark_mode = "0"
if stylesheet_path in [False, None, ""]:
    stylesheet_path = ""
else:
    if not os.path.isabs(stylesheet_path):
        stylesheet_path = os.path.normpath(developer_settings_dir + "\\" + stylesheet_path)

if python_version in [None, False, ""]:
    python_version = ""
if log_print_prepend in [None, False, ""]:
    log_print_prepend = ""
if log_input_prepend in [None, False, ""]:
    log_input_prepend = ""
if print_prepend in [None, False, ""]:
    print_prepend = ""
if input_prepend in [None, False, ""]:
    input_prepend = ""
if terminal_bg_color in [None, False, ""]:
    terminal_bg_color = ""
if terminal_text_color in [None, False, ""]:
    terminal_text_color = ""
if classic_terminal_cols in [None, False, ""]:
    classic_terminal_cols = ""
else:
    classic_terminal_cols = str(classic_terminal_cols)
if classic_terminal_lines in [None, False, ""]:
    classic_terminal_lines = ""
else:
    classic_terminal_lines = str(classic_terminal_lines)
if modern_terminal_tab_color in [None, False, ""]:
    modern_terminal_tab_color = ""

if play_sound_on_crash is True:
    play_sound_on_crash = play_sound_on_crash_default
elif play_sound_on_crash in [False, None, ""]:
    play_sound_on_crash = ""
elif not os.path.isabs(play_sound_on_crash):
    play_sound_on_crash = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_crash)
if play_sound_on_crash != "" and play_sound_on_crash[-4:] != ".wav":
    play_sound_on_crash += ".wav"
if play_sound_on_crash != "" and not os.path.exists(play_sound_on_crash):
    print(f"[Warning] Sound file does not exist: {play_sound_on_crash}")
if play_sound_on_success is True:
    play_sound_on_success = play_sound_on_success_default
elif play_sound_on_success in [False, None, ""]:
    play_sound_on_success = ""
elif not os.path.isabs(play_sound_on_success):
    play_sound_on_success = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_success)
if play_sound_on_success != "" and play_sound_on_success[-4:] != ".wav":
    play_sound_on_success += ".wav"
if play_sound_on_success != "" and not os.path.exists(play_sound_on_success):
    print(f"[Warning] Sound file does not exist: {play_sound_on_success}")
if play_sound_on_failure is True:
    play_sound_on_failure = play_sound_on_failure_default
elif play_sound_on_failure in [False, None, ""]:
    play_sound_on_failure = ""
elif not os.path.isabs(play_sound_on_failure):
    play_sound_on_failure = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_failure)
if play_sound_on_failure != "" and play_sound_on_failure[-4:] != ".wav":
    play_sound_on_failure += ".wav"
if play_sound_on_failure != "" and not os.path.exists(play_sound_on_failure):
    print(f"[Warning] Sound file does not exist: {play_sound_on_failure}")


args = [
    python_code_path,
    program_name,
    icon_path,
    # app_id,
    wdir_is_script_dir,
    close_on_crash,
    close_on_failure,
    close_on_success,
    print_prepend,
    log_path,
    log_print_prepend,
    overwrite_log,
    input_prepend,
    process_id_file_path,
    play_sound_on_success,
    send_Windows_notification_on_success,
    play_sound_on_failure,
    send_Windows_notification_on_failure,
    play_sound_on_crash,
    send_Windows_notification_on_crash,
    open_log_file_after_success,
    open_log_file_after_failure,
    open_log_file_after_crash,
    start_minimized,
    CORRECT_START_SIGNAL_FILE_PATH,
    log_input_prepend,
    ##########
    taskbar_flashing_on_crash,
    taskbar_flashing_on_failure,
    taskbar_flashing_on_success,
    taskbar_highlight_on_crash,
    taskbar_highlight_on_failure,
    taskbar_highlight_on_success,
]
