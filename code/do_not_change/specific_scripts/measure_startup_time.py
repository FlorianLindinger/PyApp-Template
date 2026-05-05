import argparse
import ctypes
import json
import os
import shutil
import statistics
import subprocess
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DO_NOT_CHANGE_DIR = SCRIPT_DIR.parent
CODE_DIR = DO_NOT_CHANGE_DIR.parent
REPO_DIR = CODE_DIR.parent
WORK_DIR = DO_NOT_CHANGE_DIR / "DO_NOT_SYNC" / "startup_time"
DEVELOPER_SETTINGS_PATH = CODE_DIR / "developer_settings.py"
PYAPP_SHORTCUT = REPO_DIR / "PyApp-Template.lnk"
VENV_PYTHON = CODE_DIR / "py_env" / "virt_env" / "Portable_Scripts" / "python.bat"
PY_DIST_PYTHON = CODE_DIR / "py_env" / "py_dist" / "python.exe"
VERSION_SCRIPT = (
    "import platform, sys; print(f'{platform.python_implementation()} {sys.version.split()[0]} ({sys.executable})')"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure PyApp startup time to the marker in the main script.")
    parser.add_argument("--runs", type=int, default=10, help="Runs per startup mode. Default: 10.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Seconds to wait for the startup marker.")
    parser.add_argument("--skip-launcher", action="store_true", help="Skip the PyApp-Template.lnk measurement.")
    parser.add_argument("--skip-global", action="store_true", help="Skip direct global 'py' measurement.")
    parser.add_argument(
        "--shortcut",
        default=str(PYAPP_SHORTCUT),
        help=f'PyApp shortcut to launch. Default: "{PYAPP_SHORTCUT}".',
    )
    return parser.parse_args()


def load_developer_setting(name: str, default):
    import importlib.util

    spec = importlib.util.spec_from_file_location("developer_settings", DEVELOPER_SETTINGS_PATH)
    if spec is None or spec.loader is None:
        return default
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name, default)


def python_command(python_path: Path | str, args: list[str]) -> list[str]:
    python_text = str(python_path)
    if python_text.lower().endswith((".bat", ".cmd")):
        return ["cmd.exe", "/d", "/c", "call", python_text, *args]
    return [python_text, *args]


def split_command_line_arguments(arguments: str) -> list[str]:
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


def resolve_shortcut(shortcut_path: Path) -> tuple[list[str], Path]:
    if not shortcut_path.exists():
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
    env["PYAPP_SHORTCUT_TO_RESOLVE"] = str(shortcut_path)
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
    cwd = Path(working_directory) if working_directory else REPO_DIR
    return [target_path, *arguments], cwd


