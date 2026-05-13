import argparse
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DONT_CHANGE_DIR = SCRIPT_DIR.parent
BACKEND_PYTHON = DONT_CHANGE_DIR / "P" / "P.exe"
WORK_DIR = DONT_CHANGE_DIR / "DO_NOT_SYNC" / "launcher_stub_overhead"


def measure(command: list[str], runs: int) -> list[float]:
    values = []
    for _ in range(runs):
        start = time.perf_counter_ns()
        result = subprocess.run(
            command,
            cwd=DONT_CHANGE_DIR.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        if result.returncode != 0:
            raise RuntimeError(f"Command failed with exit code {result.returncode}: {subprocess.list2cmdline(command)}")
        values.append(elapsed_ms)
    return values


def print_result(label: str, values: list[float], baseline: float = 0.0) -> None:
    median = statistics.median(values)
    mean = statistics.mean(values)
    print(f"{median - baseline:8.1f} {median:8.1f} {mean:8.1f}  {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure launcher stub overhead without launching the real app.")
    parser.add_argument("--runs", type=int, default=30)
    args = parser.parse_args()

    if args.runs < 1:
        raise ValueError("--runs must be at least 1")
    if not BACKEND_PYTHON.exists():
        raise FileNotFoundError(f'Backend Python not found: "{BACKEND_PYTHON}"')

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True)
    try:
        temp_path = WORK_DIR
        noop_script = temp_path / "noop.py"
        noop_script.write_text("pass\n", encoding="utf-8")

        runpy_script = temp_path / "runpy_noop.py"
        runpy_script.write_text(
            "import runpy\n"
            "import sys\n"
            f"sys.argv = [{str(noop_script)!r}]\n"
            f"runpy.run_path({str(noop_script)!r}, run_name='__main__')\n",
            encoding="utf-8",
        )

        batch_file = temp_path / "stub.bat"
        batch_file.write_text(
            "@echo off\n"
            "setlocal\n"
            f'set "launcher_dir={DONT_CHANGE_DIR}\\"\n'
            'set "python_exe=%launcher_dir%P\\P.exe"\n'
            f'set "backend_script={noop_script}"\n'
            'if not exist "%python_exe%" exit /b 1\n'
            '"%python_exe%" "%backend_script%"\n'
            "exit /b %ERRORLEVEL%\n",
            encoding="utf-8",
        )

        direct = measure([str(BACKEND_PYTHON), "-c", "pass"], args.runs)
        direct_file = measure([str(BACKEND_PYTHON), str(noop_script)], args.runs)
        direct_runpy_file = measure([str(BACKEND_PYTHON), str(runpy_script)], args.runs)
        cmd_direct = measure(["cmd.exe", "/d", "/c", str(BACKEND_PYTHON), "-c", "pass"], args.runs)
        batch_stub = measure(["cmd.exe", "/d", "/c", "call", str(batch_file)], args.runs)
    finally:
        shutil.rmtree(WORK_DIR, ignore_errors=True)

    baseline = statistics.median(direct)
    print(f"Runs: {args.runs}")
    print()
    print("ExtraMs  TotalMs   MeanMs  Path")
    print("--------------------------------")
    print_result("direct P.exe -c pass", direct)
    print_result("direct P.exe noop.py", direct_file, baseline)
    print_result("direct P.exe mini runpy -> noop.py", direct_runpy_file, baseline)
    print_result("cmd.exe -> P.exe -c pass", cmd_direct, baseline)
    print_result("cmd.exe -> .bat stub -> P.exe noop.py", batch_stub, baseline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
