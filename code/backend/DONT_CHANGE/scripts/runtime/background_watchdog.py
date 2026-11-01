"""Own one application run and its child process without killing caller shells."""

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
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from backend import developer_settings as settings
from backend.DONT_CHANGE.scripts.console_tools import (
    set_terminal_app_id,
    set_terminal_icon,
    set_terminal_title,
)
from backend.DONT_CHANGE.scripts.launcher_ui import get_log_path, set_terminal_colors
from backend.DONT_CHANGE.scripts.runtime_state import (
    ProcessRegistry,
    atomic_json,
    clean_python_environment,
    resolve_global_python,
    unique_log_path,
)
from backend.DONT_CHANGE.settings import backend_settings as paths


def confirm_replace(has_terminal):
    """Ask in the terminal or a Windows dialog whether existing instances should be stopped."""
    if has_terminal:
        return input(
            "Close the existing instance(s) and start again? [y/N] "
        ).strip().lower() in {"y", "yes"}
    import ctypes

    return (
        ctypes.windll.user32.MessageBoxW(
            None,
            "Close existing instances and start again?",
            settings.program_name,
            0x24,
        )
        == 6
    )


def acknowledge(run_dir, **payload):
    """Atomically publish watchdog startup status for the waiting launcher."""
    atomic_json(run_dir / "startup.json", payload)


