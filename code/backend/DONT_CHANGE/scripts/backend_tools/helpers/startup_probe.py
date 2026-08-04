"""Python 3.5+-compatible main.py stand-in for startup-time measurements."""

# ruff: noqa: UP032 UP030

import os
import sys
import time

marker_path = os.environ.get("PYAPP_STARTUP_BENCHMARK_MARKER")

if not marker_path:
    sys.exit(0)
else:
    try:
        ready_ns = int(time.perf_counter() * 1000000000)
        marker_dir = os.path.dirname(marker_path)
        if marker_dir:
            os.makedirs(marker_dir, exist_ok=True)
        with open(marker_path, "w", encoding="utf-8") as marker_file:
            marker_file.write("ready_ns={0}\n".format(ready_ns))
            marker_file.write(
                "start_ns={0}\n".format(
                    os.environ.get("PYAPP_STARTUP_BENCHMARK_START_NS", "")
                )
            )
            marker_file.write("pid={0}\n".format(os.getpid()))
        sys.exit(0)
    except Exception:
        sys.exit(1)
