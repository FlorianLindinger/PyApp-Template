# todo: docstring


try:
    # =============================
    # imports packages and common variables
    # =============================

    import os
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    from do_not_change.specific_scripts.common_variables import (
        backend_python_exe_path,
        compiled_terminal_path,
        developer_settings,
        file_dir,
        icon_path,
        portable_python_installer_path,
        portable_venv_creator_path,
        py_env_folder_path,
        python_dist_path,
        python_exe_path,
        python_scripts_folder_path,
        relative_venv_to_python_dist,
        script_wrapper_path,
        uncompiled_terminal_path,
        venv_dir_path,
        venv_exe_path,
    )

    # =============================
    # needed functions
    # =============================

    def error_print(message, max_wrapper_len=20, wrapper_symbol="=", red=False):
        msg_len = len(message)
        if msg_len > max_wrapper_len:
            msg_len = max_wrapper_len
        if red == True:
            print(f"\033[91m{wrapper_symbol * msg_len}")
        else:
            print(wrapper_symbol * msg_len)
        print(message)
        print(wrapper_symbol * msg_len)
        print(traceback.format_exc(), end="")
        if red == True:
            print(f"{wrapper_symbol * msg_len}\033[0m")
        else:
            print(wrapper_symbol * msg_len)

    def check_python_version(target_version: str | float, exe_path: str = "py") -> bool:
        """
        Return whether the Python executable at ``exe_path`` matches ``target_version``.

        Matching is prefix-based on proven version components:
        - If ``target_version`` is ``"3"``, any Python 3.x matches.
        - If ``target_version`` is ``"3.13"``, any Python 3.13.x matches.
        - If ``target_version`` is ``"3.13.2"``, only Python 3.13.2 matches.

        In other words, the executable's version only needs to match as far as
        ``target_version`` specifies.

        Returns:
        - ``True`` if ``exe_path`` is a valid Python executable and its version matches
        ``target_version`` up to the precision provided there.
        - ``False`` if ``exe_path`` is a valid Python executable but its version does not match.

        By default, ``exe_path="py"`` uses the global Python launcher that would also be
        chosen when running ``py`` in Command Prompt.
        """
        if isinstance(target_version, (float, int)):
            target_version = str(target_version)

        output = subprocess.check_output(  # noqa: S603
            [
                exe_path,
                "-c",
                "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
            ],
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()

        actual_parts = output.split(".")
        target_parts = target_version.strip().split(".")

        if (len(actual_parts) != 3) or (any(not part.isdigit() for part in actual_parts)):
            raise ValueError(
                f"Could not determine Python version from output: {output}. Expected format like '3.13.2'."
            )

        if not target_parts or any(not part.isdigit() for part in target_parts):
            raise ValueError(
                f"Invalid target_version format: {target_version}. Must be a string like '3', '3.13', or '3.13.2'."
            )

        return actual_parts[: len(target_parts)] == target_parts

    def input_red(msg):
        input(f"\033[91m{msg}\033[0m")

    def format_bytes(num_bytes) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(num_bytes)
        for unit in units:
            if size < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} {unit}"
                else:
                    return f"{size:.2f} {unit}"
            size /= 1024
        return f"{num_bytes} B"

    def get_folder_size(folder: Path) -> int:
        total = 0
        for p in folder.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except (OSError, PermissionError):
                # Skip unreadable files when estimating size.
                pass
        return total

    def delete_folder_safe(
        target: str | Path,
        *,
        prompt_message="Delete this folder? [y/n]: ",
        allowed_base: str | Path,
        prompt_for_confirmation=True,
    ):
        """
        Safely delete a folder after showing its size and prompting the user.

        Returns True if deleted, False if cancelled.

        Safety features:
        - resolves absolute paths
        - target must exist and be a directory
        - target must be inside allowed_base
        - refuses to delete allowed_base itself
        - refuses to delete filesystem roots
        - shows folder size before deletion
        - asks for confirmation
        """

        target_path = Path(target).resolve()
        base_path = Path(allowed_base).resolve()

        if not base_path.exists():
            raise FileNotFoundError(f"Allowed base does not exist: {base_path}")

        if not base_path.is_dir():
            raise NotADirectoryError(f"Allowed base is not a directory: {base_path}")

        if not target_path.exists():
            raise FileNotFoundError(f"Target does not exist: {target_path}")

        if not target_path.is_dir():
            raise NotADirectoryError(f"Target is not a directory: {target_path}")

        if target_path == target_path.anchor:
            raise ValueError(f"Refusing to delete filesystem root: {target_path}")

        if target_path == base_path:
            raise ValueError("Refusing to delete the allowed base directory itself")

        if base_path not in target_path.parents:
            raise ValueError(
                f"Refusing to delete directory outside allowed base.\nTarget: {target_path}\nAllowed base: {base_path}"
            )

        size_bytes = get_folder_size(target_path)
        size_text = format_bytes(size_bytes)

        if prompt_for_confirmation:
            print()
            print("Folder deletion request:")
            print(f"Folder: {target_path}")
            # print(f"Allowed base: {base_path}")
            print(f"Folder size: {size_text}")
            print()
            answer = input(prompt_message).strip().lower()
            if answer not in {"y", "yes"}:
                print("Cancelled folder deletion.")

        shutil.rmtree(target_path)

    def create_portable_python():

        python_version = getattr(developer_settings, "python_version", "") or ""

        # find what optional subparts of full python to install
        install_tkinter = "1" if getattr(developer_settings, "install_tkinter", True) else "0"
        install_tests = "1" if getattr(developer_settings, "install_tests", False) else "0"
        install_tools = "1" if getattr(developer_settings, "install_tools", False) else "0"
        install_docs = "0"

        # run a batch file to install portable python and wait for finish
        try:
            subprocess.run(  # noqa:S603
                [
                    "cmd",
                    "/c",
                    "call",
                    portable_python_installer_path,
                    python_version,
                    py_env_folder_path,  # scripts adds py_dist
                    install_tkinter,
                    install_tests,
                    install_tools,
                    install_docs,
                ],
                check=True,
            )
        except Exception as e:
            error_print(f"[Error] Portable Python installation failed: {e}")
            input("Press Enter to exit.")
            sys.exit(1)

        if not os.path.exists(python_exe_path):
            error_print(f'[Error] Portable Python installation did not produce expected file at "{python_exe_path}"')
            input("Press Enter to exit.")
            sys.exit(1)

    def create_portable_venv():
        try:
            # run a batch file to install portable python and wait for finish
            subprocess.run(  # noqa:S603
                [
                    "cmd",
                    "/c",
                    "call",
                    portable_venv_creator_path,
                    py_env_folder_path,  # scripts adds py_venv
                    relative_venv_to_python_dist,
                ],
                check=True,
            )
        except Exception as e:
            error_print(f"[Error] Creation of portable virtual environment failed: {e}")
            input("Press Enter to exit.")
            sys.exit(1)

        if not os.path.exists(venv_exe_path):
            error_print(
                f'[Error] Creation of portable virtual environment did not produce expected file at "{venv_exe_path}"'
            )
            input("Press Enter to exit.")
            sys.exit(1)

    def delete_venv():
        if os.path.exists(venv_dir_path):
            try:
                delete_folder_safe(
                    venv_dir_path, prompt_for_confirmation=False, allowed_base=Path(file_dir).parent.parent
                )
            except Exception as e:
                print(f"[Error] Failed to delete virtual environment: {e}.")
                print(f'Delete manually after confirming it is the correct one at "{venv_dir_path}" and restart.')
                print("Pressed Enter to exit.")
                input()

    def delete_python_dist():
        if os.path.exists(python_dist_path):
            try:
                delete_folder_safe(
                    python_dist_path, prompt_for_confirmation=False, allowed_base=Path(file_dir).parent.parent
                )
            except Exception as e:
                print(f"[Error] Failed to delete Python distribution: {e}.")
                print(f'Delete manually after confirming it is the correct one at "{python_dist_path}" and restart.')
                print("Pressed Enter to exit.")
                input()

    def setup_venv():
        """Makes sure the venv exists and has correct version, if not it creates it. It does not activate it as one is expected to run the venv exe"""

        wanted_python_version = getattr(developer_settings, "python_version", "")

        if not os.path.exists(python_exe_path):
            # python distribution not found case -> install python and delete venv if exists to renew it

            print(
                "\n" * 5
            )  # because the batch called in create_portable_python() hides the top of the terminal in between.
            print("[Info] Python distribution not found. Installing portable Python and creating virtual environment:")

            delete_python_dist()
            create_portable_python()
            delete_venv()
            print("[Info] Creating virtual environment:")
            create_portable_venv()

        else:  # python distribution existing case
            match = check_python_version(target_version=wanted_python_version, exe_path=python_exe_path)

            if match:
                if not os.path.exists(venv_exe_path):
                    print("[Info] Virtual environment not found. Creating portable virtual environment:")
                    delete_venv()
                    create_portable_venv()
            else:
                print(
                    "\n" * 3
                )  # because the batch called in create_portable_python() hides the top of the terminal in between.
                print(
                    "Installed Python version does not match target version. Reinstalling Python distribution and recreating virtual environment:"
                )
                delete_python_dist()
                create_portable_python()
                delete_venv()
                print("[Info] (Re)Creating virtual environment:")
                create_portable_venv()

    # =============================
    # main function
    # =============================

    def main() -> None:

        # process args

        if len(sys.argv) > 1:
            app_id = sys.argv[1]
        else:
            app_id = ""

        if len(sys.argv) > 2:
            create_terminal = sys.argv[2] == "1"  # inputs are 0 or 1
        else:
            create_terminal = True

        # ======================
        # setup venv: install python distribution if not existatant and venv. Also recreate if the target python version is not dist version

        setup_venv()

        # =============================
        # import and process developer_settings

        use_fancy_terminal = getattr(developer_settings, "use_fancy_terminal", True)
        terminal_needs_input = getattr(developer_settings, "terminal_needs_input", True)
        close_on_success = getattr(developer_settings, "close_on_success", True)
        close_on_crash = getattr(developer_settings, "close_on_crash", False)
        close_on_failure = getattr(developer_settings, "close_on_failure", False)
        use_uncompiled_terminal_and_run_it_in_global = getattr(
            developer_settings, "use_uncompiled_terminal_and_run_it_in_global", False
        )
        wdir_is_script_dir = not getattr(developer_settings, "start_in_shortcut_folder", False)
        use_global_python = getattr(developer_settings, "use_global_python", False)
        log_even_with_terminal = getattr(developer_settings, "log_even_with_terminal", True)
        restart_main_code_on_crash = getattr(developer_settings, "restart_main_code_on_crash", False)

        title = getattr(developer_settings, "program_name", "Terminal")
        log_path_rel_to_wdir = getattr(developer_settings, "log_path_rel_to_wdir", "..\\log.txt")
        terminal_bg_color = getattr(developer_settings, "terminal_bg_color", "0")
        terminal_text_color = getattr(developer_settings, "terminal_text_color", "F")
        terminal_colors = terminal_bg_color + terminal_text_color

        fancy_terminal_stylesheet = getattr(developer_settings, "fancy_terminal_stylesheet", "")
        fancy_terminal_accent_color_hex = getattr(developer_settings, "fancy_terminal_accent_color_hex", "")
        dark_mode = getattr(developer_settings, "dark_mode", "1")

        script_path = python_scripts_folder_path + developer_settings.python_code_name
        # raise error if script not found
        if not os.path.exists(script_path):
            raise FileNotFoundError(f'[Error] Python script not found at "{script_path}"')

        if use_global_python == True:
            python_exe_for_script_path = "py"
        else:
            # raise error if python or script or settings not found
            if not os.path.exists(venv_exe_path):
                raise FileNotFoundError(f'[Error] Python executable not found at "{venv_exe_path}"')
            python_exe_for_script_path = venv_exe_path

        after_python_crash_code_name = getattr(developer_settings, "after_python_crash_code_name", "")
        if after_python_crash_code_name != "":
            after_python_crash_code_path = python_scripts_folder_path + after_python_crash_code_name
            if not os.path.exists(after_python_crash_code_path):
                after_python_crash_code_path = ""
        else:
            after_python_crash_code_path = ""

        # ======================
        # launch terminal

        args = [
            title,
            icon_path if icon_path else "",
            app_id,
            "1" if wdir_is_script_dir else "0",
            "1" if close_on_crash else "0",
            "1" if close_on_failure else "0",
            "1" if close_on_success else "0",
            log_path_rel_to_wdir,
            # restart_main_code_on_crash,
            # after_python_crash_code_path
        ]

        if (use_fancy_terminal == True) and (create_terminal == True):
            # run in termnial emulator

            # terminal emulator need additional arg python_exe_for_script_path
            args += [
                fancy_terminal_accent_color_hex,
                "1" if terminal_needs_input else "0",
                fancy_terminal_stylesheet,
                dark_mode,
            ]

            if use_uncompiled_terminal_and_run_it_in_global == True:
                subprocess.Popen(  # noqa:S603
                    ["pyw", uncompiled_terminal_path, script_path, python_exe_for_script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                # run and wait (using the compiled terminal emulator)
                subprocess.Popen(  # noqa:S603
                    [compiled_terminal_path, script_path, python_exe_for_script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

        else:
            # run in Windows terminal or no window

            # script_wrapper_path need addition args
            args += [terminal_colors, "1" if create_terminal else "0", backend_python_exe_path]

            # launch script in wrapper that handles:
            #   errors
            #   return
            #   icon setting
            #   terminal-renaming
            #   working dir setting
            #   app-id setting
            #   closer or keep open logic on finish/error/fail
            #   print in additional terminal for final print info if in no-terminal mode
            if create_terminal == True:  # run in windows terminal
                subprocess.Popen(  # noqa:S603
                    [python_exe_for_script_path, script_wrapper_path, script_path, *args],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:  # run without terminal but create one on crash.
                subprocess.Popen(  # noqa:S603
                    [python_exe_for_script_path, script_wrapper_path, script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

    # =============================
    # execution of main function
    # =============================

    if __name__ == "__main__":
        try:
            main()
            sys.exit(0)

        except Exception as e:
            error_print(f"[Error] Failed to launch the program: {e}", red=True)
            input_red("Press Enter to exit...")
            sys.exit(1)

except Exception as e:
    import sys
    import traceback

    print(f"[Error] Failed during start of program with error: {e}:")
    print("=" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("Press enter to exit")
    sys.exit(1)
