"""Experimental developer settings kept for future launcher work."""

taskbar_flashing_on_success = False
taskbar_flashing_on_failure = True
taskbar_flashing_on_crash = True
# flashing overrides highlight:
taskbar_highlight_on_success = True
taskbar_highlight_on_failure = True
taskbar_highlight_on_crash = True

send_Windows_notification_on_success = False
send_Windows_notification_on_failure = True
send_Windows_notification_on_crash = True

foreground_after_success = False
foreground_after_failure = False
foreground_after_crash = False
foreground_after_KeyBoardInterrupt = False

flash_in_taskbar_after_success = False
flash_in_taskbar_after_failure = True
flash_in_taskbar_after_crash = True
flash_in_taskbar_after_KeyBoardInterrupt = True

open_main_py_after_success = False
open_main_py_after_failure = False
open_main_py_after_crash = False
open_main_py_after_KeyBoardInterrupt = False

print_message_after_success: str | None = None
print_message_after_failure: str | None = None
print_message_after_crash: str | None = None
print_message_after_KeyBoardInterrupt: str | None = None

windows_notification_after_success: str | None = None
windows_notification_after_failure: str | None = None
windows_notification_after_crash: str | None = None
windows_notification_after_KeyBoardInterrupt: str | None = None

terminal_emulator_shortcut_name: str | None = f"{program_name} (Terminal Emulator)"

enable_log_for_terminal_emulator_start = True
enable_log_for_browser_start = True

# ---------------------------
# ---- Terminal Emulator ----
# ---------------------------

terminal_needs_input = True  # to en/disable the input box
dark_mode: bool | None = True  # None = Windows dark setting
stylesheet_path: str | None = "terminal_stylesheet.py"  # None = default stylesheet settings
button_settings: None | list[tuple[str, dict[str, bool]]] = [  # None = default button settings
    # ("button_name", {"visible"/"clickable"/"pinned"/"starting_state": bool , ...}),
    ("show_input", {"pinned": False, "starting_state": True}),
    ("autoscroll", {"starting_state": True}),
    ("foreground_on_print", {"pinned": False}),
    ("highlight_on_print", {"pinned": False}),
    ("confirm_close", {"pinned": False}),
    ("restart", {}),
    ("clear", {}),
    ("stop", {"visible": True}),
    ("to_tray", {"clickable": True}),
    ("open_script", {"pinned": False}),
]

# -----------------
# ---- Browser ----
# -----------------