def handle_exit(
    mode, app_id, has_terminal, log_path, script, run_dir, native_code=None
):
    """Run completion handling in the current, hidden or newly created console as needed."""
    env = os.environ.copy()
    env["PYAPP_RUN_DIR"] = str(run_dir)
    if native_code is not None:
        env["PYAPP_UNEXPECTED_EXIT"] = str(native_code)
    args = [
        paths.BACKEND_PYTHON_EXE,
        paths.PROCESS_EXIT_PATH,
        str(mode),
        app_id,
        "false" if has_terminal else "true",
        log_path,
        script,
    ]
    # Successful hidden runs perform configured completion actions without opening a console.
    success = mode == 0
    if mode == 1:
        try:
            payload = json.loads(
                (run_dir / "traceback.json").read_text(encoding="utf-8")
            )
            entry = payload["traceback"][-1]
            code = payload.get("system_exit_code")
            success = entry["type"] == "SystemExit" and (
                code is None or isinstance(code, int) and code == 0
            )
        except (OSError, ValueError, KeyError, IndexError):
            pass
    hidden = not has_terminal and success and settings.close_after_success
    if hidden:
        env["PYAPP_SILENT_EXIT"] = "1"
        subprocess.run(
            args, env=env, check=False, creationflags=subprocess.CREATE_NO_WINDOW
        )
    elif has_terminal:
        subprocess.run(args, env=env, check=False)
    else:
        subprocess.run(
            ["conhost.exe", *args],
            env=env,
            check=False,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )


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
    child = None
    registered = False
    try:
        if launch_mode not in ("wt", "conhost", "no_terminal"):
            raise ValueError("Unknown launch mode: " + launch_mode)
        if has_terminal:
            set_terminal_colors()
            set_terminal_title(settings.program_name)
            set_terminal_app_id(app_id)
        # Check and register under the same interprocess lock; never count our own PID.
        with registry.lock():
            records, _ = registry.records()
            if records and (
                settings.close_already_running_instances_on_start
                or settings.prevent_start_if_already_running
            ):
                replace = settings.close_already_running_instances_on_start
                if not replace and settings.prompt_to_close_existing_instances:
                    replace = confirm_replace(has_terminal)
                if not replace:
                    acknowledge(run_dir, status="cancelled")
                    return
                _, _, errors = registry.stop()
                if errors:
                    raise RuntimeError(
                        "Could not stop existing instances: " + "; ".join(errors)
                    )
            registry.register()
            registered = True
        # Private diagnostic protocol; the external benchmark supplies its probe.
        benchmark_script = os.environ.pop(
            "PYAPP_TEMPLATE_ACTIVE_STARTUP_TIME_MEASUREMENT", ""
        )
        measuring = bool(benchmark_script)
        if measuring:
            script = benchmark_script
        if not Path(script).is_file():
            raise FileNotFoundError(script)
        if not isinstance(settings.args_for_main_py, list) or not all(
            isinstance(a, str) for a in settings.args_for_main_py
        ):
            raise ValueError("args_for_main_py must be a list of strings")
        args = list(settings.args_for_main_py)
        python = (
            resolve_global_python()
            if settings.use_global_python
            else paths.FRONTEND_PYTHON_EXE
        )
        if (has_terminal and settings.enable_log_for_Windows_terminal_start) or (
            not has_terminal and settings.enable_log_for_no_terminal_start
        ):
            log_path = unique_log_path(
                get_log_path(
                    settings.log_path,
                    settings.log_path_is_relative_to_start_folder_if_relative,
                ),
                run_dir.name,
            )
        cwd = (
            os.environ.get("PYAPP_START_DIR", os.getcwd())
            if settings.start_in_shortcut_folder
            else str(Path(script).parent)
        )
        config: dict[str, object] = {
            "script": script,
            "args": args,
            "app_id": app_id,
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
        if measuring:
            config["benchmark"] = {
                k: v
                for k, v in os.environ.items()
                if k.startswith("PYAPP_STARTUP_BENCHMARK_")
            }
        atomic_json(run_dir / "wrapper.json", config)
        env = clean_python_environment()
        # Keep launcher protocol private; expose public metadata as a launch-time snapshot.
        for key in list(env):
            if key.startswith("PYAPP_"):
                env.pop(key)
        env["PROGRAM_NAME"] = settings.program_name
        env["ICON_PATH"] = paths.ICON_PATH
        env["PROGRAM_HAS_TERMINAL"] = "1" if has_terminal else "0"
        env["LOG_PATH"] = log_path
        env["APP_ID"] = app_id
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
                [
                    python,
                    "-E",
                    "-s",
                    "-X",
                    "faulthandler",
                    paths.FRONTEND_SCRIPT_WRAPPER_PATH,
                    "--config",
                    str(run_dir / "wrapper.json"),
                ],
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE if raw_stream else None,
                stderr=subprocess.STDOUT if raw_stream else None,
            )
            registry.register(child.pid)
            if raw_stream:
                assert child.stdout is not None
                # Popen's binary PIPE is buffered; read1 keeps live logs responsive.
                output = cast(io.BufferedReader, child.stdout)

                def copy_output():
                    """Copy combined child output to the raw log and optional terminal, closing streams on exit."""
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
                    break  # The exit handler will show the wrapper initialization failure.
                if time.monotonic() >= deadline:
                    child.terminate()
                    child.wait(timeout=10)
                    raise TimeoutError("Application wrapper did not become ready")
                time.sleep(0.02)
            acknowledge(
                run_dir,
                status="started" if (run_dir / "ready").exists() else "failed",
                child_pid=child.pid,
                message="Application wrapper failed before it was ready; see the run logs.",
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
                result = json.loads(
                    (run_dir / "result.json").read_text(encoding="utf-8")
                )
                if result["wrapper_exit_code"] != code:
                    raise ValueError("Abrupt exit during shutdown")
            except (OSError, ValueError, KeyError):
                mode, native = 5, code
            # Remove registration before recovery can start a new instance.
            registry.remove()
            registered = False
            handle_exit(mode, app_id, has_terminal, log_path, script, run_dir, native)
        finally:
            if raw_stream and pump is None:
                raw_stream.close()
    except Exception as error:
        from backend.DONT_CHANGE.scripts.runtime.script_wrapper import (
            save_traceback,
        )

        save_traceback(error, __file__, str(run_dir / "traceback.json"))
        if not (run_dir / "startup.json").exists():
            acknowledge(run_dir, status="failed", message=str(error))
        # Preserve the original traceback even if the Rich presentation fails.
        (run_dir / "watchdog-error.txt").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        if registered:
            registry.remove()
            registered = False
        handle_exit(4, app_id, has_terminal, log_path, script, run_dir)
    finally:
        if registered:
            registry.remove()


if __name__ == "__main__":
    main()