def describe_python(python_path: Path | str) -> str:
    try:
        result = subprocess.run( #noqa:S603
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


def parse_marker(marker_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in marker_path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    return values


def kill_process_tree(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        subprocess.run( #noqa:S603
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
    marker_path: Path,
    timeout: float,
    proc: subprocess.Popen | None = None,
    *,
    fail_on_process_exit: bool = True,
) -> tuple[dict[str, str], float]:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if marker_path.exists() and marker_path.stat().st_size > 0:
            return parse_marker(marker_path), time.perf_counter()
        if proc is not None and proc.poll() is not None and (fail_on_process_exit or proc.returncode != 0):
            raise RuntimeError(f"Process exited with code {proc.returncode} before writing the startup marker.")
        time.sleep(0.005)
    raise TimeoutError(f'No startup marker was written to "{marker_path}" within {timeout:.1f}s.')


def run_one(command: list[str], marker_path: Path, timeout: float) -> float:
    if marker_path.exists():
        marker_path.unlink()

    env = os.environ.copy()
    start_ns = time.perf_counter_ns()
    env["PYAPP_STARTUP_BENCHMARK_MARKER"] = str(marker_path)
    env["PYAPP_STARTUP_BENCHMARK_START_NS"] = str(start_ns)
    env["PYTHONPATH"] = str(CODE_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.Popen( #noqa:S603
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
        ready_ns = marker_values.get("ready_ns", "")
        if ready_ns.isdigit():
            return (int(ready_ns) - start_ns) / 1_000_000
        return (detected_at - (start_ns / 1_000_000_000)) * 1000
    finally:
        cleanup_process(proc, marker_values)


def run_one_shortcut(
    shortcut_launch_command: list[str],
    shortcut_cwd: Path,
    marker_path: Path,
    timeout: float,
) -> float:
    if marker_path.exists():
        marker_path.unlink()

    env = os.environ.copy()
    start_ns = time.perf_counter_ns()
    env["PYAPP_STARTUP_BENCHMARK_MARKER"] = str(marker_path)
    env["PYAPP_STARTUP_BENCHMARK_START_NS"] = str(start_ns)
    env["PYTHONPATH"] = str(CODE_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    starter_proc = subprocess.Popen( #noqa:S603
        shortcut_launch_command,
        cwd=shortcut_cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    marker_values: dict[str, str] = {}
    try:
        marker_values, detected_at = wait_for_marker(marker_path, timeout, starter_proc, fail_on_process_exit=False)
        ready_ns = marker_values.get("ready_ns", "")
        if ready_ns.isdigit():
            return (int(ready_ns) - start_ns) / 1_000_000
        return (detected_at - (start_ns / 1_000_000_000)) * 1000
    finally:
        cleanup_process(starter_proc, marker_values)


def measure(label: str, command: list[str], runs: int, timeout: float) -> list[float]:
    results: list[float] = []
    print(f"\n{label}")
    for run_index in range(1, runs + 1):
        marker_path = WORK_DIR / f"startup_marker_{label.lower().replace(' ', '_')}_{run_index}.txt"
        elapsed_ms = run_one(command, marker_path, timeout)
        results.append(elapsed_ms)
        print(f"  run {run_index}: {elapsed_ms:.1f} ms")
    return results


def measure_shortcut(
    label: str,
    shortcut_launch_command: list[str],
    shortcut_cwd: Path,
    runs: int,
    timeout: float,
) -> list[float]:
    results: list[float] = []
    print(f"\n{label}")
    for run_index in range(1, runs + 1):
        marker_path = WORK_DIR / f"startup_marker_{label.lower().replace(' ', '_')}_{run_index}.txt"
        elapsed_ms = run_one_shortcut(
            shortcut_launch_command,
            shortcut_cwd,
            marker_path,
            timeout,
        )
        results.append(elapsed_ms)
        print(f"  run {run_index}: {elapsed_ms:.1f} ms")
    return results


def print_summary(results: dict[str, list[float]]) -> None:
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


def print_marker_help(target_script: Path) -> None:
    print("\nThe target script must write the startup marker. Add or move this near the startup point to measure:")
    print(
        """
from do_not_change.specific_scripts.startup_benchmark_marker import mark_startup_time
""".strip()
    )
    print(f"\nCurrent target script: {target_script}")


def main() -> int:
    args = parse_args()
    if args.runs < 1:
        raise ValueError("--runs must be at least 1")

    python_code_name= load_developer_setting("python_code_name", "main_code.py")
    target_script = CODE_DIR / python_code_name
    shortcut_path = Path(args.shortcut).expanduser()
    if not shortcut_path.is_absolute():
        shortcut_path = (REPO_DIR / shortcut_path).resolve()

    if not target_script.exists():
        raise FileNotFoundError(f'Target script not found: "{target_script}"')
    if not PY_DIST_PYTHON.exists():
        raise FileNotFoundError(f'Python distro exe not found: "{PY_DIST_PYTHON}"')

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    shortcut_launch_command: list[str] | None = None
    shortcut_cwd = REPO_DIR
    if not args.skip_launcher:
        shortcut_launch_command, shortcut_cwd = resolve_shortcut(shortcut_path)

    measurements: list[tuple[str, list[str]]] = [
        ("Direct py_dist python", python_command(PY_DIST_PYTHON, [str(target_script)]))
    ]
    if not args.skip_global and shutil.which("py") is not None:
        measurements.append(("Direct global py", ["py", str(target_script)]))

    print(f"Target script: {target_script}")
    print(f"Runs per mode: {args.runs}")
    print(f"PyApp shortcut: {shortcut_path}")
    if shortcut_launch_command is not None:
        print(f"Shortcut target command: {subprocess.list2cmdline(shortcut_launch_command)}")
        print(f"Shortcut working directory: {shortcut_cwd}")
    print(
        "This uses the .lnk file as the source of truth, then launches its stored target/arguments with benchmark env."
    )
    print("That includes the shortcut stub, start_program.py, and configured terminal/script path.")
    print("Timing point: import of startup_benchmark_marker in the target script.")
    print(f"py_dist Python: {describe_python(PY_DIST_PYTHON)}")
    if shutil.which("py") is None:
        print("global py: unavailable (not on PATH)")
    else:
        print(f"global py: {describe_python('py')}")

    results: dict[str, list[float]] = {}
    if not args.skip_launcher:
        try:
            assert shortcut_launch_command is not None
            results[shortcut_path.name] = measure_shortcut(
                shortcut_path.name,
                shortcut_launch_command,
                shortcut_cwd,
                args.runs,
                args.timeout,
            )
        except TimeoutError as error:
            print(f"\n[Error] {shortcut_path.name}: {error}")
            print_marker_help(target_script)
            return 1
        except (FileNotFoundError, RuntimeError) as error:
            print(f"\n[Error] {shortcut_path.name}: {error}")
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
