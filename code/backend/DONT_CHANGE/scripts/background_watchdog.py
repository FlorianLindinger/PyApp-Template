"""WIP"""

# safe default (should be overwritten in following try block):
PROGRAM_HAS_TERMINAL = False  # means a new terminal will be created for prints

try:
    # ==============================
    # import Python packages
    # ==============================

    import atexit
    import os
    import subprocess
    import sys
    import threading

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
        close_after_failure,
        close_after_KeyboardInterrupt,
        close_after_success,
        close_already_running_instances_on_start,
        enable_log_for_no_terminal_start,
        enable_log_for_Windows_terminal_start,
        input_prepend,
        log_input_prepend,
        log_path,
        log_path_is_relative_to_start_folder_if_relative,
        log_print_prepend,
        overwrite_log,
        prevent_start_if_already_running,
        print_prepend,
        program_name,
        prompt_to_close_existing_instances,
        start_in_shortcut_folder,
        use_global_python,
    )
    from backend.DONT_CHANGE.scripts._common_code import (
        close_terminal,
        get_running_processes_from_pid_file,
        make_empty_args_safe,
        resolve_log_path,
        set_terminal_app_id,
        set_terminal_colors,
        set_terminal_icon,
        set_terminal_title,
        stop_processes_from_pid_file,
    )
    from backend.DONT_CHANGE.scripts._common_variables import (
        CORRECT_START_SIGNAL_FILE_PATH,
        EMPTY_ARG_INDICATOR,
        env_var_to_signal_startup_time_measurement,
        exit_processer_path,
        frontend_python_exe,
        frontend_script_wrapper_path,
        icon_path,
        process_id_file_path,
        python_script_path,
        start_time_dummy_main_script_path,
        tmp_traceback_json_path,
    )

    # ==============================
    # process imported variables
    # ==============================

    if log_print_prepend in (None, False, ""):
        log_print_prepend = ""
    if log_input_prepend in (None, False, ""):
        log_input_prepend = ""
    if print_prepend in (None, False, ""):
        print_prepend = ""
    if input_prepend in (None, False, ""):
        input_prepend = ""

    # ==============================
    # define local variables
    # ==============================

    # ==============================
    # define local functions/classes
    # ==============================

    class _ProcessIdRegistry:
        """Maintain the PID file entries created by this launcher process."""

        def __init__(self, path: str) -> None:
            self.path = path
            self._process_ids: set[int] = set()
            self._lock = threading.RLock()

        def add(self, process_id: int) -> None:
            """Add a pid value to the local collection when valid and new."""
            if self.path == "" or process_id <= 0:
                return

            with self._lock:
                if process_id in self._process_ids:
                    return
                self._process_ids.add(process_id)

                folder = os.path.dirname(self.path)
                if folder:
                    os.makedirs(folder, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as pid_file:
                    pid_file.write(f"{process_id}\n")

        def remove(self, process_id: int) -> None:
            """Remove a value from the local collection and backing file."""
            if self.path == "" or process_id <= 0:
                return

            with self._lock:
                self._process_ids.discard(process_id)
                try:
                    with open(self.path, encoding="utf-8") as pid_file:
                        lines = pid_file.readlines()
                except FileNotFoundError:
                    return
                except Exception:
                    return

                remaining_lines = []
                process_id_text = str(process_id)
                for line in lines:
                    parts = line.strip().split(maxsplit=1)
                    if parts and parts[0] == process_id_text:
                        continue
                    remaining_lines.append(line)

                try:
                    if any(line.strip() for line in remaining_lines):
                        with open(self.path, "w", encoding="utf-8") as pid_file:
                            pid_file.writelines(remaining_lines)
                    else:
                        os.remove(self.path)
                except Exception:
                    pass

        def cleanup(self) -> None:
            """Remove registered process IDs during interpreter shutdown."""
            for process_id in list(self._process_ids):
                self.remove(process_id)

    def process_exit_here_or_in_new_terminal(
        exit_code: int | str,
        app_id: str,
        program_has_terminal: bool,
        log_path_resolved: str,
        selected_python_script_path: str,
    ):
        new_terminal_was_created = not program_has_terminal
        args = [
            str(exit_code),
            app_id,
            "true" if new_terminal_was_created else "false",
            log_path_resolved,
            selected_python_script_path,
        ]

        if not program_has_terminal:
            # don't wait:
            subprocess.Popen(  # noqa:S603
                [
                    "conhost.exe",
                    sys.executable,
                    "-X",
                    "faulthandler",
                    exit_processer_path,
                    *args,
                ],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

        else:
            import runpy

            old_argv = sys.argv[:]
            try:
                sys.argv = ["_filename"] + args
                # waiting:
                runpy.run_path(exit_processer_path, run_name="__main__")
            finally:
                sys.argv = old_argv

    def get_frontend_args(selected_python_script_path: str, app_id: str, log_path: str) -> list[str]:
        """Get the arguments to pass to the frontend script."""

        return make_empty_args_safe(
            [
                EMPTY_ARG_INDICATOR,
                selected_python_script_path,
                app_id,
                print_prepend,
                input_prepend,
                log_input_prepend,
                log_path,
                "true" if overwrite_log else "false",
                log_print_prepend,
                tmp_traceback_json_path,
            ]
        )

    # ==============================
    # define main function
    # ==============================

    def main() -> None:
        global PROGRAM_HAS_TERMINAL

        # ==============================
        # tell the backend terminal via a signal file to close because successful start

        if CORRECT_START_SIGNAL_FILE_PATH:
            folder = os.path.dirname(CORRECT_START_SIGNAL_FILE_PATH)
            if folder:
                os.makedirs(folder, exist_ok=True)
            open(CORRECT_START_SIGNAL_FILE_PATH, "w", encoding="utf-8").close()

        # ==============================
        # delete old temporary crash traceback report if existing (to know if new one was created later)

        if os.path.exists(tmp_traceback_json_path):
            os.remove(tmp_traceback_json_path)

        # ==============================
        # get args

        _file_name, app_id, launch_mode = sys.argv
        if app_id == EMPTY_ARG_INDICATOR:
            app_id = ""

        # ==============================

        if launch_mode in ("wt", "conhost"):
            PROGRAM_HAS_TERMINAL = True

            set_terminal_colors()

            # set app-id for grouping of this terminal in taskbar with shorcut pinned to taskbar
            set_terminal_app_id(app_id)

            if launch_mode == "wt":
                set_terminal_icon(icon_path)

            elif launch_mode == "conhost":
                # set terminal title in case shortcut was renamed:
                set_terminal_title(program_name)
        else:
            PROGRAM_HAS_TERMINAL = False

        # ==============================
        # add pid to "currently running" file:

        process_id_registry = _ProcessIdRegistry(process_id_file_path)
        process_id_registry.add(os.getpid())
        atexit.register(process_id_registry.cleanup)

        # ==============================
        # process args

        if use_global_python:
            python_exe_for_script = "py"
        else:
            python_exe_for_script = frontend_python_exe

        # ==============================
        # get log_path if logging is enabled

        if (launch_mode == "terminal" and enable_log_for_Windows_terminal_start) or (
            launch_mode == "no_terminal" and enable_log_for_no_terminal_start
        ):
            log_path_resolved = resolve_log_path(log_path, log_path_is_relative_to_start_folder_if_relative)
        else:
            log_path_resolved = ""

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
        # setup variables used in launch

        if os.environ.get(env_var_to_signal_startup_time_measurement):
            selected_python_script_path = start_time_dummy_main_script_path
            os.environ.pop(env_var_to_signal_startup_time_measurement, None)
        else:
            selected_python_script_path = python_script_path

        if not os.path.exists(selected_python_script_path):
            raise FileNotFoundError(f'[Error] Python script not found at "{selected_python_script_path}"')

        passed_args = get_frontend_args(selected_python_script_path, app_id, log_path_resolved)

        if start_in_shortcut_folder:
            wdir_is_script_dir = False
            cwd_for_main_script = None
        else:
            wdir_is_script_dir = True
            cwd_for_main_script = os.path.dirname(selected_python_script_path)

        # ==============================
        # set environment variables for main.py script

        wrapper_env_vars = os.environ.copy()
        wrapper_env_vars["PROGRAM_NAME"] = program_name
        wrapper_env_vars["ICON_PATH"] = icon_path
        wrapper_env_vars["PROGRAM_HAS_TERMINAL"] = "1" if PROGRAM_HAS_TERMINAL else "0"
        wrapper_env_vars["LOG_PATH"] = log_path_resolved
        wrapper_env_vars["APP_ID"] = app_id
        wrapper_env_vars["WDIR_IS_SCRIPT_DIR"] = "1" if wdir_is_script_dir else "0"
        wrapper_env_vars["CLOSE_AFTER_FAILURE"] = "1" if close_after_failure else "0"
        wrapper_env_vars["CLOSE_AFTER_SUCCESS"] = "1" if close_after_success else "0"
        wrapper_env_vars["CLOSE_AFTER_KEYBOARDINTERRUPT"] = "1" if close_after_KeyboardInterrupt else "0"

        # ==============================
        # start wrapper script and don't wait for finish

        process = subprocess.Popen(  # noqa:S603
            [python_exe_for_script, frontend_script_wrapper_path, *passed_args],
            encoding="utf-8",
            env=wrapper_env_vars,
            cwd=cwd_for_main_script,
        )

        # ==============================
        # update terminal appearance if visible

        if PROGRAM_HAS_TERMINAL:
            # set terminal icon + app-ID (for taskabr grouping of terminal) in new thread because slow:
            def _set_terminal_icon_and_app_id() -> None:
                try:
                    set_terminal_icon(icon_path)  # type: ignore
                    set_terminal_app_id(app_id)
                except Exception as error:
                    print(f"[Warning] Error during terminal appearance update: {error}")

            terminal_appearance_thread = threading.Thread(target=_set_terminal_icon_and_app_id)
            terminal_appearance_thread.start()
        else:
            terminal_appearance_thread = None

        # ==============================
        # wait for finish of wrapper

        # Ctrl+C is delivered to every process attached to this console.
        # Ignore it in the watchdog while waiting so main.py receives the first interrupt.
        import signal

        old_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            process.wait()
        finally:
            signal.signal(signal.SIGINT, old_sigint_handler)

        # ==============================
        # handle exit of wrapper

        exit_mode = process.returncode  # Can be 0,1,2,3

        # exit_mode meaning:
        # 0 = correctly handled end of script in main.py (no json)
        # 1 = correctly handled other exit of main.py (json)
        # 2 = handled failure in wrapper of main.py (json)
        # 3 = unsuccessfully handled failure in wrapper of main.py (no json)
        # (4 = handled failure in this script. See Exception of main below)

        # process exit in current terminal if it exists or in new terminal if not. Wait in the second case:
        process_exit_here_or_in_new_terminal(
            exit_mode, app_id, PROGRAM_HAS_TERMINAL, log_path_resolved, selected_python_script_path
        )

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            # WIP_ save_exception_as_json()
            process_exit_here_or_in_new_terminal(
                exit_code=4,
                app_id="",
                program_has_terminal=PROGRAM_HAS_TERMINAL,
                log_path_resolved="",
                selected_python_script_path="",
            )

        close_terminal()

    # ==============================

except Exception as e:
    import os
    import traceback

    # WIP: assume no terminal and make new windwo and print traceback

    PROGRAM_HAS_TERMINAL

    print()
    print()
    print("=" * 30)
    print(f"[Error] Within background watchdog: {e}")
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
