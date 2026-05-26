
terminal_emulator_shortcut_name: str | None = f"{program_name} (Terminal Emulator)"

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