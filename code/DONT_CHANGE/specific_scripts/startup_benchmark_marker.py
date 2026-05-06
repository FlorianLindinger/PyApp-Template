from __future__ import annotations

import os
import sys
import time


def mark_startup_time() -> None:
    marker_path = os.environ.get("PYAPP_STARTUP_BENCHMARK_MARKER")
    if not marker_path:
        return

    try:
        ready_ns = time.perf_counter_ns()
        marker_dir = os.path.dirname(marker_path)
        if marker_dir:
            os.makedirs(marker_dir, exist_ok=True)
        with open(marker_path, "w", encoding="utf-8") as marker_file:
            marker_file.write(f"ready_ns={ready_ns}\n")
            marker_file.write(f"start_ns={os.environ.get('PYAPP_STARTUP_BENCHMARK_START_NS', '')}\n")
            marker_file.write(f"pid={os.getpid()}\n")
    except Exception:
        sys.exit(1)
    sys.exit(0)


mark_startup_time()
