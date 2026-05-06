# todo: docstring

# ====================================

import os
import subprocess
import sys
import time
from datetime import datetime, timezone

# ====================================
# setup for start without backend python (eg for debug)
DONT_CHANGE_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
code_dir = os.path.normpath(os.path.join(DONT_CHANGE_dir, ".."))
bundled_packages_dir = os.path.join(DONT_CHANGE_dir, "python_packages")

for path in reversed(
    [
        code_dir,
        bundled_packages_dir,
        os.path.join(bundled_packages_dir, "win32"),
        os.path.join(bundled_packages_dir, "win32", "lib"),
        os.path.join(bundled_packages_dir, "Pythonwin"),
    ]
):
    if path not in sys.path:
        sys.path.insert(0, path)

if hasattr(os, "add_dll_directory"):
    for path in [
        bundled_packages_dir,
        os.path.join(bundled_packages_dir, "pywin32_system32"),
    ]:
        if os.path.exists(path):
            os.add_dll_directory(path)
# end of setup for start without backend python (eg for debug)
# ====================================


try:
    # =============================
    # imports packages and common variables and developer settings
    # =============================

    from developer_settings import (
        button_settings,
        close_existing_instances_on_start,
        close_on_failure,
        close_on_python_interpreter_crash,
        close_on_success,
        dark_mode,
        enable_log_for_no_terminal_start,
        enable_log_for_terminal_start,
        input_prepend,
        log_path_rel_to_wdir,
        log_timestamp_format,
        open_log_file_after_failure,
        open_log_file_after_python_interpreter_crash,
        open_log_file_after_success,
        overwrite_log,
        play_sound_on_failure,
        play_sound_on_python_interpreter_crash,
        play_sound_on_success,
        prevent_launch_if_existing_instances_running,
        print_timestamp_format,
        prompt_to_close_existing_instances,
        python_code_name,
        python_version,
        script_after_python_interpreter_crash_name,
        send_Windows_notification_on_failure,
        send_Windows_notification_on_python_interpreter_crash,
        send_Windows_notification_on_success,
        start_in_shortcut_folder,
        start_minimized,
        stylesheet_path,
        terminal_bg_color,
        terminal_needs_input,
        terminal_text_color,
        use_faulthandler,
        use_global_python,
        use_uncompiled_terminal_emulator_and_run_it_in_global,  # noqa
    )
    from developer_settings import (
        program_name as title,
    )
    from DONT_CHANGE.specific_scripts.common_code import (
        delete_venv,
        get_running_processes_from_pid_file,
        input_warn,
        install_packages,
        print_traceback,
        print_warn,
        read_search_phrase_state,
        recreate_portable_venv,
        reinstall_python_distro_if_nonexistent_or_incorrect_version,
        save_current_packages_as_default,
        save_requirements_of_root_folder_noVersion,
        stop_processes_from_pid_file,
    )
    from DONT_CHANGE.specific_scripts.common_variables import (
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

        valid_launch_modes = ["terminal", "no_terminal", "terminal_emulator", "browser"]

        if len(sys.argv) >= 3:
            app_id = sys.argv[1]
            launch_mode = sys.argv[2]
        elif len(sys.argv) == 2:
            app_id = ""
            launch_mode = sys.argv[1]
        else:
            app_id = ""
            launch_mode = "terminal"

        if launch_mode not in valid_launch_modes:
            raise ValueError(
                f'[Error] Unknown launch_mode "{launch_mode}". Expected one of: {", ".join(valid_launch_modes)}'
            )

        # it overrides use_uncompiled_terminal_emulator_and_run_it_in_global from developer_settings
        if len(sys.argv) > 3:  # any arg means True. Used for debug before compiling terminal emulator
            use_uncompiled_terminal_emulator_and_run_it_in_global = True

        if close_existing_instances_on_start:
            stop_result = stop_processes_from_pid_file(process_id_file_path)
            failed_messages = list(stop_result["failed_messages"])
            if failed_messages:
                raise RuntimeError(
                    "Failed to close existing program instance(s):\n" + "\n".join(failed_messages)
                )
            stopped_count = int(stop_result["stopped_count"])
            if stopped_count:
                print(f"[Info] Closed {stopped_count} existing program instance(s).")
        elif prevent_launch_if_existing_instances_running:
            running_result = get_running_processes_from_pid_file(process_id_file_path)
            running_process_ids = list(running_result["running_process_ids"])
            if running_process_ids:
                print(
                    f"[Info] {len(running_process_ids)} existing program instance(s) are still running: "
                    + ", ".join(str(process_id) for process_id in running_process_ids)
                )

                if not prompt_to_close_existing_instances:
                    input("[Info] New launch cancelled. Press Enter to exit.")
                    sys.exit(0)

                answer = input("Close the existing instance(s) and launch a new one? [y/N] ").strip().lower()
                if answer not in {"y", "yes"}:
                    print("[Info] New launch cancelled.")
                    sys.exit(0)

                stop_result = stop_processes_from_pid_file(process_id_file_path)
                failed_messages = list(stop_result["failed_messages"])
                if failed_messages:
                    raise RuntimeError(
                        "Failed to close existing program instance(s):\n" + "\n".join(failed_messages)
                    )
                print(f"[Info] Closed {int(stop_result['stopped_count'])} existing program instance(s).")

        def bool_arg(value: bool) -> str:
            return "true" if value else "false"

        def sound_arg(value: str | bool | None, default_wav: str) -> str:
            if value in [None, False, ""]:
                return ""
            if value is True:
                return default_wav

            sound_path = str(value).strip()
            if sound_path.lower() in {"", "0", "false", "no", "off", "none"}:
                return ""
            extension = os.path.splitext(sound_path)[1]
            if not extension:
                sound_path += ".wav"
            elif extension.lower() != ".wav":
                raise ValueError(f'[Error] Sound setting must be False, None, "", True, or a .wav file: "{sound_path}"')
            return sound_path

        def generate_minimized_startupinfo():
            if not start_minimized:
                return None

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = getattr(subprocess, "SW_SHOWMINIMIZED", 2)
            return startupinfo

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

        if launch_mode != "no_terminal":
            effective_log_path = log_path if enable_log_for_terminal_start else ""
        else:
            effective_log_path = log_path if enable_log_for_no_terminal_start else ""

        args = [
            title,
            icon_path,
            app_id,
            bool_arg(wdir_is_script_dir),
            bool_arg(close_on_python_interpreter_crash),
            bool_arg(close_on_failure),
            bool_arg(close_on_success),
            print_timestamp_format,
            effective_log_path,
            log_timestamp_format,
            bool_arg(overwrite_log),
            script_after_interpreter_crash_path,
            input_prepend,
            process_id_file_path,
            sound_arg(play_sound_on_success, "notify.wav"),
            bool_arg(send_Windows_notification_on_success),
            sound_arg(play_sound_on_failure, "Windows Critical Stop.wav"),
            bool_arg(send_Windows_notification_on_failure),
            sound_arg(play_sound_on_python_interpreter_crash, "Windows Critical Stop.wav"),
            bool_arg(send_Windows_notification_on_python_interpreter_crash),
            bool_arg(open_log_file_after_success),
            bool_arg(open_log_file_after_failure),
            bool_arg(open_log_file_after_python_interpreter_crash),
            bool_arg(start_minimized),
        ]

        if use_faulthandler == True:
            extra_args = ["-X", "faulthandler"]
        else:
            extra_args = []

        if launch_mode == "browser":
            launched_backend_path = browser_terminal_path
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
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        elif launch_mode == "terminal_emulator":
            # run in terminal emulator
            import json

            # pass button settings via json
            if button_settings in [None, False]:
                button_settings_path = ""
            else:
                try:
                    button_settings_path = json.dumps(dict(button_settings))
                except TypeError as e:
                    raise TypeError(
                        f'[Error] button_settings in developer settings at "{developer_settings_path}" must be JSON serializable and convertible to a dict.'
                    ) from e
                except ValueError as e:
                    raise ValueError(
                        f'[Error] button_settings in developer settings at "{developer_settings_path}" must be a dict or an iterable of (button_name, settings) pairs.'
                    ) from e

            args += [
                bool_arg(terminal_needs_input),
                stylesheet_path,
                dark_mode,
                bool_arg(use_faulthandler),
                button_settings_path,
            ]

            if use_uncompiled_terminal_emulator_and_run_it_in_global == True:  # Meant for debugging terminal
                launched_backend_path = uncompiled_terminal_path
                proc = subprocess.Popen(  # noqa:S603 #type:ignore
                    ["py", *extra_args, uncompiled_terminal_path, script_path, python_exe_for_script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            else:
                # run and wait (using the compiled terminal emulator)
                launched_backend_path = compiled_terminal_path
                proc = subprocess.Popen(  # noqa:S603 #type:ignore
                    [compiled_terminal_path, script_path, python_exe_for_script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    startupinfo=generate_minimized_startupinfo(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )

        else:  # run in terminal or no window
            # script_wrapper_path need additional args
            launched_backend_path = script_wrapper_path
            args += [
                terminal_bg_color + terminal_text_color,  # type:ignore
                bool_arg(launch_mode == "terminal"),
            ]

            if launch_mode == "terminal":  # run in terminal and don't wait
                proc = subprocess.Popen(  # noqa:S603 #type:ignore
                    [python_exe_for_script_path, *extra_args, script_wrapper_path, script_path, *args],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    startupinfo=generate_minimized_startupinfo(),
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
            print(f"[Error] Failed launching {launch_mode} backend:")
            print(launched_backend_path)
            print("-" * 20)
            try:
                child_output, _ = proc.communicate(timeout=0.2)
            except Exception:
                child_output = ""
            if child_output:
                print(child_output.rstrip())
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
