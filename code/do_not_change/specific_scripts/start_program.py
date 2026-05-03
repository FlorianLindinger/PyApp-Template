# todo: docstring

# ====================================

import os
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    # =============================
    # imports packages and common variables and developer settings
    # =============================

    from developer_settings import (
        button_settings,
        close_on_failure,
        close_on_python_interpreter_crash,
        close_on_success,
        dark_mode,
        enable_log_for_no_terminal_start,
        enable_log_for_terminal_start,
        input_prepend,
        log_path_rel_to_wdir,
        log_timestamp_format,
        overwrite_log,
        play_sound_on_failure,
        play_sound_on_python_interpreter_crash,
        play_sound_on_success,
        print_timestamp_format,
        python_code_name,
        python_version,
        script_after_python_interpreter_crash_name,
        send_Windows_notification_on_failure,
        send_Windows_notification_on_python_interpreter_crash,
        send_Windows_notification_on_success,
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
    from do_not_change.specific_scripts.common_code import (
        delete_venv,
        input_warn,
        install_packages,
        print_traceback,
        print_warn,
        read_search_phrase_state,
        recreate_portable_venv,
        reinstall_python_distro_if_nonexistent_or_incorrect_version,
        save_current_packages_as_default,
        save_requirements_of_root_folder_noVersion,
    )
    from do_not_change.specific_scripts.common_variables import (
        browser_terminal_path,
        compiled_terminal_path,
        default_packages_file_path,
        developer_settings_dir,
        developer_settings_path,
        icon_path,
        needed_packages_output_file_path,
        process_id_file_path,
        python_scripts_folder_path,
        script_wrapper_path,
        uncompiled_terminal_path,
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
        log_path = datetime.now(tz=timezone.utc).strftime(log_path)
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
            script_after_interpreter_crash_path,
            input_prepend,
            process_id_file_path,
            "1" if play_sound_on_success else "0",
            "1" if send_Windows_notification_on_success else "0",
            "1" if play_sound_on_failure else "0",
            "1" if send_Windows_notification_on_failure else "0",
            "1" if play_sound_on_python_interpreter_crash else "0",
            "1" if send_Windows_notification_on_python_interpreter_crash else "0",
        ]

        if use_faulthandler == True:
            extra_args = ["-X", "faulthandler"]
        else:
            extra_args = []

        if create_browser_terminal == True:
            proc = subprocess.Popen(  # noqa:S603 #type:ignore
                [
                    sys.executable,
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
            import json  # noqa:PLC0415

            # pass button settings via json
            if button_settings in [None, False]:
                button_settings_path = ""
            else:
                try:
                    button_settings_path = json.dumps(button_settings)
                except TypeError as e:
                    raise TypeError(
                        f'[Error] button_settings in developer settings at "{developer_settings_path}" must be JSON serializable.'
                    ) from e

            args += [
                "1" if terminal_needs_input else "0",
                stylesheet_path,
                dark_mode,
                "1" if use_faulthandler else "0",
                button_settings_path,
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
