# todo: docstring

# ====================================

import os
import shutil
import subprocess
import sys
import time

try:
    # =============================
    # imports packages and common variables and developer settings
    # =============================

    from developer_settings import (
        close_on_failure,
        close_on_python_interpreter_crash,
        close_on_success,
        dark_mode,
        enable_log_for_no_terminal_start,
        enable_log_for_terminal_start,
        input_prepend,
        install_tests,
        install_tkinter,
        install_tools,
        log_file_date_append_format,
        log_path_rel_to_wdir,
        log_timestamp_format,
        overwrite_log,
        print_timestamp_format,
        python_code_name,
        python_version,
        script_after_python_interpreter_crash_name,
        start_in_shortcut_folder,
        stylesheet_path,
        terminal_bg_color,
        terminal_needs_input,
        terminal_text_color,
        use_fancy_terminal,
        use_faulthandler,
        use_global_python,
        use_uncompiled_terminal_emulator_and_run_it_in_global,  # noqa
    )
    from developer_settings import (
        program_name as title,
    )
    from do_not_change.specific_scripts.common_code import input_warn, print_traceback, print_warn
    from do_not_change.specific_scripts.common_variables import (
        browser_terminal_path,
        compiled_terminal_path,
        default_packages_file_path,
        developer_settings_dir,
        developer_settings_path,
        excluded_folders_for_package_search,
        icon_path,
        needed_packages_output_file_path,
        portable_python_installer_path,
        portable_venv_creator_path,
        process_id_file_path,
        py_env_folder_path,
        python_dist_path,
        python_exe_path,
        python_scripts_folder_path,
        relative_venv_to_python_dist,
        script_wrapper_path,
        uncompiled_terminal_path,
        variable_in_default_packages_path_that_triggers_search_if_true,
        venv_dir_path,
        venv_exe_path,
    )

    # =============================
    # process imports
    # =============================

    if script_after_python_interpreter_crash_name in [None, False]:
        script_after_interpreter_crash_path = ""
    else:
        script_after_interpreter_crash_path = python_scripts_folder_path + script_after_python_interpreter_crash_name
        if not os.path.exists(script_after_interpreter_crash_path):
            raise FileNotFoundError(
                f'[Error] Python after crash script not found at "{script_after_interpreter_crash_path}"'
            )
    if close_on_python_interpreter_crash == True and script_after_interpreter_crash_path != "":
        raise ValueError(
            f'[Error] Either choose close_on_python_interpreter_crash = False or script_after_interpreter_crash_path not in [None,"",False] in developer settings at "{developer_settings_path}"'
        )

    script_path: str = python_scripts_folder_path + python_code_name
    # raise error if script not found
    if not os.path.exists(script_path):
        raise FileNotFoundError(f'[Error] Python script not found at "{script_path}"')

    if use_global_python == True:
        python_exe_for_script_path = "py"
    else:
        python_exe_for_script_path = venv_exe_path

    if start_in_shortcut_folder == True:
        wdir_is_script_dir = False
    else:
        wdir_is_script_dir = True

    if log_path_rel_to_wdir in [None, False, ""]:
        log_path = ""
    else:
        if wdir_is_script_dir:
            log_path = os.path.join(os.path.dirname(script_path), log_path_rel_to_wdir)
        else:
            log_path = os.path.join(os.getcwd(), log_path_rel_to_wdir)
    if (enable_log_for_terminal_start != False or enable_log_for_no_terminal_start != False) and log_path == "":
        raise ValueError(
            f'[Error] log_path_rel_to_wdir in [False,None,""] in developer settings at "{developer_settings_path}" prevents log creation which is wanted by the settings enable_log_for_terminal_start or enable_log_for_no_terminal_start being True.'
        )

    if dark_mode is None:
        dark_mode = "auto"
    elif dark_mode is True:
        dark_mode = "1"
    elif dark_mode is False:  # type:ignore
        dark_mode = "0"

    if stylesheet_path in [False, None]:
        stylesheet_path = ""
    else:
        if not os.path.isabs(stylesheet_path):
            stylesheet_path = os.path.join(developer_settings_dir, stylesheet_path)

    if python_version in [None, False]:
        python_version = ""
    if log_file_date_append_format in [None, False]:
        log_file_date_append_format = ""
    if log_timestamp_format in [None, False]:
        log_timestamp_format = ""
    if print_timestamp_format in [None, False]:
        print_timestamp_format = ""
    if input_prepend in [None, False]:
        input_prepend = ""
    if terminal_bg_color in [None, False]:
        terminal_bg_color = ""
    if terminal_text_color in [None, False]:
        terminal_text_color = ""

    # =============================
    # helper functions
    # =============================

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

    def get_folder_size(folder: str | os.PathLike[str]) -> int:
        total = 0
        for root, _dirs, files in os.walk(folder):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    if os.path.isfile(path):
                        total += os.path.getsize(path)
                except (OSError, PermissionError):
                    # Skip unreadable files when estimating size.
                    pass
        return total

    def is_filesystem_root(path: str) -> bool:
        return os.path.abspath(path) == os.path.abspath(os.path.join(path, os.pardir))

    def delete_folder_safe(
        target: str | os.PathLike[str],
        *,
        prompt_message="Delete this folder? [y/n]: ",
        allowed_base: str | os.PathLike[str],
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

        target_path = os.path.realpath(os.path.abspath(os.fspath(target)))
        base_path = os.path.realpath(os.path.abspath(os.fspath(allowed_base)))

        if not os.path.exists(base_path):
            raise FileNotFoundError(f"Allowed base does not exist: {base_path}")

        if not os.path.isdir(base_path):
            raise NotADirectoryError(f"Allowed base is not a directory: {base_path}")

        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Target does not exist: {target_path}")

        if not os.path.isdir(target_path):
            raise NotADirectoryError(f"Target is not a directory: {target_path}")

        if is_filesystem_root(target_path):
            raise ValueError(f"Refusing to delete filesystem root: {target_path}")

        if os.path.normcase(target_path) == os.path.normcase(base_path):
            raise ValueError("Refusing to delete the allowed base directory itself")

        try:
            common_path = os.path.commonpath([base_path, target_path])
        except ValueError as exc:
            raise ValueError(
                f"Refusing to delete directory outside allowed base.\nTarget: {target_path}\nAllowed base: {base_path}"
            ) from exc

        if os.path.normcase(common_path) != os.path.normcase(base_path):
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
                return False

        shutil.rmtree(target_path)
        if not os.path.exists(target_path):
            return True
        else:
            return False

    def create_portable_python():

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
                    "1" if install_tkinter else "0",
                    "1" if install_tests else "0",
                    "1" if install_tools else "0",
                    "0",  # don't install docs
                ],
                check=True,
            )
        except Exception as e:
            print_traceback(f"[Error] Portable Python installation failed: {e}", add_press_enter_to_exit=True)

        if not os.path.exists(python_exe_path):
            print_traceback(
                f'[Error] Portable Python installation did not produce expected file at "{python_exe_path}"',
                add_press_enter_to_exit=True,
            )

    def recreate_portable_venv():
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
            print_traceback(
                f"[Error] Creation of portable virtual environment failed: {e}", add_press_enter_to_exit=True
            )

        if not os.path.exists(venv_exe_path):
            print_traceback(
                f'[Error] Creation of portable virtual environment did not produce expected file at "{venv_exe_path}"',
                add_press_enter_to_exit=True,
            )

    def install_packages(path):

        if not os.path.exists(path):
            raise FileNotFoundError(f'[Error] Packages file not found at "{path}"')

        # check if default_packages_file_path empty:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        for l in lines:
            l = l.strip()
            if l != "" and not l.startswith("#"):
                has_package = True
                break
        else:
            has_package = False

        if has_package == True:
            print()
            print("=" * 20)
            print("Installing packages:")
            print("-" * 20)
            subprocess.run(  # noqa
                [
                    venv_exe_path,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    path,
                    "--disable-pip-version-check",
                ],
                check=True,
            )
            print("-" * 20)
            print("Finished installing packages")
            print("=" * 20)
            print()
        else:
            print()
            print("=" * 20)
            print("No packages to install.")
            print("=" * 20)
            print()

    def read_search_phrase_state() -> bool | None:
        with open(default_packages_file_path) as f:
            lines = f.readlines()
        if variable_in_default_packages_path_that_triggers_search_if_true in lines[0]:
            val = (
                lines[0]
                .replace(variable_in_default_packages_path_that_triggers_search_if_true, "")
                .replace("=", "")
                .replace("#", "")
                .strip()
                .lower()
            )
            if val == "true":
                return True
            elif val == "false":
                return False
            else:
                return None
        else:
            return None

    def save_current_packages_as_default(search_phrase_state=None):
        """search_phrase_state==None means that is leaves the current state in the default packages file."""

        with open(default_packages_file_path, "w", encoding="utf-8") as file:  # override default packages file
            if search_phrase_state is None:
                search_phrase_state = read_search_phrase_state()
            file.write(f"{variable_in_default_packages_path_that_triggers_search_if_true} = {search_phrase_state}\n\n")
            file.flush()  # otherwise this line appears after subprocess output
            subprocess.run(  # noqa
                [
                    venv_exe_path,
                    "-m",
                    "pip",
                    "freeze",
                    "--local",
                ],
                stdout=file,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

    def delete_venv():
        if os.path.exists(venv_dir_path):
            try:
                delete_folder_safe(
                    venv_dir_path,
                    prompt_for_confirmation=False,
                    allowed_base=python_scripts_folder_path,  # a suitable path that is independent setting to venv_dir_path
                )
            except Exception as e:
                print(f"[Error] Failed to delete virtual environment: {e}.")
                print(f'Delete manually after confirming it is the correct one at "{venv_dir_path}" and restart.')
                print("Pressed Enter to exit.")
                input()

    def delete_python_distro():
        if os.path.exists(python_dist_path):
            try:
                delete_folder_safe(
                    python_dist_path,
                    prompt_for_confirmation=False,
                    allowed_base=python_scripts_folder_path,  # a suitable path that is independent setting to python_dist_path
                )
            except Exception as e:
                print(f"[Error] Failed to delete Python distribution: {e}.")
                print(f'Delete manually after confirming it is the correct one at "{python_dist_path}" and restart.')
                print("Pressed Enter to exit.")
                input()

    def reinstall_python_distro_if_nonexistent_or_incorrect_version():

        if not os.path.exists(python_exe_path):  # python distribution not existing case
            # python distribution not found case -> install python and delete venv if exists to renew it

            print(
                "\n" * 5
            )  # because the batch called in create_portable_python() hides the top of the terminal in between.
            print("[Info] Python distribution not found. Installing portable Python and creating virtual environment:")

            delete_python_distro()
            create_portable_python()
            delete_venv()
        else:  # python distribution existing case
            match = check_python_version(target_version=python_version, exe_path=python_exe_path)

            if match:  # correct python version case
                if not os.path.exists(venv_exe_path):
                    print("[Info] Virtual environment not found. Creating portable virtual environment:")
                    delete_venv()
            else:  # wrong python version case
                print(
                    "\n" * 3
                )  # because the batch called in create_portable_python() hides the top of the terminal in between.
                print(
                    "Installed Python version does not match target version. Reinstalling Python distribution and recreating virtual environment:"
                )
                delete_python_distro()
                create_portable_python()
                delete_venv()

    def save_requirements_of_root_folder_noVersion(output_path):

        searched_folder = python_scripts_folder_path
        excluded_folders = excluded_folders_for_package_search

        cmd = [
            sys.executable,
            "-m",
            "pipreqs.pipreqs",
            searched_folder,
            "--force",
            "--savepath",
            output_path,
            "--ignore",
            ",".join(excluded_folders),
            "--encoding",
            "utf-8",
            "--mode",
            "no-pin",
            "--no-follow-links",
        ]

        print()
        print("=" * 20)
        print("Start of finding required python packages")
        print("-" * 20)
        subprocess.run(cmd, check=True)  # noqa
        print("-" * 20)
        print(f'End of finding required python packages. Result: "{output_path}":\n')
        with open(output_path, encoding="utf-8") as file:
            contents = file.read()
        print(contents)
        print("=" * 20)
        print()

    # =============================
    # main function
    # =============================

    def main() -> None:
        global use_uncompiled_terminal_emulator_and_run_it_in_global

        # ======================
        # process args

        app_id = sys.argv[1]
        launch_mode = sys.argv[2]
        create_terminal = launch_mode == "1"  # inputs are 0 or 1
        create_browser_terminal = launch_mode == "browser"

        # it overrides use_uncompiled_terminal_emulator_and_run_it_in_global from developer_settings
        if len(sys.argv) > 3:  # any arg means True. Used for debug before compiling terminal emulator
            use_uncompiled_terminal_emulator_and_run_it_in_global = True

        # ======================
        # potentially auto search for required packages

        if use_global_python == False:
            # auto find packages if none given and magic phrase present
            if read_search_phrase_state():
                if os.path.exists(needed_packages_output_file_path):
                    os.remove(needed_packages_output_file_path)
                try:
                    save_requirements_of_root_folder_noVersion(needed_packages_output_file_path)
                except Exception as e:
                    print_traceback(
                        f"[Error] Failed to auto determine packages (do you have internet?): {e}",
                        add_press_enter_to_exit=True,
                    )

                if os.path.exists(needed_packages_output_file_path):
                    delete_venv()
                    reinstall_python_distro_if_nonexistent_or_incorrect_version()
                    recreate_portable_venv()
                    install_packages(needed_packages_output_file_path)
                    save_current_packages_as_default(search_phrase_state=False)
                else:
                    print_warn("[Error] Failed to auto determine required Python packages.")
                    input_warn("Aborting. Press enter to exit")

        # ======================
        # setup venv: install python distribution if not existatant and venv. Also recreate if the target python version is not dist version.

        if use_global_python == False:
            reinstall_python_distro_if_nonexistent_or_incorrect_version()  # deletes venv for change/creation of distro
            if not os.path.exists(venv_dir_path):
                recreate_portable_venv()
                install_packages(default_packages_file_path)

        # ======================
        # launch terminal

        if create_terminal or create_browser_terminal:
            effective_log_path = log_path if enable_log_for_terminal_start else ""
        else:
            effective_log_path = log_path if enable_log_for_no_terminal_start else ""

        args = [
            title,
            icon_path,
            app_id,
            "1" if wdir_is_script_dir else "0",
            "1" if close_on_python_interpreter_crash else "0",
            "1" if close_on_failure else "0",
            "1" if close_on_success else "0",
            print_timestamp_format,
            effective_log_path,
            log_timestamp_format,
            "1" if overwrite_log else "0",
            log_file_date_append_format,
            script_after_interpreter_crash_path,
            input_prepend,
            process_id_file_path,
        ]

        if use_faulthandler == True:
            extra_args = ["-X", "faulthandler"]
        else:
            extra_args = []

        if create_browser_terminal == True:
            proc = subprocess.Popen(  # noqa:S603 #type:ignore
                [
                    python_exe_for_script_path,
                    *extra_args,
                    browser_terminal_path,
                    script_path,
                    python_exe_for_script_path,
                    *args,
                ],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        elif (use_fancy_terminal == True) and (create_terminal == True):
            # run in termnial emulator

            args += [
                "1" if terminal_needs_input else "0",
                stylesheet_path,
                dark_mode,
                "1" if use_faulthandler else "0",
            ]

            if use_uncompiled_terminal_emulator_and_run_it_in_global == True:  # Meant for debugging terminal
                proc = subprocess.Popen(  # noqa:S603 #type:ignore
                    ["py", *extra_args, uncompiled_terminal_path, script_path, python_exe_for_script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                # run and wait (using the compiled terminal emulator)
                proc = subprocess.Popen(  # noqa:S603 #type:ignore
                    [compiled_terminal_path, script_path, python_exe_for_script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

        else:  # run in Windows terminal or no window
            # script_wrapper_path need additional args
            args += [
                terminal_bg_color + terminal_text_color,  # type:ignore
                "1" if create_terminal else "0",
            ]

            if create_terminal == True:  # run in windows terminal and don't wait
                proc = subprocess.Popen(  # noqa:S603 #type:ignore
                    [python_exe_for_script_path, *extra_args, script_wrapper_path, script_path, *args],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:  # run without terminal but create one on crash and don't wait
                proc = subprocess.Popen(  # noqa:S603 #type:ignore
                    [python_exe_for_script_path, *extra_args, script_wrapper_path, script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

        # wait shortly and check & handle if script immediately failed
        time.sleep(0.8)
        error_code = proc.poll()
        if error_code is not None and proc.poll() != 0:
            print("=" * 20)
            print("[Error] Failed launching terminal-emulator/script-wrapper. Probably a syntax error in the script:")
            if (use_fancy_terminal == True) and (create_terminal == True):
                if use_uncompiled_terminal_emulator_and_run_it_in_global:
                    print(uncompiled_terminal_path)
                else:
                    print(compiled_terminal_path)
            else:
                print(script_wrapper_path)
            print("-" * 20)
            input("[Error (see above)] Press enter to exit.")
            os._exit(error_code)

    # =============================
    # execution of main function
    # =============================

    if __name__ == "__main__":
        try:
            main()
            sys.exit(0)
        except Exception as e:
            print_traceback(f"[Error] Failed to launch the program: {e}", add_press_enter_to_exit=True)

except Exception as e:
    import os
    import traceback

    print()
    print()
    print("=" * 20)
    print(f"[Error] Failed during start of program: {e}")
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("[Error (see above)] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
