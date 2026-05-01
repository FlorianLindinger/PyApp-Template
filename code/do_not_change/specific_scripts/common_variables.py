import os


def make_abs(x: str) -> str:
    return os.path.normpath(_file_dir + x)


def get_dir(x: str) -> str:
    return os.path.dirname(x)


_file_dir: str = get_dir(os.path.normpath(__file__)) + "\\"

# ========================
# === define variables ===
# ========================

developer_settings_path = make_abs(
    "..\\..\\developer_settings.py"
)  # kind of unsused since scripts expect developer_settings to be at root for import

portable_python_installer_path = make_abs("..\\general_scripts\\create_portable_python.bat")
portable_venv_creator_path = make_abs("..\\general_scripts\\create_portable_venv.bat")

py_env_folder_path = make_abs("..\\..\\py_env")

script_wrapper_path = make_abs("script_wrapper.py")

python_scripts_folder_path = make_abs("..\\..\\")
icon_path = make_abs("..\\..\\icons\\icon.ico")

compiled_terminal_path = make_abs("..\\terminal_emulator\\compiled\\run.exe")
uncompiled_terminal_path = make_abs("..\\terminal_emulator\\terminal_emulator.py")

process_id_file_path = make_abs("..\\..\\..\\currently_running.pid")

default_packages_file_path = make_abs("..\\..\\developer_tools\\!DEFAULT_PYHON_PACKAGES.txt")
excluded_folders_for_package_search = ["do_not_change", "py_env", "icons", "developer_tools", "__pycache__"]

variable_in_default_packages_path_that_triggers_search_if_true = (
    "# auto_find_required_packages_here_and_reset_venv_to_them"
)

developer_tools_folder_path = make_abs("..\\..\\developer_tools\\")

determined_current_packages_file_path = make_abs(developer_tools_folder_path + "determined_current_packages.txt")

needed_packages_output_file_path = make_abs(developer_tools_folder_path + "auto_found_required_packages.txt")

# =========================
# === process variables ===
# =========================

developer_settings_dir = get_dir(developer_settings_path)

if python_scripts_folder_path != "" and python_scripts_folder_path[-1] != "\\":
    python_scripts_folder_path += "\\"
if developer_tools_folder_path != "" and developer_tools_folder_path[-1] != "\\":
    developer_tools_folder_path += "\\"

python_dist_path = py_env_folder_path + "\\py_dist"
venv_dir_path = py_env_folder_path + "\\virt_env"
venv_exe_path = venv_dir_path + "\\Portable_Scripts\\python.bat"

python_exe_path = os.path.normpath(python_dist_path + "\\python.exe")
relative_venv_to_python_dist = os.path.relpath(python_dist_path, get_dir(venv_dir_path))

# ====================
# === common code ====
# ====================

# colored print and input

ANSI_WARN = "\x1b[1;37;41m"  # white text, red bg, bold
ANSI_SUCCESS = "\x1b[1;37;42m"  # white text, green bg, bold
ANSI_RESET = "\033[0m"


def print_warn(msg, sep: str | None = " ", end: str | None = "\n"):
    print(f"{ANSI_WARN}{msg}{ANSI_RESET}", sep=sep, end=end)


def input_warn(msg):
    input(f"{ANSI_WARN}{msg}{ANSI_RESET}")


def input_success(msg):
    input(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}")


# colored traceback related
try:
    import rich.box
    import rich.console
    import rich.panel
    import rich.text
    import rich.traceback

    # enable colored traceback (needed especially before python 3.13)
    rich.traceback.install(show_locals=False)

    def print_traceback(message="Error", add_press_enter_to_exit=False) -> None:
        import sys  # noqa

        exc_type, exc_value, tb = sys.exc_info()
        if exc_type is None or exc_value is None:
            rich.console.Console().print(
                "[yellow][Warning] Running print_traceback function without active exception.[/yellow]"
            )
            if add_press_enter_to_exit:
                rich.console.Console().print("[red]Press enter to exit[/red]")
        else:
            panel = rich.panel.Panel(
                rich.traceback.Traceback.from_exception(
                    exc_type,
                    exc_value,
                    tb,
                    show_locals=False,
                ),
                title=rich.text.Text(message, style="bold red on white"),
                title_align="left",
                subtitle=rich.text.Text("Press Enter to exit", style="bold red on white")
                if add_press_enter_to_exit
                else None,
                subtitle_align="left",
                box=rich.box.HEAVY,
                border_style="bold red",
                padding=(1, 2),
                expand=False,
            )
            rich.console.Console().print(panel)

        if add_press_enter_to_exit:
            input()
            import signal  # noqa

            os.kill(
                os.getppid(), signal.SIGTERM
            )  # kills even terminal launched by cmd and terminal from script calling this script

except Exception:
    import os

    print(
        r'Failed during setup of rich traceback. Is "rich" package installed in the code\do_not_change\python_packages folder?'
    )
    print("Press enter to exit")
    input()
    os._exit(1)
