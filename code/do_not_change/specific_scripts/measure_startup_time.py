from __future__ import annotations

import argparse
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import unicodedata
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DO_NOT_CHANGE_DIR = SCRIPT_DIR.parent
CODE_DIR = DO_NOT_CHANGE_DIR.parent
WORK_DIR = DO_NOT_CHANGE_DIR / "DO_NOT_SYNC" / "startup_time"
DEVELOPER_SETTINGS_PATH = CODE_DIR / "developer_settings.py"
SCRIPT_WRAPPER_PATH = SCRIPT_DIR / "script_wrapper.py"
VENV_PYTHON = CODE_DIR / "py_env" / "virt_env" / "Portable_Scripts" / "python.bat"
PY_DIST_PYTHON = CODE_DIR / "py_env" / "py_dist" / "python.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure PyApp startup time to the marker in the main script.")
    parser.add_argument("--runs", type=int, default=5, help="Runs per startup mode. Default: 5.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Seconds to wait for the startup marker.")
    parser.add_argument("--skip-launcher", action="store_true", help="Skip the PyApp wrapper/no-terminal measurement.")
    parser.add_argument("--skip-global", action="store_true", help="Skip direct global 'py' measurement.")
    return parser.parse_args()


def load_developer_setting(name: str, default):
    import importlib.util

    spec = importlib.util.spec_from_file_location("developer_settings", DEVELOPER_SETTINGS_PATH)
    if spec is None or spec.loader is None:
        return default
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name, default)


def sanitize_app_id(input_string: str) -> str:
    name = unicodedata.normalize("NFKD", input_string).encode("ascii", "ignore").decode("ascii").lower()
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"[^a-z0-9\-\.]", "", name)
    name = re.sub(r"-+", "-", name)
    name = re.sub(r"\.+", ".", name)
    return name.strip("-.") or "pyapp-template"


def python_command(python_path: Path | str, args: list[str]) -> list[str]:
    python_text = str(python_path)
    if python_text.lower().endswith((".bat", ".cmd")):
        return ["cmd.exe", "/d", "/c", "call", python_text, *args]
    return [python_text, *args]


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
        subprocess.run(
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


def wait_for_marker(marker_path: Path, timeout: float, proc: subprocess.Popen) -> tuple[dict[str, str], float]:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if marker_path.exists() and marker_path.stat().st_size > 0:
            return parse_marker(marker_path), time.perf_counter()
        if proc.poll() is not None:
            raise RuntimeError(f"Process exited with code {proc.returncode} before writing the startup marker.")
        time.sleep(0.005)
    raise TimeoutError(f'No startup marker was written to "{marker_path}" within {timeout:.1f}s.')


def run_one(label: str, command: list[str], marker_path: Path, timeout: float) -> float:
    if marker_path.exists():
        marker_path.unlink()

    env = os.environ.copy()
    start_ns = time.perf_counter_ns()
    env["PYAPP_STARTUP_BENCHMARK_MARKER"] = str(marker_path)
    env["PYAPP_STARTUP_BENCHMARK_START_NS"] = str(start_ns)
    env["PYTHONPATH"] = str(CODE_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.Popen(
        command,
        cwd=CODE_DIR,
        env=env,
        stdin=subprocess.DEVNULL,
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


def measure(label: str, command: list[str], runs: int, timeout: float) -> list[float]:
    results: list[float] = []
    print(f"\n{label}")
    for run_index in range(1, runs + 1):
        marker_path = WORK_DIR / f"startup_marker_{label.lower().replace(' ', '_')}_{run_index}.txt"
        elapsed_ms = run_one(label, command, marker_path, timeout)
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

mark_startup_time()
""".strip()
    )
    print(f"\nCurrent target script: {target_script}")


def main() -> int:
    args = parse_args()
    if args.runs < 1:
        raise ValueError("--runs must be at least 1")

    python_code_name = load_developer_setting("python_code_name", "main_code.py")
    program_name = load_developer_setting("program_name", "PyApp-Template")
    start_in_shortcut_folder = load_developer_setting("start_in_shortcut_folder", False)
    target_script = CODE_DIR / python_code_name
    app_id = sanitize_app_id(str(program_name))

    if not target_script.exists():
        raise FileNotFoundError(f'Target script not found: "{target_script}"')
    if not PY_DIST_PYTHON.exists():
        raise FileNotFoundError(f'Python distro exe not found: "{PY_DIST_PYTHON}"')

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    measurements: list[tuple[str, list[str]]] = []
    if not args.skip_launcher:
        wrapper_python = VENV_PYTHON if VENV_PYTHON.exists() else PY_DIST_PYTHON
        wrapper_process_id_file = WORK_DIR / "script_wrapper_startup_benchmark.pid"
        measurements.append(
            (
                "PyApp wrapper no-terminal",
                python_command(
                    wrapper_python,
                    [
                        str(SCRIPT_WRAPPER_PATH),
                        str(target_script),
                        str(program_name),
                        "",
                        app_id,
                        "0" if start_in_shortcut_folder else "1",
                        "1",
                        "1",
                        "1",
                        "",
                        "",
                        "",
                        "1",
                        "",
                        "",
                        str(wrapper_process_id_file),
                        "",
                        "0",
                    ],
                ),
            )
        )
    measurements.append(("Direct py_dist python", python_command(PY_DIST_PYTHON, [str(target_script)])))
    if not args.skip_global and shutil.which("py") is not None:
        measurements.append(("Direct global py", ["py", str(target_script)]))

    print(f"Target script: {target_script}")
    print(f"Runs per mode: {args.runs}")
    print("Timing point: first PYAPP_STARTUP_BENCHMARK_MARKER write in target script.")

    results: dict[str, list[float]] = {}
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
