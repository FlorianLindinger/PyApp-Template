import os


def make_abs(x: str) -> str:
    return os.path.normpath(_file_dir + x)


def get_dir(x: str) -> str:
    return os.path.dirname(x)


_file_dir: str = get_dir(os.path.normpath(__file__)) + "\\"

# =======================
# define variables

developer_settings_path = make_abs(
    "..\\..\\developer_settings.py"
)  # kind of unsused since scripts expect developer_settings to be at root for import

portable_python_installer_path = make_abs("..\\general_scripts\\create_portable_python.bat")
portable_venv_creator_path = make_abs("..\\general_scripts\\create_portable_venv.bat")

py_env_folder_path = make_abs("..\\..\\py_env")

backend_python_exe_path = make_abs("..\\P\\P.exe")

script_wrapper_path = make_abs("script_wrapper.py")

python_scripts_folder_path = make_abs("..\\..\\")
icon_path = make_abs("..\\..\\icons\\icon.ico")

compiled_terminal_path = make_abs("..\\terminal_emulator\\compiled\\run.exe")
uncompiled_terminal_path = make_abs("..\\terminal_emulator\\terminal_emulator.py")

process_id_file_path = make_abs("..\\..\\..\\currently_running_without_terminal_id.pid")

default_packages_file_path = make_abs("..\\..\\developer_tools\\!DEFAULT_PYHON_PACKAGES.txt")
excluded_folders_for_package_search = ["do_not_change", "py_env", "icons", "developer_tools", "__pycache__"]
# required_packages_output_file_path = make_abs("..\\..\\developer_tools\\found_required_python_packages.txt")
auto_search_required_packages_output_file_path = make_abs("..\\..\\developer_tools\\auto_found_required_python_packages.txt")
magic_phrase_in_default_packages_path_that_triggers_search = "# [Info] If this exact line is ontop and no other packages are defined below, it will automatically determine needed packages for the python code and add results to this file below."


# =======================
# process variables

developer_settings_dir = get_dir(developer_settings_path)

if python_scripts_folder_path != "" and python_scripts_folder_path[-1] != "\\":
    python_scripts_folder_path += "\\"

python_dist_path = py_env_folder_path + "\\py_dist"
venv_dir_path = py_env_folder_path + "\\virt_env"
venv_exe_path = venv_dir_path + "\\Portable_Scripts\\python.bat"

python_exe_path = os.path.normpath(python_dist_path + "\\python.exe")
relative_venv_to_python_dist = os.path.relpath(python_dist_path, get_dir(venv_dir_path))

# =======================
# common code


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
            import signal #noqa
            os.kill(os.getppid(), signal.SIGTERM) # kills even terminal launched by cmd and terminal from script calling this script
            
except Exception:
    import sys

    print('Failed during setup of rich traceback. Is "rich" package installed?')
    print("Press enter to exit")
    input()
    sys.exit(1)
