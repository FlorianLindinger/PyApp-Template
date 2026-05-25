# todo: docstring

# ====================================

import os
import subprocess
import sys
import time
from datetime import datetime, timezone

# ====================================
# add root dir for debug cases where this script is called on its own:
root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
# ====================================

try:
    # =============================
    # global variables
    # =============================

    VALID_LAUNCH_MODES = ["terminal", "no_terminal", "terminal_emulator", "uncompiled_terminal_emulator", "browser"]
    EMPTY_ARG_INDICATOR = "__EMPTY__"

    # =============================
    # imports packages and common variables and developer settings
    # =============================

    from developer_settings import (
        button_settings,
        classic_terminal_cols,
        classic_terminal_lines,
        close_existing_instances_on_start,
        close_on_crash,
        close_on_failure,
        close_on_success,
        dark_mode,
        enable_log_for_browser_start,
        enable_log_for_no_terminal_start,
        enable_log_for_terminal_emulator_start,
        enable_log_for_Windows_terminal_start,
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
        prevent_launch_if_existing_instances_running,
        print_prepend,
        program_name,
        prompt_to_close_existing_instances,
        python_version,
        send_Windows_notification_on_crash,
        send_Windows_notification_on_failure,
        send_Windows_notification_on_success,
        start_in_shortcut_folder,
        start_minimized,
        stylesheet_path,
        terminal_bg_color,
        terminal_needs_input,
        terminal_text_color,
        use_classic_terminal,
        use_global_python,
    )
    from DONT_CHANGE.specific_scripts.common_code import (
        close_terminal,
        ensure_frontend_packages,
        get_running_processes_from_pid_file,
        input_warn,
        print_traceback,
        print_warn,
        stop_processes_from_pid_file,
    )
    from DONT_CHANGE.specific_scripts.common_variables import (
        CORRECT_START_SIGNAL_FILE_PATH,
        backend_packages_dir,
        browser_terminal_path,
        compiled_terminal_path,
        developer_settings_dir,
        developer_settings_path,
        frontend_python_exe,
        icon_path,
        play_sound_on_crash_default,
        play_sound_on_failure_default,
        play_sound_on_success_default,
        process_id_file_path,
        python_code_path,
        script_wrapper_path,
        uncompiled_terminal_path,
        windows_dir,
    )

    # needed for pywin32 to find its modules
    for path in reversed(
        [
            backend_packages_dir,
            os.path.join(backend_packages_dir, "win32"),
            os.path.join(backend_packages_dir, "win32", "lib"),
            os.path.join(backend_packages_dir, "Pythonwin"),
        ]
    ):
        if path not in sys.path:
            sys.path.insert(0, path)
    if hasattr(os, "add_dll_directory"):
        for path in [
            backend_packages_dir,
            os.path.join(backend_packages_dir, "pywin32_system32"),
        ]:
            if os.path.exists(path):
                os.add_dll_directory(path)

    # =============================
    # process imported variables
    # =============================

    script_path: str = python_code_path
    # raise error if script not found
    if not os.path.exists(script_path):
        raise FileNotFoundError(f'[Error] Python script not found at "{script_path}"')

    if use_global_python == True:
        python_exe_for_script_path = "py"
    else:
        python_exe_for_script_path = frontend_python_exe

    if start_in_shortcut_folder == True:
        wdir_is_script_dir = False
    else:
        wdir_is_script_dir = True

    if log_path_rel_to_start_folder in [None, False, ""]:
        log_path = EMPTY_ARG_INDICATOR
    else:
        if wdir_is_script_dir:
            log_path = os.path.normpath(os.path.join(os.path.dirname(script_path), log_path_rel_to_start_folder))
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
        stylesheet_path = EMPTY_ARG_INDICATOR
    else:
        if not os.path.isabs(stylesheet_path):
            stylesheet_path = os.path.normpath(developer_settings_dir + "\\" + stylesheet_path)

    if python_version in [None, False, ""]:
        python_version = EMPTY_ARG_INDICATOR
    if log_print_prepend in [None, False, ""]:
        log_print_prepend = EMPTY_ARG_INDICATOR
    if log_input_prepend in [None, False, ""]:
        log_input_prepend = EMPTY_ARG_INDICATOR
    if print_prepend in [None, False, ""]:
        print_prepend = EMPTY_ARG_INDICATOR
    if input_prepend in [None, False, ""]:
        input_prepend = EMPTY_ARG_INDICATOR
    if terminal_bg_color in [None, False, ""]:
        terminal_bg_color = EMPTY_ARG_INDICATOR
    if terminal_text_color in [None, False, ""]:
        terminal_text_color = EMPTY_ARG_INDICATOR
    if classic_terminal_cols in [None, False, ""]:
        classic_terminal_cols = EMPTY_ARG_INDICATOR
    else:
        classic_terminal_cols = str(classic_terminal_cols)
    if classic_terminal_lines in [None, False, ""]:
        classic_terminal_lines = EMPTY_ARG_INDICATOR
    else:
        classic_terminal_lines = str(classic_terminal_lines)
    if modern_terminal_tab_color in [None, False, ""]:
        modern_terminal_tab_color = EMPTY_ARG_INDICATOR

    if play_sound_on_crash is True:
        play_sound_on_crash = play_sound_on_crash_default
    elif play_sound_on_crash in [False, None, ""]:
        play_sound_on_crash = EMPTY_ARG_INDICATOR
    elif not os.path.isabs(play_sound_on_crash):
        play_sound_on_crash = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_crash)
    if play_sound_on_crash != EMPTY_ARG_INDICATOR and play_sound_on_crash[-4:] != ".wav":
        play_sound_on_crash += ".wav"
    if play_sound_on_crash != EMPTY_ARG_INDICATOR and not os.path.exists(play_sound_on_crash):
        print(f"[Warning] Sound file does not exist: {play_sound_on_crash}")
    if play_sound_on_success is True:
        play_sound_on_success = play_sound_on_success_default
    elif play_sound_on_success in [False, None, ""]:
        play_sound_on_success = EMPTY_ARG_INDICATOR
    elif not os.path.isabs(play_sound_on_success):
        play_sound_on_success = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_success)
    if play_sound_on_success != EMPTY_ARG_INDICATOR and play_sound_on_success[-4:] != ".wav":
        play_sound_on_success += ".wav"
    if play_sound_on_success != EMPTY_ARG_INDICATOR and not os.path.exists(play_sound_on_success):
        print(f"[Warning] Sound file does not exist: {play_sound_on_success}")
    if play_sound_on_failure is True:
        play_sound_on_failure = play_sound_on_failure_default
    elif play_sound_on_failure in [False, None, ""]:
        play_sound_on_failure = EMPTY_ARG_INDICATOR
    elif not os.path.isabs(play_sound_on_failure):
        play_sound_on_failure = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_failure)
    if play_sound_on_failure != EMPTY_ARG_INDICATOR and play_sound_on_failure[-4:] != ".wav":
        play_sound_on_failure += ".wav"
    if play_sound_on_failure != EMPTY_ARG_INDICATOR and not os.path.exists(play_sound_on_failure):
        print(f"[Warning] Sound file does not exist: {play_sound_on_failure}")

    # =============================
    # helper function
    # =============================

    def generate_minimized_startupinfo():
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = getattr(subprocess, "SW_SHOWMINIMIZED", 2)
        return startupinfo

    def bool_to_arg(value: bool) -> str:
        return "true" if value else "false"

    # =============================
    # main function
    # =============================

    def main() -> None:
        global log_path

        # clear old signal file
        try:
            if os.path.exists(CORRECT_START_SIGNAL_FILE_PATH):
                os.remove(CORRECT_START_SIGNAL_FILE_PATH)
        except Exception:
            pass

        # =============================
        # get args

        if len(sys.argv) >= 3:
            app_id = sys.argv[1]
            launch_mode = sys.argv[2]
        elif len(sys.argv) == 2:
            app_id = EMPTY_ARG_INDICATOR
            launch_mode = sys.argv[1]
        else:
            app_id = EMPTY_ARG_INDICATOR
            launch_mode = "terminal"

        # =============================
        # process args

        # check launch_mode
        if launch_mode not in VALID_LAUNCH_MODES:
            raise ValueError(
                f'[Error] Unknown launch_mode "{launch_mode}". Expected one of: {", ".join(VALID_LAUNCH_MODES)}'
            )

        # set log_path=EMPTY_ARG_INDICATOR if not enabled
        if (
            (launch_mode == "terminal" and enable_log_for_Windows_terminal_start == False)
            or (launch_mode == "no_terminal" and enable_log_for_no_terminal_start == False)
            or (launch_mode == "browser" and enable_log_for_browser_start == False)
            or (
                launch_mode in ["terminal_emulator", "uncompiled_terminal_emulator"]
                and enable_log_for_terminal_emulator_start == False
            )
        ):
            log_path = EMPTY_ARG_INDICATOR

        # ======================
        # close existing instances if enabled

        if close_existing_instances_on_start:
            stopped_count, _stale_count, failed_messages = stop_processes_from_pid_file(process_id_file_path)
            if failed_messages:
                raise RuntimeError("Failed to close existing program instance(s):\n" + "\n".join(failed_messages))
            if stopped_count:
                print(f"[Info] Closed {stopped_count} existing program instance(s).")
        elif prevent_launch_if_existing_instances_running:
            running_process_ids, _stale_count = get_running_processes_from_pid_file(process_id_file_path)
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

                stopped_count, _stale_count, failed_messages = stop_processes_from_pid_file(process_id_file_path)
                if failed_messages:
                    raise RuntimeError("Failed to close existing program instance(s):\n" + "\n".join(failed_messages))
                print(f"[Info] Closed {stopped_count} existing program instance(s).")

        # ======================
        # setup python

        if use_global_python == False:
            ensure_frontend_packages(app_id_for_slow=app_id)

        # ======================
        # launch terminal

        args = [
            script_path,
            program_name,
            icon_path,
            app_id,
            bool_to_arg(wdir_is_script_dir),
            bool_to_arg(close_on_crash),
            bool_to_arg(close_on_failure),
            bool_to_arg(close_on_success),
            print_prepend,
            log_path,
            log_print_prepend,
            bool_to_arg(overwrite_log),
            input_prepend,
            process_id_file_path,
            play_sound_on_success,
            bool_to_arg(send_Windows_notification_on_success),
            play_sound_on_failure,
            bool_to_arg(send_Windows_notification_on_failure),
            play_sound_on_crash,
            bool_to_arg(send_Windows_notification_on_crash),
            bool_to_arg(open_log_file_after_success),
            bool_to_arg(open_log_file_after_failure),
            bool_to_arg(open_log_file_after_crash),
            bool_to_arg(start_minimized),
            CORRECT_START_SIGNAL_FILE_PATH,
            log_input_prepend,
        ]

        # ==============

        if launch_mode == "browser":
            args += [python_exe_for_script_path]
            launched_backend_path = browser_terminal_path
            proc = subprocess.Popen(  # noqa:S603 #type:ignore
                [
                    sys.executable,
                    "-X",
                    "faulthandler",
                    browser_terminal_path,
                    *args,
                ],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        # ==============

        elif launch_mode in ["terminal_emulator", "uncompiled_terminal_emulator"]:
            # run in terminal emulator
            import json

            # pass button settings via json
            if button_settings in [None, False, ""]:
                button_settings_path = EMPTY_ARG_INDICATOR
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
                python_exe_for_script_path,
                bool_to_arg(terminal_needs_input),
                stylesheet_path,
                dark_mode,
                button_settings_path,
            ]

            if launch_mode == "uncompiled_terminal_emulator":
                launched_backend_path = uncompiled_terminal_path
                proc = subprocess.Popen(  # noqa:S603 #type:ignore
                    [
                        "py",
                        "-X",
                        "faulthandler",
                        uncompiled_terminal_path,
                        *args,
                    ],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            else:
                # run and wait (using the compiled terminal emulator)
                launched_backend_path = compiled_terminal_path
                proc = subprocess.Popen(  # noqa:S603 #type:ignore
                    [compiled_terminal_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    startupinfo=generate_minimized_startupinfo() if start_minimized else None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )

        # ==============

        else:  # run in terminal or no window
            # script_wrapper_path need additional args
            launched_backend_path = script_wrapper_path
            windows_terminal_mode = (
                "classic"
                if (use_classic_terminal and launch_mode == "terminal")
                else "modern"
                if (launch_mode == "terminal")
                else "invisible"
            )
            args += [
                terminal_bg_color + terminal_text_color,  # type:ignore
                windows_terminal_mode,
                classic_terminal_cols,
                classic_terminal_lines,
            ]

            script_command = [
                python_exe_for_script_path,
                "-X",
                "faulthandler",
                script_wrapper_path,
                *args,
            ]

            if windows_terminal_mode == "classic":
                terminal_command = ["conhost.exe", *script_command]
                creationflags = subprocess.CREATE_NEW_CONSOLE
                startupinfo = generate_minimized_startupinfo() if start_minimized else None
            elif windows_terminal_mode == "modern":
                terminal_command = ["wt.exe", "--title", program_name]
                if modern_terminal_tab_color != EMPTY_ARG_INDICATOR:
                    terminal_command += ["--tabColor", modern_terminal_tab_color]
                terminal_command += script_command
                creationflags = subprocess.CREATE_NO_WINDOW
                startupinfo = generate_minimized_startupinfo() if start_minimized else None
            else:
                terminal_command = script_command
                creationflags = subprocess.CREATE_NO_WINDOW
                startupinfo = None
            proc = subprocess.Popen(  # noqa:S603 #type:ignore
                terminal_command,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )

        # =================================
        # wait for signal file creation to know if correct start
        # =================================

        correct_start_signal_received = False
        for _ in range(40):  # try up to 2s
            if os.path.exists(CORRECT_START_SIGNAL_FILE_PATH):
                try:
                    os.remove(CORRECT_START_SIGNAL_FILE_PATH)
                except Exception:
                    pass
                correct_start_signal_received = True
                break
            time.sleep(0.05)

        if not correct_start_signal_received:
            error_code = proc.poll()
            print()
            print_warn("=" * 20)
            print_warn("[Error] Backend code did not seem to launch properly.")
            print_warn(f"Launch mode: {launch_mode}")
            print_warn(f"Backend code: {launched_backend_path}")
            print_warn(f'Error code (potentially meaningless): "{error_code}"')
            try:
                child_output, _ = proc.communicate(timeout=0.2)
            except Exception:
                child_output = ""
            if child_output:
                print_warn("-" * 20)
                print_warn(child_output.rstrip())
            print("=" * 20)
            input_warn("[Error (see above)] Press enter to exit.")
        close_terminal()

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
