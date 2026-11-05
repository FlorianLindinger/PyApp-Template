"""Own one application run: instance policy, logging, the app process and completion handling."""

from __future__ import annotations

import io
import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from backend import developer_settings as settings
from backend.DONT_CHANGE.scripts.console_tools import (
    set_terminal_app_id,
    set_terminal_icon,
    set_terminal_title,
)
from backend.DONT_CHANGE.scripts.instance_policy import decide
from backend.DONT_CHANGE.scripts.launcher_ui import get_log_path, set_terminal_colors
from backend.DONT_CHANGE.scripts.runtime._pyapp_protocol import (
    ExitMode,
    WrapperExit,
    exit_code_is_success,
    save_report,
)
from backend.DONT_CHANGE.scripts.runtime_state import (
    ProcessRegistry,
    atomic_json,
    clean_python_environment,
    unique_log_path,
)
from backend.DONT_CHANGE import backend_settings as paths


def acknowledge(run_dir, **payload):
    """Atomically publish watchdog startup status for the waiting launcher."""
    atomic_json(run_dir / "startup.json", payload)


def successful_application_exit(mode, run_dir):
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


def handle_exit(mode, app_id, has_terminal, log_path, script, run_dir, native_code=None):
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
        str(int(mode)),
        app_id,
        "false" if has_terminal else "true",
        log_path,
        script,
    ]
    success = successful_application_exit(mode, run_dir)
    if not has_terminal and success and settings.close_after_success:
        # Successful hidden runs perform their completion actions without a console.
        env["PYAPP_SILENT_EXIT"] = "1"
        subprocess.run(args, env=env, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
    elif has_terminal:
        subprocess.run(args, env=env, check=False)
    else:
        subprocess.run(["conhost.exe", *args], env=env, check=False, creationflags=subprocess.CREATE_NEW_CONSOLE)


def register_with_policy(registry, has_terminal, run_dir):
    """Apply instance_policy and register; dialogs are shown without holding the registry lock."""
    policy = settings.instance_policy
    while True:
        with registry.lock():
            records, _ = registry.records()
            if not records or policy == "allow":
                registry.register()
                return True
            if policy == "replace":
                _, _, errors = registry.stop()
                if errors:
                    raise RuntimeError("Could not stop existing instances: " + "; ".join(errors))
                registry.register()
                return True
        decision = decide(policy, records, settings.program_name)
        if decision == "cancel":
            acknowledge(run_dir, status="cancelled")
            return False
        policy = "replace"


def main():
    """Own registration, launch, logging and completion handling for one application run."""
    app_id, launch_mode = sys.argv[1:3]
    if app_id == paths.EMPTY_ARG_INDICATOR:
        app_id = ""
    run_dir = Path(os.environ["PYAPP_RUN_DIR"])
    has_terminal = launch_mode in ("wt", "conhost")
    registry = ProcessRegistry(paths.PROCESS_ID_FILE_PATH)
    script = paths.MAIN_PY_SCRIPT_PATH
    log_path = ""
    registered = False
    exit_handled = False
    try:
        if launch_mode not in ("wt", "conhost", "no_terminal"):
            raise ValueError("Unknown launch mode: " + launch_mode)
        if has_terminal:
            set_terminal_colors()
            set_terminal_title(settings.program_name)
            set_terminal_app_id(app_id)
        if not register_with_policy(registry, has_terminal, run_dir):
            return
        registered = True
        # Windows group a window with the pinned shortcut whose System.AppUserModel.ID matches.
        window_app_id = app_id + paths.NO_TERMINAL_APP_ID_SUFFIX if app_id and launch_mode == "no_terminal" else app_id
        app_python = json.loads(os.environ.pop("PYAPP_APP_PYTHON"))
        if not Path(script).is_file():
            raise FileNotFoundError(script)
        if (has_terminal and settings.enable_log_for_Windows_terminal_start) or (
            not has_terminal and settings.enable_log_for_no_terminal_start
        ):
            log_path = unique_log_path(
                get_log_path(settings.log_path, settings.log_path_is_relative_to_start_folder_if_relative),
                run_dir.name,
            )
        cwd = os.environ.get("PYAPP_START_DIR", os.getcwd()) if settings.start_in_shortcut_folder else str(Path(script).parent)
        config = {
            "script": script,
            "args": list(settings.args_for_main_py),
            "app_id": window_app_id,
            "app_root": paths.PYTHON_SCRIPTS_DIR,
            "traceback_extra_lines": settings.traceback_extra_lines,
            "print_prepend": settings.print_prepend,
            "input_prepend": settings.input_prepend,
            "log_print_prepend": settings.log_print_prepend,
            "log_input_prepend": settings.log_input_prepend,
            "log_path": log_path,
            "overwrite_log": settings.overwrite_log,
            "traceback": str(run_dir / "traceback.json"),
            "result": str(run_dir / "result.json"),
            "ready": str(run_dir / "ready"),
        }
        atomic_json(run_dir / "wrapper.json", config)
        # The user's own interpreter keeps its PYTHON* settings; a project venv is isolated.
        isolated = app_python["kind"] == "venv"
        env = clean_python_environment(isolated=isolated)
        for key in list(env):
            if key.startswith("PYAPP_"):
                env.pop(key)
        env["PROGRAM_NAME"] = settings.program_name
        env["ICON_PATH"] = paths.ICON_PATH
        env["PROGRAM_HAS_TERMINAL"] = "1" if has_terminal else "0"
        env["LOG_PATH"] = log_path
        env["APP_ID"] = window_app_id
        env["WDIR_IS_SCRIPT_DIR"] = "0" if settings.start_in_shortcut_folder else "1"
        env["CLOSE_AFTER_FAILURE"] = "1" if settings.close_after_failure else "0"
        env["CLOSE_AFTER_SUCCESS"] = "1" if settings.close_after_success else "0"
        raw_stream = None
        pump = None
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            raw_stream = open(log_path + ".output.log", "wb")
        try:
            child = subprocess.Popen(
                [app_python["exe"], *app_python["flags"], "-X", "faulthandler", paths.FRONTEND_SCRIPT_WRAPPER_PATH, "--config", str(run_dir / "wrapper.json")],
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE if raw_stream else None,
                stderr=subprocess.STDOUT if raw_stream else None,
            )
            registry.register(child.pid)
            if raw_stream:
                output = child.stdout
                assert isinstance(output, io.BufferedReader)

                def copy_output():
                    """Copy combined child output to the raw log and the terminal."""
                    try:
                        while True:
                            chunk = output.read1(65536)
                            if not chunk:
                                break
                            raw_stream.write(chunk)
                            raw_stream.flush()
                            if has_terminal and sys.stdout is not None:
                                try:
                                    sys.stdout.buffer.write(chunk)
                                    sys.stdout.buffer.flush()
                                except OSError:
                                    pass
                    finally:
                        output.close()
                        raw_stream.close()

                pump = threading.Thread(target=copy_output, daemon=True)
                pump.start()
            deadline = time.monotonic() + 30
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
                    pass
            previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
            try:
                code = child.wait()
            finally:
                signal.signal(signal.SIGINT, previous)
            if pump:
                pump.join(timeout=5)
            mode, native = code, None
            try:
                result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
                if result["wrapper_exit_code"] != code:
                    raise ValueError("Abrupt exit during shutdown")
            except (OSError, ValueError, KeyError):
                mode, native = ExitMode.NO_REPORT, code
            if mode not in (WrapperExit.SUCCESS, WrapperExit.APP_FAILED, WrapperExit.WRAPPER_FAILED, ExitMode.NO_REPORT):
                mode, native = ExitMode.NO_REPORT, code
            # Worker threads can fail after main.py returned, while Python waits for them.
            background = run_dir / "traceback.json.background"
            if background.is_file() and successful_application_exit(mode, run_dir):
                atomic_json(run_dir / "traceback.json", json.loads(background.read_text(encoding="utf-8")))
                mode = ExitMode.APP_EXIT
            # Remove the registration before recovery can start a new instance.
            registry.remove()
            registered = False
            exit_handled = True
            handle_exit(mode, app_id, has_terminal, log_path, script, run_dir, native)
        finally:
            if raw_stream and pump is None:
                raw_stream.close()
    except Exception as error:
        try:
            save_report(error, __file__, str(run_dir / "traceback.json"))
        except Exception:
            pass
        if not (run_dir / "startup.json").exists():
            acknowledge(run_dir, status="failed", message=str(error))
        (run_dir / "watchdog-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        if registered:
            registry.remove()
            registered = False
        if not exit_handled:
            handle_exit(ExitMode.WATCHDOG_ERROR, app_id, has_terminal, log_path, script, run_dir)
    finally:
        if registered:
            registry.remove()


if __name__ == "__main__":
    main()
