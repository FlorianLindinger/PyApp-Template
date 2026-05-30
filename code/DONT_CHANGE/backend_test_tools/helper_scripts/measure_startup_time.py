"""Measure startup times for PyApp Template shortcuts and compare to direct launch."""

import argparse
import ctypes
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import unicodedata

# ========================

# Add code dir for debug cases where this script is called on its own.
root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import developer_settings
from DONT_CHANGE.specific_scripts.common_variables import (
    backend_python_exe,
    env_var_to_signal_startup_time_measurement,
    frontend_python_exe,
    start_program_script,
    start_time_dummy_main_script,
)

# ========================

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(FILE_DIR)))
REPO_DIR = os.path.dirname(CODE_DIR)
WORK_DIR = os.path.normpath(FILE_DIR + "..\\.startup_time_markers")

VERSION_SCRIPT = (
    "import platform, sys; print(f'{platform.python_implementation()} {sys.version.split()[0]} ({sys.executable})')"
)

# ========================


def setting_to_shortcut_path(setting_name: str) -> str | None:
    """Resolve a shortcut setting into a repository shortcut path."""
    shortcut_name = getattr(developer_settings, setting_name, None)
    if shortcut_name in {None, False, ""}:
        return None
    return os.path.join(REPO_DIR, f"{shortcut_name}.lnk")


def shortcut_paths_from_developer_settings(args: argparse.Namespace) -> list[str]:
    """Collect shortcut paths enabled by developer settings."""
    shortcut_paths: list[str] = []
    shortcut_settings = [
        (args.measure_windows_terminal_shortcut, "windows_terminal_shortcut_name"),
        (args.measure_no_terminal_shortcut, "no_terminal_shortcut_name"),
        (args.measure_terminal_emulator_shortcut, "terminal_emulator_shortcut_name"),
        (args.measure_browser_shortcut, "browser_shortcut_name"),
    ]
    for enabled, setting_name in shortcut_settings:
        if not enabled:
            continue
        path = setting_to_shortcut_path(setting_name)
        if path is not None:
            shortcut_paths.append(path)
    return shortcut_paths


def start_program_modes_from_developer_settings(args: argparse.Namespace) -> list[tuple[str, str]]:
    """Collect direct start_program modes enabled by settings."""
    modes: list[tuple[str, str]] = []
    shortcut_settings = [
        (args.measure_windows_terminal_shortcut, "windows_terminal_shortcut_name", "terminal"),
        (args.measure_no_terminal_shortcut, "no_terminal_shortcut_name", "no_terminal"),
        (args.measure_terminal_emulator_shortcut, "terminal_emulator_shortcut_name", "terminal_emulator"),
        (args.measure_browser_shortcut, "browser_shortcut_name", "browser"),
    ]
    for enabled, setting_name, launch_mode in shortcut_settings:
        if enabled and setting_to_shortcut_path(setting_name) is not None:
            modes.append((f"Direct start_program {launch_mode}", launch_mode))
    return modes


def sanitize_app_id(input_string: str) -> str:
    """Sanitize the program name into a compact Windows AppUserModelID."""
    name = unicodedata.normalize("NFKD", input_string).encode("ascii", "ignore").decode("ascii").lower()
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"[^a-z0-9\-\.]", "", name)
    name = re.sub(r"-+", "-", name)
    name = re.sub(r"\.+", ".", name)
    name = name.strip("-.")
    if len(name) > 15:
        name = name.replace("-", "").replace(".", "")
    if len(name) > 15:
        name = name[:7] + name[-7:]
    return name


def shortcut_paths_from_explicit_args(shortcut_paths: list[str]) -> list[str]:
    """Resolve shortcut paths supplied on the command line."""
    return [os.path.abspath(os.path.expanduser(path)) for path in shortcut_paths]


def warn_missing_shortcuts(shortcuts: list[str]) -> None:
    """Print diagnostics for missing shortcut targets."""
    print("[Error] Missing shortcut(s):")
    for shortcut_path in shortcuts:
        print(f"  {shortcut_path}")
    print()
    print("Regenerate shortcuts or disable the matching measurement flag in the batch file.")


