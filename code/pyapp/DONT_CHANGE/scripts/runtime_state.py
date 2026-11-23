# What this file is for, in plain words:
# - ProcessRegistry: one small file per running copy of the app in DONT_CHANGE\tmp\running, so a
#   second start, the Stop shortcut and "focus the running window" can find the running copies.
# - It uses the standalone helpers: FileLock and atomic_json (standalone/file_tools.py), process
#   identities and job objects (standalone/processes.py; Stop ends a whole job at once).
#
# Windows API calls through ctypes, for readers new to them:
#   ctypes.WinDLL("kernel32")   loads a Windows system library so Python can call its functions.
#   .argtypes / .restype        tell ctypes the C types of a function's arguments and result; without
#                               them 64-bit handles can be cut off silently.
#   a "handle"                  a number Windows gives out for an open process, file, mutex, ...;
#                               it must be closed again with CloseHandle.
#   ctypes.byref(x)             passes x so the Windows function can write a result into it.
"""Run ownership, cross-process locks, and atomic state for the Windows launcher."""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import json
import math
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

from pyapp.DONT_CHANGE.scripts.standalone.file_tools import atomic_json
from pyapp.DONT_CHANGE.scripts.standalone.processes import (
    close_job,
    job_process_ids,
    matches_identity,
    open_job,
    own_job_name,
    process_identity,
    process_tree,
    terminate_job,
    terminate_job_handle,
    terminate_tree,
)


def clean_python_environment() -> Dict[str, str]:
    """Environment for the application: launcher/package-tool and PYTHON* variables removed."""
    blocked = ("PIP_", "UV_", "VIRTUAL_ENV", "PYTHON")
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(blocked)}
    env["PYTHONNOUSERSITE"] = "1"
    return env


