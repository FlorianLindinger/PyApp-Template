"""Paths for the development tools in this folder; the launcher never imports it."""

import tempfile
from pathlib import Path

DONT_CHANGE_DIR = Path(__file__).resolve().parents[2]
CODE_DIR = DONT_CHANGE_DIR.parents[1]
PROJECT_ROOT = CODE_DIR.parent
VENV_PYTHON = CODE_DIR / "backend" / "generated" / ".venv" / "Scripts" / "python.exe"
# get_startup_time.py: temporary project copies, outside the project to keep their paths short.
STARTUP_BENCHMARK_WORK_DIR = Path(tempfile.gettempdir()) / "pyapp_startup_benchmark"