def safe_marker_name(label: str) -> str:
    """Convert a measurement label into a safe marker filename."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", label).strip("_.-") or "measurement"


def print_marker_help(target_script: str) -> None:
    """Print the marker help."""
    print()
    print("[Hint] The measured script must write the startup marker.")
    print(f"Expected marker script: {target_script}")
    print("For shortcut measurements, start_program.py receives the startup-measurement environment variable.")


def parse_args() -> argparse.Namespace:
    """Parse the args."""
    parser = argparse.ArgumentParser(description="Measure PyApp startup time.")
    parser.add_argument("runs", nargs="?", type=int, default=5)
    parser.add_argument("timeout", nargs="?", type=float, default=5.0)
    parser.add_argument("measure_windows_terminal_shortcut", nargs="?", type=int, default=1)
    parser.add_argument("measure_no_terminal_shortcut", nargs="?", type=int, default=1)
    parser.add_argument("measure_terminal_emulator_shortcut", nargs="?", type=int, default=0)
    parser.add_argument("measure_browser_shortcut", nargs="?", type=int, default=0)
    parser.add_argument("measure_direct_py_dist", nargs="?", type=int, default=1)
    parser.add_argument("measure_direct_global_py", nargs="?", type=int, default=1)
    parser.add_argument("run_setup_warmup", nargs="?", type=int, default=1)
    parser.add_argument("setup_timeout", nargs="?", type=float, default=600.0)
    parser.add_argument("measure_direct_start_program", nargs="?", type=int, default=1)
    parser.add_argument("--shortcut", action="append", default=[])
    parser.add_argument("--skip-launcher", action="store_true")
    parser.add_argument("--skip-start-program", action="store_true")
    parser.add_argument("--skip-py-dist", action="store_true")
    parser.add_argument("--skip-global", action="store_true")
    parser.add_argument("--skip-setup-warmup", action="store_true")
    args = parser.parse_args()
    args.measure_windows_terminal_shortcut = bool(args.measure_windows_terminal_shortcut)
    args.measure_no_terminal_shortcut = bool(args.measure_no_terminal_shortcut)
    args.measure_terminal_emulator_shortcut = bool(args.measure_terminal_emulator_shortcut)
    args.measure_browser_shortcut = bool(args.measure_browser_shortcut)
    args.skip_py_dist = args.skip_py_dist or not bool(args.measure_direct_py_dist)
    args.skip_global = args.skip_global or not bool(args.measure_direct_global_py)
    args.skip_start_program = args.skip_start_program or not bool(args.measure_direct_start_program)
    args.run_setup_warmup = bool(args.run_setup_warmup) and not args.skip_setup_warmup
    if args.setup_timeout <= 0:
        args.setup_timeout = None
    return args


def python_command(python_path: str, args: list[str]) -> list[str]:
    """Build a command for a Python executable or batch wrapper."""
    if python_path.lower().endswith((".bat", ".cmd")):
        return ["cmd.exe", "/d", "/c", "call", python_path, *args]
    return [python_path, *args]


def split_command_line_arguments(arguments: str) -> list[str]:
    """Split the command line arguments."""
    if arguments.strip() == "":
        return []

    command_line_to_argv = ctypes.windll.shell32.CommandLineToArgvW
    command_line_to_argv.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    command_line_to_argv.restype = ctypes.POINTER(ctypes.c_wchar_p)

    local_free = ctypes.windll.kernel32.LocalFree
    local_free.argtypes = [ctypes.c_void_p]
    local_free.restype = ctypes.c_void_p

    argc = ctypes.c_int()
    argv = command_line_to_argv(arguments, ctypes.byref(argc))
    if not argv:
        raise RuntimeError(f"Could not parse shortcut arguments: {arguments}")
    try:
        return [argv[index] for index in range(argc.value)]
    finally:
        local_free(argv)


def resolve_shortcut(shortcut_path: str) -> tuple[list[str], str]:
    """Resolve a Windows .lnk shortcut into a command and working directory."""
    if not os.path.exists(shortcut_path):
        raise FileNotFoundError(f'PyApp shortcut not found: "{shortcut_path}"')
    if os.name != "nt":
        raise RuntimeError(".lnk startup measurement is only supported on Windows.")

    command = (
        "$shortcutPath = $env:PYAPP_SHORTCUT_TO_RESOLVE; "
        "$shell = New-Object -ComObject WScript.Shell; "
        "$shortcut = $shell.CreateShortcut($shortcutPath); "
        "[pscustomobject]@{"
        "TargetPath=$shortcut.TargetPath;"
        "Arguments=$shortcut.Arguments;"
        "WorkingDirectory=$shortcut.WorkingDirectory"
        "} | ConvertTo-Json -Compress"
    )
    env = os.environ.copy()
    env["PYAPP_SHORTCUT_TO_RESOLVE"] = shortcut_path
    result = subprocess.run(  # noqa:S603
        ["powershell", "-NoProfile", "-Command", command],
        cwd=REPO_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=10.0,
        check=False,
    )
    output = (result.stdout or "").strip()
    if result.returncode != 0:
        raise RuntimeError(f"Failed to resolve shortcut {shortcut_path}: {output}")

    shortcut_data = json.loads(output)
    target_path = shortcut_data.get("TargetPath", "")
    if not target_path:
        raise RuntimeError(f'Shortcut has no target path: "{shortcut_path}"')

    arguments = split_command_line_arguments(shortcut_data.get("Arguments", ""))
    working_directory = shortcut_data.get("WorkingDirectory", "")
    cwd = working_directory if working_directory else REPO_DIR
    if target_path.lower().endswith((".bat", ".cmd")):
        return ["cmd.exe", "/d", "/c", "call", target_path, *arguments], cwd
    return [target_path, *arguments], cwd


def describe_python(python_path: str) -> str:
    """Return a description for the python."""
    try:
        result = subprocess.run(  # noqa:S603
            python_command(python_path, ["-c", VERSION_SCRIPT]),
            cwd=CODE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5.0,
            check=False,
        )
    except Exception as error:
        return f"unavailable ({error})"

    output = (result.stdout or "").strip()
    if result.returncode != 0:
        detail = f": {output}" if output else ""
        return f"unavailable, exit {result.returncode}{detail}"
    return output


def parse_marker(marker_path: str) -> dict[str, str]:
    """Parse the marker."""
    values: dict[str, str] = {}
    with open(marker_path, encoding="utf-8") as marker_file:
        for line in marker_file.read().splitlines():
            key, separator, value = line.partition("=")
            if separator:
                values[key] = value
    return values


def kill_process_tree(pid: int) -> None:
    """Terminate a process tree for measurement cleanup."""
    if pid <= 0:
        return
    if os.name == "nt":
        subprocess.run(  # noqa:S603
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.kill(pid, 9)
    except OSError:
        pass


def cleanup_process(proc: subprocess.Popen, marker_values: dict[str, str]) -> None:
    """Terminate and reap a process after a failed measurement."""
    marker_pid = marker_values.get("pid", "")
    if marker_pid.isdigit():
        kill_process_tree(int(marker_pid))
    if proc.poll() is None:
        kill_process_tree(proc.pid)
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            pass


def wait_for_marker(
    marker_path: str,
    timeout: float | None,
    proc: subprocess.Popen | None = None,
    *,
    fail_on_process_exit: bool = True,
) -> tuple[dict[str, str], float]:
    """Wait for the measured script to write its startup marker."""
    deadline = None if timeout is None else time.perf_counter() + timeout
    while deadline is None or time.perf_counter() < deadline:
        if os.path.exists(marker_path) and os.path.getsize(marker_path) > 0:
            return parse_marker(marker_path), time.perf_counter()
        if proc is not None and proc.poll() is not None and fail_on_process_exit:
            raise RuntimeError(f"Process exited with code {proc.returncode} before writing the startup marker.")
        time.sleep(0.005)
    raise TimeoutError(f'No startup marker was written to "{marker_path}" within {timeout:.1f}s.')


def raise_if_marker_error(marker_values: dict[str, str]) -> None:
    """Raise the if marker error."""
    error = marker_values.get("error", "")
    if error:
        raise RuntimeError(error)


def run_one(command: list[str], marker_path: str, timeout: float) -> float:
    """Run the one."""
    if os.path.exists(marker_path):
        os.remove(marker_path)

    env = os.environ.copy()
    start_ns = time.perf_counter_ns()
    env["PYAPP_STARTUP_BENCHMARK_MARKER"] = marker_path
    env["PYAPP_STARTUP_BENCHMARK_START_NS"] = str(start_ns)
    env[env_var_to_signal_startup_time_measurement] = "1"
    env["PYTHONPATH"] = CODE_DIR + os.pathsep + env.get("PYTHONPATH", "")

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.Popen(  # noqa:S603
        command,
        cwd=CODE_DIR,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    marker_values: dict[str, str] = {}
    try:
        marker_values, detected_at = wait_for_marker(marker_path, timeout, proc)
        raise_if_marker_error(marker_values)
        ready_ns = marker_values.get("ready_ns", "")
        if ready_ns.isdigit():
            return (int(ready_ns) - start_ns) / 1_000_000
        return (detected_at - (start_ns / 1_000_000_000)) * 1000
    finally:
        cleanup_process(proc, marker_values)
        cleanup_marker(marker_path)


def run_one_shortcut(
    shortcut_launch_command: list[str],
    shortcut_cwd: str,
    marker_path: str,
    timeout: float | None,
    *,
    show_output: bool = False,
) -> float:
    """Run the one shortcut."""
    if os.path.exists(marker_path):
        os.remove(marker_path)

    env = os.environ.copy()
    start_ns = time.perf_counter_ns()
    env["PYAPP_STARTUP_BENCHMARK_MARKER"] = marker_path
    env["PYAPP_STARTUP_BENCHMARK_START_NS"] = str(start_ns)
    env[env_var_to_signal_startup_time_measurement] = "1"
    env["PYTHONPATH"] = CODE_DIR + os.pathsep + env.get("PYTHONPATH", "")

    creationflags = 0 if show_output else subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    starter_proc = subprocess.Popen(  # noqa:S603
        shortcut_launch_command,
        cwd=shortcut_cwd,
        env=env,
        stdin=None if show_output else subprocess.DEVNULL,
        stdout=None if show_output else subprocess.DEVNULL,
        stderr=None if show_output else subprocess.DEVNULL,
        creationflags=creationflags,
    )

    marker_values: dict[str, str] = {}
    try:
        marker_values, detected_at = wait_for_marker(marker_path, timeout, starter_proc, fail_on_process_exit=False)
        raise_if_marker_error(marker_values)
        ready_ns = marker_values.get("ready_ns", "")
        if ready_ns.isdigit():
            return (int(ready_ns) - start_ns) / 1_000_000
        return (detected_at - (start_ns / 1_000_000_000)) * 1000
    finally:
        cleanup_process(starter_proc, marker_values)
        cleanup_marker(marker_path)


def cleanup_marker(marker_path: str) -> None:
    """Delete one startup measurement marker file if it exists."""
    try:
        if os.path.exists(marker_path):
            os.remove(marker_path)
    except OSError as error:
        print(f'[Warning] Could not remove startup marker "{marker_path}": {error}')


def cleanup_stale_markers() -> None:
    """Remove stale startup measurement marker files."""
    if not os.path.exists(WORK_DIR):
        return
    for file_name in os.listdir(WORK_DIR):
        if file_name.startswith("startup_marker_") and file_name.endswith(".txt"):
            cleanup_marker(os.path.join(WORK_DIR, file_name))


def measure(label: str, command: list[str], runs: int, timeout: float) -> list[float]:
    """Run repeated measurements for one launch target."""
    results: list[float] = []
    print(f"\n{label}")
    for run_index in range(1, runs + 1):
        marker_path = os.path.join(WORK_DIR, f"startup_marker_{safe_marker_name(label)}_{run_index}.txt")
        elapsed_ms = run_one(command, marker_path, timeout)
        results.append(elapsed_ms)
        print(f"  run {run_index}: {elapsed_ms:.1f} ms")
    return results


def measure_shortcut(
    label: str,
    shortcut_launch_command: list[str],
    shortcut_cwd: str,
    runs: int,
    timeout: float,
) -> list[float]:
    """Run repeated startup measurements for one shortcut target."""
    results: list[float] = []
    print(f"\n{label}")
    for run_index in range(1, runs + 1):
        marker_path = os.path.join(WORK_DIR, f"startup_marker_{safe_marker_name(label)}_{run_index}.txt")
        elapsed_ms = run_one_shortcut(
            shortcut_launch_command,
            shortcut_cwd,
            marker_path,
            timeout,
        )
        results.append(elapsed_ms)
        print(f"  run {run_index}: {elapsed_ms:.1f} ms")
    return results


def run_setup_warmup(
    shortcut_path: str,
    shortcut_launch_command: list[str],
    shortcut_cwd: str,
    timeout: float | None,
) -> None:
    """Run the setup warmup."""
    shortcut_name = os.path.basename(shortcut_path)
    marker_path = os.path.join(WORK_DIR, f"startup_marker_setup_{safe_marker_name(shortcut_name)}.txt")
    timeout_text = "no timeout" if timeout is None else f"{timeout:.0f}s timeout"
    print("\nSetup warmup")
    print(f"  shortcut: {shortcut_name}")
    print(f"  mode: unmeasured, {timeout_text}")
    print("  purpose: let ensure_frontend_packages finish setup before timed runs")
    elapsed_ms = run_one_shortcut(
        shortcut_launch_command,
        shortcut_cwd,
        marker_path,
        timeout,
        show_output=True,
    )
    print(f"  ready after {elapsed_ms:.1f} ms")


def print_summary(results: dict[str, list[float]]) -> None:
    """Print aggregate measurement statistics."""
    print("\nSummary")
    print("Mode                                      median      mean       min       max")
    print("----                                      ------      ----       ---       ---")
    for label, values in results.items():
        print(
            f"{label[:40]:40}"
            f"{statistics.median(values):9.1f}"
            f"{statistics.mean(values):10.1f}"
            f"{min(values):10.1f}"
            f"{max(values):10.1f}"
        )


def main() -> int:
    """Run this script's command-line workflow."""
    args = parse_args()
    if args.runs < 1:
        raise ValueError("--runs must be at least 1")

    target_script = os.path.normpath(start_time_dummy_main_script)
    shortcut_paths: list[str] = []
    if not args.skip_launcher:
        if args.shortcut:
            shortcut_paths = shortcut_paths_from_explicit_args(args.shortcut)
        else:
            shortcut_paths = shortcut_paths_from_developer_settings(args)

    if not os.path.exists(target_script):
        raise FileNotFoundError(f'Target script not found: "{target_script}"')
    if not args.skip_start_program and not os.path.exists(backend_python_exe):
        raise FileNotFoundError(f'Backend Python exe not found: "{backend_python_exe}"')
    if not args.skip_start_program and not os.path.exists(start_program_script):
        raise FileNotFoundError(f'start_program.py not found: "{start_program_script}"')
    if not args.skip_py_dist and not os.path.exists(frontend_python_exe):
        raise FileNotFoundError(f'Python distro exe not found: "{frontend_python_exe}"')

    os.makedirs(WORK_DIR, exist_ok=True)
    cleanup_stale_markers()

    shortcut_measurements: list[tuple[str, list[str], str]] = []
    missing_shortcuts = [shortcut_path for shortcut_path in shortcut_paths if not os.path.exists(shortcut_path)]
    if missing_shortcuts:
        warn_missing_shortcuts(missing_shortcuts)
        return 1

    for shortcut_path in shortcut_paths:
        shortcut_launch_command, shortcut_cwd = resolve_shortcut(shortcut_path)
        shortcut_measurements.append((shortcut_path, shortcut_launch_command, shortcut_cwd))

    measurements: list[tuple[str, list[str]]] = []
    app_id = sanitize_app_id(getattr(developer_settings, "program_name", ""))
    if not args.skip_start_program:
        for label, launch_mode in start_program_modes_from_developer_settings(args):
            measurements.append((label, [backend_python_exe, start_program_script, app_id, launch_mode]))
    if not args.skip_py_dist:
        measurements.append(("Direct py_dist python", python_command(frontend_python_exe, [target_script])))
    if not args.skip_global and shutil.which("py") is not None:
        measurements.append(("Direct global py", ["py", target_script]))

    print(f"Target script: {target_script}")
    print(f"Runs per mode: {args.runs}")
    print("Setup warmup: " + ("enabled" if args.run_setup_warmup and shortcut_measurements else "skipped"))
    if shortcut_measurements:
        print("PyApp shortcuts:")
        for shortcut_path, shortcut_launch_command, shortcut_cwd in shortcut_measurements:
            print(f"  {shortcut_path}")
            print(f"    target command: {subprocess.list2cmdline(shortcut_launch_command)}")
            print(f"    working directory: {shortcut_cwd}")
    else:
        print("PyApp shortcuts: skipped")

    print(
        "This uses the .lnk files as the source of truth, then launches their stored targets/arguments with benchmark env."
    )
    print("That includes the shortcut stub, start_program.py, and configured terminal/script path.")
    print("Direct start_program rows skip the shortcut/cmd/bat layer and start from start_program.py.")
    print("Timing point: import of startup_benchmark_marker in the target script.")

    if args.skip_start_program:
        print("direct start_program: skipped")
    else:
        print(f"direct start_program Python: {describe_python(backend_python_exe)}")

    if args.skip_py_dist:
        print("py_dist Python: skipped")
    else:
        print(f"py_dist Python: {describe_python(frontend_python_exe)}")

    if shutil.which("py") is None:
        print("global py: unavailable (not on PATH)")
    else:
        print("global py: skipped" if args.skip_global else f"global py: {describe_python('py')}")

    if args.run_setup_warmup and shortcut_measurements:
        shortcut_path, shortcut_launch_command, shortcut_cwd = shortcut_measurements[0]
        try:
            run_setup_warmup(shortcut_path, shortcut_launch_command, shortcut_cwd, args.setup_timeout)
        except TimeoutError as error:
            print(f"\n[Error] setup warmup: {error}")
            print_marker_help(target_script)
            return 1
        except (FileNotFoundError, RuntimeError) as error:
            print(f"\n[Error] setup warmup: {error}")
            return 1

    results: dict[str, list[float]] = {}
    for shortcut_path, shortcut_launch_command, shortcut_cwd in shortcut_measurements:
        shortcut_name = os.path.basename(shortcut_path)
        try:
            results[shortcut_name] = measure_shortcut(
                shortcut_name,
                shortcut_launch_command,
                shortcut_cwd,
                args.runs,
                args.timeout,
            )
        except TimeoutError as error:
            print(f"\n[Error] {shortcut_name}: {error}")
            print_marker_help(target_script)
            return 1
        except (FileNotFoundError, RuntimeError) as error:
            print(f"\n[Error] {shortcut_name}: {error}")
            return 1

    for label, command in measurements:
        try:
            results[label] = measure(label, command, args.runs, args.timeout)
        except TimeoutError as error:
            print(f"\n[Error] {label}: {error}")
            print_marker_help(target_script)
            return 1
        except (FileNotFoundError, RuntimeError) as error:
            if label == "Direct global py":
                print(f"\n[Warning] Skipping {label}: {error}")
                continue
            print(f"\n[Error] {label}: {error}")
            return 1

    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
