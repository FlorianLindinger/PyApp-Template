"""Own one application run: instance policy, logging, the app process and completion handling."""

from __future__ import annotations

import io
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Dict, Optional, Union

# Last, so app modules named like standard-library modules (code/random.py, ...) cannot shadow them.
sys.path.append(str(Path(__file__).resolve().parents[3]))
from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.runtime._pyapp import (
    EXIT_MODE_FOR_WRAPPER_EXIT,
    ExitMode,
    exit_code_is_success,
    save_report,
)
from pyapp.DONT_CHANGE.scripts.config import main_script_path
from pyapp.DONT_CHANGE.scripts.config import settings as load_settings
from pyapp.DONT_CHANGE.scripts.console_tools import (
    print_info,
    set_terminal_app_id,
    set_terminal_icon,
    set_terminal_title,
)
from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored
from pyapp.DONT_CHANGE.scripts.file_tools import make_abs_path_relative_to_file
from pyapp.DONT_CHANGE.scripts.instance_policy import decide
from pyapp.DONT_CHANGE.scripts.launcher_ui import (
    OUTPUT_LOG_SUFFIX,
    get_log_folder_path,
    get_log_path,
    set_settings_colors,
)
from pyapp.DONT_CHANGE.scripts.runtime_state import (
    ProcessRegistry,
    atomic_json,
    clean_python_environment,
    create_own_job,
    terminate_tree,
    unique_log_path,
)

# Popen became subscriptable in 3.9; runtime inspection (typing.get_type_hints) on 3.8 uses the class.
if TYPE_CHECKING:
    from pyapp.DONT_CHANGE.scripts.system_tray import MinimizeToTray

    BinaryProcess = subprocess.Popen[bytes]
else:
    BinaryProcess = subprocess.Popen


def app_working_folder(settings: Union[ModuleType, SimpleNamespace], script: str) -> str:
    """Keep the inherited starting folder when requested; otherwise use the main script's folder."""
    if settings.start_in_shortcut_position:
        return os.environ.get("PYAPP_START_DIR", str(Path.cwd()))
    return str(Path(script).parent)


def app_environment(
    settings: Union[ModuleType, SimpleNamespace], has_terminal: bool, log_path: str, app_id: str
) -> Dict[str, str]:
    """Build the app's public environment without creating the folders its paths describe."""
    env = clean_python_environment()
    for key in list(env):
        if key.startswith("PYAPP_"):
            env.pop(key)
    env.update(settings.environment_for_main_py)
    env.update(
        PROGRAM_NAME=settings.program_name,
        ICON_PATH=paths.ICON_PATH,
        SUCCESS_ICON_PATH=paths.SUCCESS_ICON_PATH,
        FAILURE_ICON_PATH=paths.FAILURE_ICON_PATH,
        SETTINGS_ICON_PATH=paths.SETTINGS_ICON_PATH,
        LOG_ICON_PATH=paths.LOG_ICON_PATH,
        CRASH_LOG_ICON_PATH=paths.CRASH_LOG_ICON_PATH,
        OPEN_CODE_ICON_PATH=paths.OPEN_CODE_ICON_PATH,
        TITLE_AFTER_SUCCESS=settings.title_after_success,
        TITLE_AFTER_FAILURE=settings.title_after_failure,
        USER_SETTINGS_PATH=(
            make_abs_path_relative_to_file(settings.user_settings_path, paths.DEV_SETTINGS_PATH)
            if settings.user_settings_path
            else ""
        ),
        LOG_DIR=str(Path(log_path).parent) if log_path else "",
        CRASH_LOG_DIR=(
            get_log_folder_path(
                settings.crash_log_path, settings.crash_log_path_is_relative_to_start_folder_if_relative
            )
            or ""
        )
        if settings.enable_crash_log
        else "",
        PROJECT_DIR=str(Path(paths.BACKEND_DIR).parents[1]),
        START_DIR=os.environ.get("PYAPP_START_DIR", str(Path.cwd())),
        PROGRAM_HAS_TERMINAL="1" if has_terminal else "0",
        LOG_PATH=log_path,
        APP_ID=app_id,
        WDIR_IS_SCRIPT_DIR="0" if settings.start_in_shortcut_position else "1",
        CLOSE_AFTER_FAILURE="1" if settings.close_after_failure else "0",
        CLOSE_AFTER_SUCCESS="1" if settings.close_after_success else "0",
    )
    return env