class ProcessRegistry:
    """One atomic identity record per running launcher (watchdog)."""

    def __init__(self, directory: Union[str, Path]) -> None:
        """directory holds one <pid>.json record per running watchdog."""
        self.directory = Path(directory)

    @contextlib.contextmanager
    def lock(self, timeout: float = 120) -> Generator[None, None, None]:
        """Serialize registry changes without leaving a lock file on disk."""
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        identity = os.path.normcase(os.path.realpath(self.directory))
        # A named mutex is a lock that Windows keeps in memory, shared by every process that opens the same
        # name; the name comes from this project's folder, so different projects never block each other.
        name = "Global\\PyAppTemplateRegistry-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
        handle = kernel.CreateMutexW(None, False, name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        owned = False
        try:
            # Wait for the mutex: 0 = got it, 128 = got it from a process that ended without releasing it,
            # 258 = timeout (another launcher held it the whole time).
            result = kernel.WaitForSingleObject(handle, int(timeout * 1000))
            if result == 258:
                raise TimeoutError("Another launcher is busy: " + str(self.directory))
            # An abandoned mutex is acquired too; records are revalidated below.
            if result not in (0, 128):
                raise ctypes.WinError(ctypes.get_last_error())
            owned = True
            yield
        finally:
            if owned:
                kernel.ReleaseMutex(handle)
            kernel.CloseHandle(handle)

    def register(self, child_pid: Optional[int] = None) -> None:
        """Atomically record this launcher's verified identity, its console window and optional app child."""
        with self.lock(), process_identity(os.getpid()) as identity:
            if identity is None:
                raise RuntimeError("Cannot establish launcher process identity")
            if child_pid is not None:
                with process_identity(child_pid) as child:
                    identity["child"] = child
            # The run folder lets Stop leave a "stop requested" note for this watchdog.
            identity["run_dir"] = os.environ.get("PYAPP_RUN_DIR", "")
            # The job object holding this watchdog and everything it starts (see create_own_job).
            identity["job"] = own_job_name()
            try:
                identity["console_hwnd"] = int(ctypes.windll.kernel32.GetConsoleWindow() or 0)
            except Exception:
                from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

                note_ignored("register: console window handle")
                identity["console_hwnd"] = 0
            atomic_json(self.directory / (str(os.getpid()) + ".json"), identity)

    def remove(self) -> None:
        """Remove this launcher's record and prune stale records and empty PID artifacts."""
        with self.lock():
            (self.directory / (str(os.getpid()) + ".json")).unlink(missing_ok=True)
            self.records()

    def _cleanup_empty(self) -> None:
        """Called under the registry mutex; preserve every remaining record."""
        if any(self.directory.glob("*.json")):
            return
        for path in self.directory.glob("*.tmp"):  # abandoned atomic writes
            path.unlink(missing_ok=True)
        # Missing or not empty: never recursively delete unknown files.
        with contextlib.suppress(OSError):
            self.directory.rmdir()

    def records(self) -> Tuple[List[Dict[str, Any]], int]:
        """Return other live launcher records and a stale count while cleaning empty registry artifacts."""
        with self.lock():
            records, stale = self._records()
            self._cleanup_empty()
            return records, stale

    def _records(self) -> Tuple[List[Dict[str, Any]], int]:
        """Validate stored identities and discard stale records, excluding this process from live results."""
        records: List[Dict[str, Any]] = []
        stale = 0
        for path in self.directory.glob("*.json"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                # Gone meanwhile, or held open by antivirus or an indexer: neither proves that the
                # instance ended, so the record is neither listed nor deleted this time.
                continue
            try:
                record = json.loads(text)
                with process_identity(int(record["pid"])) as current:
                    if current is not None and matches_identity(record, current):
                        if current["pid"] != os.getpid():
                            records.append(record)
                        continue
            except (OSError, ValueError, KeyError, TypeError):
                pass
            stale += 1
            with contextlib.suppress(OSError):  # tried again by the next call
                path.unlink(missing_ok=True)
        return records, stale

    def stop(
        self, timeout: float = 0.0, report: Optional[Callable[[str], object]] = None
    ) -> Tuple[int, int, List[str]]:
        """Stop the running instances; returns (stopped, stale, failures).

        With timeout > 0 each instance is first asked to close (WM_CLOSE to its windows, or
        Ctrl+C for a console app) and gets that many seconds to end by itself, so it can save
        its state. Whatever still runs afterwards is terminated with its process tree, including
        processes of an instance whose watchdog did close in time. The registry lock is not held while waiting: an ending watchdog needs it to unregister.
        report(text) receives progress messages.
        """
        if not math.isfinite(timeout):
            raise ValueError(f"The stop timeout must be a finite number of seconds, not {timeout!r}.")
        records, stale = self.records()
        if not records:
            return 0, stale, []
        # A job loses its name when its watchdog ends, and it does not kill on close. Holding a
        # handle from before the close request keeps it reachable, so processes that outlive a
        # watchdog which closed by itself can still be ended.
        held_jobs: Dict[int, int] = {}
        try:
            if timeout > 0:
                for record in records:
                    handle = open_job(record.get("job"))
                    if handle:
                        held_jobs[record["pid"]] = handle
                if report:
                    report(f"Asking {len(records)} instance(s) to close (up to {timeout:g} s) ...")
                for record in records:
                    request_close(record)
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline and any(_still_running(r) for r in records):
                    time.sleep(0.1)
            return self._finish(records, held_jobs, timeout, report, stale)
        finally:
            for handle in held_jobs.values():
                close_job(handle)

    def _finish(
        self,
        records: List[Dict[str, Any]],
        held_jobs: Dict[int, int],
        timeout: float,
        report: Optional[Callable[[str], object]],
        stale: int,
    ) -> Tuple[int, int, List[str]]:
        """The end of stop(): terminate what is left, under the registry lock."""
        stopped = 0
        failures: List[str] = []
        with self.lock():
            for record in records:
                path = self.directory / (str(record["pid"]) + ".json")
                with process_identity(record["pid"]) as current:
                    if not matches_identity(record, current):
                        # It closed by itself; end what it left running in its job.
                        held = held_jobs.get(record["pid"])
                        try:
                            if held:
                                terminate_job_handle(held)
                        except OSError as error:
                            failures.append(f"PID {record['pid']}: its remaining processes: {error}")
                        stopped += 1
                        path.unlink(missing_ok=True)
                        continue
                    if report and timeout > 0:
                        report(f"PID {record['pid']} did not close in time; ending it.")
                    _write_stop_request(record)
                    try:
                        # The job holds the watchdog, the app and all their child processes; the
                        # tree walk is only the fallback for a record without a usable job.
                        # The verified root handle stays open meanwhile, so its PID cannot be reused.
                        if not terminate_job(record.get("job")):
                            terminate_tree(record["pid"])
                        stopped += 1
                        path.unlink(missing_ok=True)
                    except (OSError, RuntimeError) as error:
                        failures.append(str(error))
            self._cleanup_empty()
        return stopped, stale, failures


def _still_running(record: Dict[str, Any]) -> bool:
    with process_identity(record["pid"]) as current:
        return matches_identity(record, current)


def _write_stop_request(record: Dict[str, Any]) -> None:
    """Tell the instance's watchdog that its end was requested (no completion actions)."""
    from pyapp.DONT_CHANGE.pyapp_settings import STOP_REQUEST_FILE_NAME

    run_dir = record.get("run_dir")
    if run_dir and Path(run_dir).is_dir():
        try:
            Path(run_dir, STOP_REQUEST_FILE_NAME).write_text("stop", encoding="utf-8")
        except OSError:
            from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

            note_ignored("write stop request")


def request_close(record: Dict[str, Any]) -> None:
    """Ask one instance to end by itself: WM_CLOSE to its app windows, else Ctrl+C to its console."""
    import subprocess
    import sys

    from pyapp.DONT_CHANGE.pyapp_settings import CTRL_C_HELPER_PATH
    from pyapp.DONT_CHANGE.scripts.desktop.windows_focus import app_windows
    from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

    _write_stop_request(record)
    child = record.get("child") if isinstance(record.get("child"), dict) else None
    child_pid = None
    if child:
        with process_identity(child.get("pid") or 0) as current:
            if matches_identity(child, current):
                child_pid = child["pid"]
    try:
        job_pids = job_process_ids(record.get("job"))
        if job_pids:
            windows = app_windows(job_pids - {record["pid"]})
        else:
            windows = app_windows(process_tree([child_pid])) if child_pid else []
        if windows:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            for hwnd in windows:
                user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE, like clicking the window's X
            return
        # No window: a console app. Ctrl+C reaches every process of the instance's console; its
        # watchdog ignores it while the app runs. DETACHED_PROCESS: the helper has no console yet.
        # Run the bundled Ctrl+C helper with the current interpreter and a numeric process ID.
        subprocess.run(  # noqa: S603
            [sys.executable, "-I", "-S", CTRL_C_HELPER_PATH, str(child_pid or record["pid"])],
            creationflags=0x00000008,
            timeout=10,
            check=False,
        )
    except Exception:
        note_ignored("request_close")


def unique_log_path(path: Optional[str], run_id: Optional[str] = None) -> str:
    """Append a compact 12-character run suffix, preserving an empty disabled path."""
    if not path:
        return ""
    p = Path(path)
    # Keep 48 random bits while avoiding a full UUID in Windows log paths.
    suffix = (run_id or uuid.uuid4().hex)[:12]
    return str(p.with_name(p.stem + "_" + suffix + p.suffix))
