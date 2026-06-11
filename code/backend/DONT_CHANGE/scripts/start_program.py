"""WIP"""

# {e} will be formatted to exception:
fail_message = "[Error] Failed during program start: {e}"

try:
    # ==============================
    # import Python packages
    # ==============================

    import os
    import subprocess
    import sys
    import time
    from datetime import datetime

    # ==============================
    # import third-party packages
    # ==============================

    # ==============================
    # imports from files
    # ==============================

    # add root dir to resolve file imports for debug cases where this script is called on its own:
    root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.developer_settings import (
        classic_terminal_cols,
        classic_terminal_lines,
        close_already_running_instances_on_start,
        enable_log_for_no_terminal_start,
        enable_log_for_Windows_terminal_start,
        log_path_rel_to_start_folder,
        modern_terminal_tab_color,
        prevent_start_if_already_running,
        program_name,
        prompt_to_close_existing_instances,
        start_in_shortcut_folder,
        start_minimized,
        terminal_bg_color,
        terminal_text_color,
        use_classic_terminal,
        use_global_python,
    )
    from backend.DONT_CHANGE.scripts._common_code import (
        close_terminal,
        ensure_frontend_packages,
        get_running_processes_from_pid_file,
        input_warn,
        print_traceback,
        print_warn,
        setup_terminal_colors,
        setup_unminimize_and_foreground_on_first_print,
        stop_processes_from_pid_file,
    )
    from backend.DONT_CHANGE.scripts._common_variables import (
        CORRECT_START_SIGNAL_FILE_PATH,
        EMPTY_ARG_INDICATOR,
        frontend_python_exe,
        process_id_file_path,
        python_script_path,
        script_wrapper_path,
    )

    # ==============================
    # define local variables
    # ==============================

    # ==============================
    # define local functions/classes
    # ==============================

    def get_frontend_args(app_id: str, log_path: str) -> list[str]:

        from backend.developer_settings import (
            close_on_crash,
            close_on_failure,
            close_on_success,
            input_prepend,
            log_input_prepend,
            log_print_prepend,
            open_log_file_after_crash,
            open_log_file_after_failure,
            open_log_file_after_success,
            overwrite_log,
            play_sound_on_crash,
            play_sound_on_failure,
            play_sound_on_success,
            print_prepend,
            python_version,
        )
        from backend.DONT_CHANGE.scripts._common_variables import (
            backend_packages_dir,
            backend_python_exe,
            env_var_to_signal_startup_time_measurement,
            icon_path,
            play_sound_on_crash_default,
            play_sound_on_failure_default,
            play_sound_on_success_default,
            python_script_path,
            start_time_dummy_main_script,
            windows_dir,
        )

        # change main_script if in startup time measurement mode
        if os.environ.get(env_var_to_signal_startup_time_measurement):
            python_script_path = start_time_dummy_main_script

        # raise error if script not found
        if not os.path.exists(python_script_path):
            raise FileNotFoundError(f'[Error] Python script not found at "{python_script_path}"')

        if start_in_shortcut_folder == True:
            wdir_is_script_dir = False
        else:
            wdir_is_script_dir = True

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

        # Normalize optional sound settings to concrete .wav paths. Each setting accepts False/None/"", True for the template default, a media filename, or an absolute path.
        if play_sound_on_crash is True:
            wav_on_crash = play_sound_on_crash_default
        elif play_sound_on_crash in [False, None, ""]:
            wav_on_crash = ""
        elif not os.path.isabs(play_sound_on_crash):
            wav_on_crash = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_crash)
        else:
            wav_on_crash = play_sound_on_crash
        if wav_on_crash != "":
            if wav_on_crash[-4:] != ".wav":
                wav_on_crash += ".wav"
            if not os.path.exists(wav_on_crash):
                print(f"[Warning] Sound file does not exist: {wav_on_crash}")
                wav_on_crash = ""

        if play_sound_on_success is True:
            wav_on_success = play_sound_on_success_default
        elif play_sound_on_success in [False, None, ""]:
            wav_on_success = ""
        elif not os.path.isabs(play_sound_on_success):
            wav_on_success = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_success)
        else:
            wav_on_success = play_sound_on_success
        if wav_on_success != "":
            if wav_on_success[-4:] != ".wav":
                wav_on_success += ".wav"
            if not os.path.exists(wav_on_success):
                print(f"[Warning] Sound file does not exist: {wav_on_success}")
                wav_on_success = ""

        if play_sound_on_failure is True:
            wav_on_failure = play_sound_on_failure_default
        elif play_sound_on_failure in [False, None, ""]:
            wav_on_failure = ""
        elif not os.path.isabs(play_sound_on_failure):
            wav_on_failure = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_failure)
        else:
            wav_on_failure = play_sound_on_failure
        if wav_on_failure != "":
            if wav_on_failure[-4:] != ".wav":
                wav_on_failure += ".wav"
            if not os.path.exists(wav_on_failure):
                print(f"[Warning] Sound file does not exist: {wav_on_failure}")
                wav_on_failure = ""

        out: list[str] = [
            EMPTY_ARG_INDICATOR,
            app_id,
            log_path,
            bool_to_string(close_on_crash),
            bool_to_string(close_on_failure),
            bool_to_string(close_on_success),
            icon_path,
            input_prepend,
            log_input_prepend,
            log_print_prepend,
            bool_to_string(open_log_file_after_crash),
            bool_to_string(open_log_file_after_failure),
            bool_to_string(open_log_file_after_success),
            bool_to_string(overwrite_log),
            print_prepend,
            program_name,
            python_script_path,
            wav_on_crash,
            wav_on_failure,
            wav_on_success,
            bool_to_string(wdir_is_script_dir),
            CORRECT_START_SIGNAL_FILE_PATH,
            process_id_file_path,
            backend_packages_dir,
            backend_python_exe,
        ]

        return make_empty_args_safe(out)

    def make_empty_args_safe(args: list[str]) -> list[str]:
        """Needed because passing empty args as "" in Windows can be flimsy -> replace "" with EMPTY_ARG_INDICATOR and decode in child."""
        return [a if a != "" else EMPTY_ARG_INDICATOR for a in args]

    def generate_minimized_startupinfo():
        """Creates subprocess.Popen STARTUPINFO that opens a child process minimized."""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = getattr(subprocess, "SW_SHOWMINNOACTIVE", 7)
        return startupinfo

    def bool_to_string(value: bool) -> str:
        return "true" if value else "false"

    # ==============================
    # define main function
    # ==============================

    def main() -> None:
        # ==============================
        # get args

        if len(sys.argv) == 3:
            app_id = sys.argv[1]
            launch_mode = sys.argv[2]
        elif len(sys.argv) == 1:
            app_id = ""
            launch_mode = "terminal"
        else:
            raise RuntimeError(f"[Error] Wrong number of arguments: {len(sys.argv) - 1}. Allowed 0 or 2.")

        # ==============================
        # process args

        if use_global_python == True:
            python_exe_for_script = "py"
        else:
            python_exe_for_script = frontend_python_exe

        # ==============================
        # set log_path if logging is enabled

        log_path = ""
        if (launch_mode == "terminal" and enable_log_for_Windows_terminal_start == True) or (
            launch_mode == "no_terminal" and enable_log_for_no_terminal_start == True
        ):
            if log_path_rel_to_start_folder:
                if start_in_shortcut_folder == True:
                    log_path = os.path.normpath(os.path.join(os.getcwd(), log_path_rel_to_start_folder))
                else:
                    log_path = os.path.normpath(
                        os.path.join(os.path.dirname(python_script_path), log_path_rel_to_start_folder)
                    )
                log_path = datetime.now().astimezone().strftime(log_path)

        # ==============================
        # clear old signal file (signals correct launch of child script)

        try:
            if os.path.exists(CORRECT_START_SIGNAL_FILE_PATH):
                os.remove(CORRECT_START_SIGNAL_FILE_PATH)
        except Exception:
            pass

        # ==============================
        # close existing instances or block start if already running, if enabled

        if close_already_running_instances_on_start or prevent_start_if_already_running:
            running_process_ids, _stale_count = get_running_processes_from_pid_file(process_id_file_path)

            if close_already_running_instances_on_start:
                if running_process_ids:
                    stopped_count, _stale_count, failed_messages = stop_processes_from_pid_file(process_id_file_path)
                else:
                    stopped_count = 0
                    failed_messages = []
                if failed_messages:
                    raise RuntimeError("Failed to close existing program instance(s):\n" + "\n".join(failed_messages))
                if stopped_count:
                    print(f"[Info] Closed {stopped_count} existing program instance(s).")
            elif prevent_start_if_already_running:
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
                        raise RuntimeError(
                            "Failed to close existing program instance(s):\n" + "\n".join(failed_messages)
                        )
                    print(f"[Info] Closed {stopped_count} existing program instance(s).")

        # ==============================
        # setup python

        if use_global_python == False:
            ensure_frontend_packages(app_id)

        # ==============================
        # setup passed args that all launch modes have in common

        args = get_frontend_args(app_id, log_path)

        # ==============================
        # launch main_script in specific launch mode

        if launch_mode in ["terminal", "no_terminal"]:
            # add terminal appearance to args:
            terminal_colors = ""
            if terminal_bg_color:
                terminal_colors += terminal_bg_color
            if terminal_text_color:
                terminal_colors += terminal_text_color

            args += [
                terminal_colors,
                classic_terminal_cols,
                classic_terminal_lines,
                (launch_mode == "terminal"),
            ]

            if launch_mode == "terminal":
                # get terminal launch command:
                if use_classic_terminal:
                    terminal_command = ["conhost.exe"]
                else:  # modern terminal case:
                    terminal_command = ["wt.exe", "--title", program_name]
                    if modern_terminal_tab_color:
                        terminal_command += ["--tabColor", modern_terminal_tab_color]

                startupinfo = generate_minimized_startupinfo() if start_minimized else None
                creationflags = subprocess.CREATE_NEW_CONSOLE
            else:  # no terminal case:
                startupinfo = None
                creationflags = subprocess.CREATE_NO_WINDOW
                terminal_command = []

            terminal_command += [
                python_exe_for_script,
                "-X",
                "faulthandler",
                script_wrapper_path,
                *args,
            ]

            # open new separate process and don't wait:
            process = subprocess.Popen(  # noqa:S603 #type:ignore
                terminal_command,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )

        else:
            raise ValueError(f'[Error] Unknown launch_mode: "{launch_mode}"')

        # ==============================
        # wait for signal file creation to know that child had correct start

        for _ in range(100):  # wait up to ~5s
            if os.path.exists(CORRECT_START_SIGNAL_FILE_PATH):
                try:
                    os.remove(CORRECT_START_SIGNAL_FILE_PATH)
                except Exception:
                    pass
                break
            time.sleep(0.05)
        else:
            error_code = process.poll()

            print()
            print_warn("=" * 20)
            print_warn("[Error] Backend code did not seem to launch properly")
            print_warn("-" * 20)
            print_warn(f"Launch mode: {launch_mode}")
            print_warn(f'Error code (potentially meaningless): "{error_code}"')
            try:
                child_output, _ = process.communicate(timeout=0.2)
                if child_output:
                    print_warn("-" * 20)
                    print_warn(child_output.rstrip())
            except Exception:
                pass
            print("=" * 20)
            input_warn("[Error] Press enter to exit")

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            setup_terminal_colors()
            setup_unminimize_and_foreground_on_first_print()
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))
            input_warn("[Error] Press enter to exit")
        close_terminal()

    # =============================

except Exception as e:
    import os
    import traceback

    print()
    print()
    print("=" * 30)
    print(fail_message.format(e=e))
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