def end_started_app(child: Optional[BinaryProcess]) -> None:
    """End an app this watchdog started but can no longer supervise, with its child processes.

    Without this, a watchdog error after the start would leave the app running unregistered, so
    Stop could not find it and a retry would start a second copy. The process tree is used, not
    the job: the watchdog is in the job itself and must survive to report the error.
    """
    if child is None or child.poll() is not None:
        return
    try:
        terminate_tree(child.pid)
        child.wait(timeout=10)
    except Exception:
        note_ignored("end the app after a watchdog error")


def stop_from_tray(child: Optional[BinaryProcess], run_dir: Path, timeout: float) -> None:
    """Stop only this run, keeping the watchdog alive to remove its tray icon and registration."""
    if child is None or child.poll() is not None:
        return
    try:
        (run_dir / paths.STOP_REQUEST_FILE_NAME).write_text("stop", encoding="utf-8")
        if timeout > 0:
            from pyapp.DONT_CHANGE.scripts.runtime_state import request_close

            request_close({"pid": os.getpid(), "child": {"pid": child.pid}})
            try:
                child.wait(timeout=timeout)
                return
            except subprocess.TimeoutExpired:
                pass
        end_started_app(child)
    except Exception:
        note_ignored("stop this app from the system tray")


def acknowledge(run_dir: Path, **payload: object) -> None:
    """Atomically publish watchdog startup status for the waiting launcher."""
    atomic_json(run_dir / "startup.json", payload)


def successful_application_exit(mode: int, run_dir: Path) -> bool:
    """Normal return, or SystemExit with None/integer zero."""
    if mode == ExitMode.SUCCESS:
        return True
    if mode == ExitMode.APP_EXIT:
        try:
            report = json.loads((run_dir / "traceback.json").read_text(encoding="utf-8"))
            return report.get("exception_type") == "SystemExit" and exit_code_is_success(report.get("system_exit_code"))
        except (OSError, ValueError):
            pass
    return False


# The last part of what the app printed before its wrapper took over the output (see save_early_output).
EARLY_OUTPUT_LIMIT = 1_048_576


def save_early_output(raw_path: str, early_output: bytes) -> None:
    """Keep what the app printed if its wrapper never set up the raw output file.

    That happens when the interpreter or the wrapper fails right at the start; the wrapper then
    cannot merge the output into the log, and the console may be gone (no terminal).
    """
    if raw_path and early_output and not Path(raw_path).exists():
        try:
            Path(raw_path).write_bytes(early_output)
        except OSError:
            note_ignored("save the early output")


def keep_raw_output(raw_path: str, log_path: str, mode: int, run_dir: Path) -> None:
    """Move the raw output next to the log as evidence of a failure, or delete it.

    While the app runs it lives in the run folder (tmp/runs/<id>), out of the log folder. After a
    normal end the log contains all of it, and an empty one is evidence of nothing (Ctrl+C, a
    closed window); only a failure with output leaves <log>.output.log next to the log.
    """
    if not raw_path:
        return
    raw = Path(raw_path)
    try:
        if not raw.is_file():
            return
        if successful_application_exit(mode, run_dir) or raw.stat().st_size == 0 or not log_path:
            raw.unlink()
            return
        target = Path(log_path + OUTPUT_LOG_SUFFIX)
        try:
            raw.replace(target)
        except OSError:
            # A child program of the app may still have it open, which forbids moving it on
            # Windows: keep a copy as evidence; the run folder is deleted with the next launch.
            shutil.copyfile(raw, target)
    except OSError:
        note_ignored("keep or remove the raw output")


def handle_exit(
    settings: Union[ModuleType, SimpleNamespace],
    mode: int,
    app_id: str,
    has_terminal: bool,
    log_path: str,
    script: str,
    run_dir: Path,
    native_code: Optional[int] = None,
) -> None:
    """Run completion handling in the current, a hidden, or a new console as needed."""
    env = os.environ.copy()
    env["PYAPP_RUN_DIR"] = str(run_dir)
    if native_code is not None:
        env["PYAPP_UNEXPECTED_EXIT"] = str(native_code)
    args = [
        sys.executable,
        "-I",
        "-S",
        "-X",
        "utf8",
        paths.PROCESS_EXIT_PATH,
        str(mode),
        app_id,
        "false" if has_terminal else "true",
        log_path,
        script,
    ]
    success = successful_application_exit(mode, run_dir)
    if not has_terminal and success and settings.close_after_success:
        # Successful hidden runs perform their completion actions without a console. Nobody can
        # type into that console, so stdin is NUL: a prompt (e.g. after an error in the handler)
        # ends at once instead of keeping both processes alive, invisible to Stop.
        # Run the launcher helper or configured app interpreter with a controlled argument list.
        hidden = subprocess.run(  # noqa: S603
            args, env=env, check=False, stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW
        )
        if hidden.returncode == 0:
            return
        # The handler itself failed (e.g. developer_settings.py was broken while the app ran):
        # run it again in a window below, so the error is seen.
    if has_terminal:
        # Run the launcher helper or configured app interpreter with a controlled argument list.
        subprocess.run(args, env=env, check=False)  # noqa: S603
    else:
        # Run the launcher helper or configured app interpreter with a controlled argument list.
        subprocess.run(  # noqa: S603
            # Run the launcher helper or configured app interpreter with a controlled argument list.
            [paths.CONHOST_EXE, *args],
            env=env,
            check=False,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )


def register_with_policy(
    settings: Union[ModuleType, SimpleNamespace], registry: ProcessRegistry, run_dir: Path
) -> bool:
    """Apply instance_policy and register.

    Dialogs and stopping other instances happen without holding the registry lock (a stopping
    watchdog needs it to unregister); the check is then repeated under the lock.
    """
    policy = settings.instance_policy
    for _ in range(5):
        with registry.lock():
            records, _ = registry.records()
            if not records or policy == "allow":
                registry.register()
                return True
        if policy != "replace":
            decision = decide(policy, records, settings.program_name)
            if decision == "cancel":
                acknowledge(run_dir, status="cancelled")
                return False
            policy = "replace"
        _, _, errors = registry.stop(settings.stop_timeout_seconds, report=print)
        if errors:
            raise RuntimeError("Could not stop existing instances: " + "; ".join(errors))
    raise RuntimeError("Other instances keep starting; could not replace them.")


def main() -> None:
    """Own registration, launch, logging and completion handling for one application run."""
    app_id, launch_mode = sys.argv[1:3]
    if app_id == paths.EMPTY_ARG_INDICATOR:
        app_id = ""
    run_dir = Path(os.environ["PYAPP_RUN_DIR"])
    # developer_settings, loaded here (not at import time); start_program.py validated it, but it
    # can change in between. The waiting launcher then shows why instead of a bare timeout.
    try:
        settings = load_settings()
    except Exception as error:
        acknowledge(run_dir, status="failed", message=f"developer_settings.py could not be loaded: {error}")
        raise
    # Discard inherited launch state: only this run may provide a terminal handle to completion.
    os.environ.pop("PYAPP_TERMINAL_WINDOW", None)
    os.environ.pop("PYAPP_TASKBAR_ACTIVITY", None)
    has_terminal = launch_mode in ("wt", "conhost", "browser")
    registry = ProcessRegistry(paths.PROCESS_REGISTRY_DIR)
    try:
        # Before anything is started: the app and all its processes then belong to this job.
        create_own_job()
    except Exception:
        note_ignored("create_own_job (Stop falls back to the process tree)")
    script = ""
    log_path = ""
    registered = False
    exit_handled = False
    child: Optional[BinaryProcess] = None
    tray: Optional[MinimizeToTray] = None
    try:
        if launch_mode not in ("wt", "conhost", "browser", "no_terminal"):
            raise ValueError("Unknown launch mode: " + launch_mode)
        from pyapp.DONT_CHANGE.scripts.terminal_window import configure, validate_close_mode

        validate_close_mode(settings, launch_mode)
        configure(settings, launch_mode)
        script = main_script_path(settings)
        if has_terminal:
            set_settings_colors()
            set_terminal_title(settings.program_name)
            set_terminal_app_id(app_id)
            if launch_mode in ("wt", "conhost"):
                from pyapp.DONT_CHANGE.scripts.taskbar_status import start

                start(settings)
        if not register_with_policy(settings, registry, run_dir):
            return
        registered = True
        # Windows groups a window with the pinned shortcut whose System.AppUserModel.ID matches.
        window_app_id = app_id + paths.NO_TERMINAL_APP_ID_SUFFIX if app_id and launch_mode == "no_terminal" else app_id
        app_python = json.loads(os.environ.pop("PYAPP_APP_PYTHON"))
        if not Path(script).is_file():
            raise FileNotFoundError(script)
        if (has_terminal and settings.enable_log_for_terminal_start) or (
            not has_terminal and settings.enable_log_for_no_terminal_start
        ):
            log_path = unique_log_path(
                get_log_path(
                    settings.log_path,
                    settings.log_path_is_relative_to_start_folder_if_relative,
                ),
                run_dir.name,
            )
        # In the run folder while the app runs; next to the log only if kept (keep_raw_output).
        raw_path = str(run_dir / paths.RAW_OUTPUT_FILE_NAME) if log_path else ""
        cwd = app_working_folder(settings, script)
        if launch_mode == "browser":
            from pyapp.DONT_CHANGE.browser_terminal import ui

            try:
                ui.request(
                    env_var=paths.BROWSER_UI_ENV_VAR,
                    info={"Working folder": cwd, "Current log file": log_path or "off"},
                )
            except (OSError, KeyError):
                note_ignored("browser terminal: report working folder and current log")
        config = {
            "script": script,
            "args": list(settings.args_for_main_py),
            "app_id": window_app_id,
            "app_root": paths.PYTHON_SCRIPTS_DIR,
            "traceback_lines_before": paths.traceback_lines_before,
            "traceback_lines_after": paths.traceback_lines_after,
            "print_prepend": settings.print_prepend,
            "input_prepend": settings.input_prepend,
            # The browser terminal's UI request file: input() announces itself there.
            "browser_ui": os.environ.get(paths.BROWSER_UI_ENV_VAR, "") if launch_mode == "browser" else "",
            "foreground_on_first_print": settings.foreground_on_first_print and has_terminal,
            "log_print_prepend": settings.log_print_prepend,
            "log_input_prepend": settings.log_input_prepend,
            "log_path": log_path,
            # Output that bypasses Python's streams is captured here and merged into the log.
            "native_output": raw_path,
            "traceback": str(run_dir / "traceback.json"),
            "result": str(run_dir / "result.json"),
            "ready": str(run_dir / "ready"),
        }
        atomic_json(run_dir / "wrapper.json", config)
        env = app_environment(settings, has_terminal, log_path, window_app_id)
        pump = None
        early_output = bytearray()
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        # From before the app exists: a Ctrl+C during its start-up must not end this watchdog.
        previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
        # Run the launcher helper or configured app interpreter with a controlled argument list.
        child = subprocess.Popen(  # noqa: S603
            [
                app_python["exe"],
                *app_python["flags"],
                "-X",
                "faulthandler",
                paths.SCRIPT_WRAPPER_PATH,
                "--config",
                str(run_dir / "wrapper.json"),
            ],
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE if log_path else None,
            stderr=subprocess.STDOUT if log_path else None,
        )
        registry.register(child.pid)
        if log_path:
            output = child.stdout
            if not isinstance(output, io.BufferedReader):
                raise RuntimeError("The child process did not provide a buffered output pipe.")

            def copy_output() -> None:
                """Copy combined child output to the terminal, keeping its last part for save_early_output."""
                try:
                    while True:
                        chunk = output.read1(65536)
                        if not chunk:
                            break
                        early_output.extend(chunk)
                        del early_output[:-EARLY_OUTPUT_LIMIT]
                        if has_terminal and sys.stdout is not None:
                            try:
                                sys.stdout.buffer.write(chunk)
                                sys.stdout.buffer.flush()
                            except OSError:
                                pass
                finally:
                    output.close()

            pump = threading.Thread(target=copy_output, daemon=True)
            pump.start()
        deadline = time.monotonic() + paths.WRAPPER_READY_TIMEOUT_SECONDS
        while not (run_dir / "ready").exists():
            if child.poll() is not None:
                break  # completion handling shows the wrapper's failure
            if time.monotonic() >= deadline:
                child.terminate()
                child.wait(timeout=10)
                raise TimeoutError("The application wrapper did not become ready")
            time.sleep(0.02)
        acknowledge(
            run_dir,
            status="started" if (run_dir / "ready").exists() else "failed",
            child_pid=child.pid,
            message="The application wrapper failed before it was ready; see the run logs.",
        )
        if has_terminal:
            try:
                set_terminal_icon(paths.ICON_PATH)
            except Exception:
                note_ignored("set_terminal_icon")
        if settings.replace_minimize_with_minimize_to_system_tray and launch_mode in ("conhost", "wt"):
            from pyapp.DONT_CHANGE.scripts.system_tray import MinimizeToTray
            from pyapp.DONT_CHANGE.scripts.taskbar_status import terminal_window

            stopping = threading.Event()

            def stop_run() -> None:
                if not stopping.is_set():
                    stopping.set()
                    threading.Thread(
                        target=stop_from_tray, args=(child, run_dir, settings.stop_timeout_seconds), daemon=True
                    ).start()

            try:
                hwnd = terminal_window()
                if not hwnd:
                    raise RuntimeError("No native terminal window was available for the system tray.")
                tray = MinimizeToTray(hwnd, settings.program_name, paths.ICON_PATH, stop_run)
                tray.start()
            except Exception:
                # Minimize remains ordinary if the shell cannot provide a recovery icon.
                note_ignored("start minimize-to-system-tray")
                from pyapp.DONT_CHANGE.scripts.console_tools import print_warn

                print_warn("Minimize to system tray is unavailable; the terminal stays accessible on the taskbar.")
        try:
            code = child.wait()
        finally:
            signal.signal(signal.SIGINT, previous)
        if pump:
            pump.join(timeout=5)
        save_early_output(raw_path, bytes(early_output))
        native = None
        try:
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            if result["wrapper_exit_code"] != code:
                raise ValueError("Abrupt exit during shutdown")
            mode = EXIT_MODE_FOR_WRAPPER_EXIT[code]
        except (OSError, ValueError, KeyError):
            # No (matching) completion report: native crash, os._exit, killed, ...
            mode, native = ExitMode.NO_REPORT, code
        # Worker threads can fail after main.py returned, while Python waits for them.
        background = run_dir / "traceback.json.background"
        if background.is_file() and successful_application_exit(mode, run_dir):
            atomic_json(
                run_dir / "traceback.json",
                json.loads(background.read_text(encoding="utf-8")),
            )
            mode = ExitMode.APP_EXIT
        keep_raw_output(raw_path, log_path, mode, run_dir)
        # Remove the registration before recovery can start a new instance.
        registry.remove()
        registered = False
        exit_handled = True
        if (run_dir / paths.STOP_REQUEST_FILE_NAME).exists():
            # Stopped by the Stop shortcut or a replacing launch: no sounds, menus or prompts.
            print_info("Stopped on request.")
            return
        handle_exit(settings, mode, app_id, has_terminal, log_path, script, run_dir, native)
    except Exception as error:
        try:
            save_report(error, __file__, str(run_dir / "traceback.json"))
        except Exception:
            note_ignored("save_report after a watchdog error")
        if not (run_dir / "startup.json").exists():
            acknowledge(run_dir, status="failed", message=str(error))
        (run_dir / "watchdog-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        # Before unregistering: until it has ended, the app must stay findable for Stop.
        end_started_app(child)
        if registered:
            registry.remove()
            registered = False
        if not exit_handled:
            handle_exit(settings, ExitMode.WATCHDOG_ERROR, app_id, has_terminal, log_path, script, run_dir)
    finally:
        if tray is not None:
            tray.close(activate=False)
        if registered:
            registry.remove()


if __name__ == "__main__":
    main()
