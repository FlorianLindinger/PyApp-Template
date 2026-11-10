"""Run ownership, cross-process locks, and atomic state for the Windows launcher."""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import json
import math
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

_local_locks = threading.local()


class FileLock:
    """A reentrant, process-shared lock; Windows releases it after a crash."""

    def __init__(self, path: Union[str, Path], timeout: float = 120):
        """Store the normalized lock path and acquisition timeout."""
        self.path = str(Path(path).resolve())
        self.timeout = timeout

    def __enter__(self):
        """Acquire or reenter the checkout's file lock, waiting up to the configured timeout."""
        import msvcrt

        held: Optional[Dict[str, List[Any]]] = getattr(_local_locks, "held", None)
        if held is None:
            held = {}
            _local_locks.held = held
        if self.path in held:
            held[self.path][1] += 1
            return self
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        stream = Path(self.path).open("a+b")
        if stream.seek(0, 2) == 0:
            stream.write(b"\0")
            stream.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                held[self.path] = [stream, 1]
                return self
            except OSError:
                if time.monotonic() >= deadline:
                    stream.close()
                    raise TimeoutError("Another launcher is busy: " + self.path)
                time.sleep(0.05)

    def __exit__(self, *exc: object):
        """Release one acquisition and close the file lock when the final nested context exits."""
        import msvcrt

        stream, count = _local_locks.held[self.path]
        if count > 1:
            _local_locks.held[self.path][1] -= 1
        else:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            stream.close()
            del _local_locks.held[self.path]


def atomic_json(path: Union[str, Path], payload: object):
    """Write JSON through a unique sibling file and atomically replace the destination."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        Path(temp).replace(path)
    finally:
        temp.unlink(missing_ok=True)


def clean_python_environment():
    """Environment for the application: launcher/package-tool and PYTHON* variables removed."""
    blocked = ("PIP_", "UV_", "VIRTUAL_ENV", "PYTHON")
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(blocked)}
    env["PYTHONNOUSERSITE"] = "1"
    return env


@contextlib.contextmanager
def process_identity(pid: int):
    """Keep the process handle open while its creation time and image are checked."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        yield None
        return
    try:
        creation, end, system, user = (wintypes.FILETIME() for _ in range(4))
        size = wintypes.DWORD(32768)
        image = ctypes.create_unicode_buffer(size.value)
        exit_code = wintypes.DWORD()
        if (
            kernel.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(end),
                ctypes.byref(system),
                ctypes.byref(user),
            )
            and kernel.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size))
            and kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            and exit_code.value == 259
        ):
            yield {
                "pid": pid,
                "created": (creation.dwHighDateTime << 32) | creation.dwLowDateTime,
                "image": os.path.normcase(image.value),
            }
        else:
            yield None
    finally:
        kernel.CloseHandle(handle)


class ProcessRegistry:
    """One atomic identity record per running launcher (watchdog)."""

    def __init__(self, directory: Union[str, Path]):
        """directory holds one <pid>.json record per running watchdog."""
        self.directory = Path(directory)

    @contextlib.contextmanager
    def lock(self, timeout: float = 120):
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
        name = "Global\\PyAppTemplateRegistry-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
        handle = kernel.CreateMutexW(None, False, name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        owned = False
        try:
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

    def register(self, child_pid: Optional[int] = None):
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
            identity["job"] = _own_job_name
            try:
                identity["console_hwnd"] = int(ctypes.windll.kernel32.GetConsoleWindow() or 0)
            except Exception:
                from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

                note_ignored("register: console window handle")
                identity["console_hwnd"] = 0
            atomic_json(self.directory / (str(os.getpid()) + ".json"), identity)

    def remove(self):
        """Remove this launcher's record and prune stale records and empty PID artifacts."""
        with self.lock():
            (self.directory / (str(os.getpid()) + ".json")).unlink(missing_ok=True)
            self.records()

    def _cleanup_empty(self):
        """Called under the registry mutex; preserve every remaining record."""
        if any(self.directory.glob("*.json")):
            return
        for path in self.directory.glob("*.tmp"):  # abandoned atomic writes
            path.unlink(missing_ok=True)
        try:
            self.directory.rmdir()
        except OSError:
            pass  # Missing or not empty; never recursively delete unknown files.

    def records(self):
        """Return other live launcher records and a stale count while cleaning empty registry artifacts."""
        with self.lock():
            records, stale = self._records()
            self._cleanup_empty()
            return records, stale

    def _records(self):
        """Validate stored identities and discard stale records, excluding this process from live results."""
        records: List[Dict[str, Any]] = []
        stale = 0
        for path in self.directory.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                with process_identity(int(record["pid"])) as current:
                    if current is not None and matches_identity(record, current):
                        if current["pid"] != os.getpid():
                            records.append(record)
                        continue
            except (OSError, ValueError, KeyError, TypeError):
                pass
            stale += 1
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
    from pyapp.DONT_CHANGE.backend_settings import STOP_REQUEST_FILE_NAME

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

    from pyapp.DONT_CHANGE.backend_settings import CTRL_C_HELPER_PATH
    from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored
    from pyapp.DONT_CHANGE.scripts.windows_focus import app_windows, process_tree

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


# ---------------------------------------------------------------- job objects
#
# The watchdog puts itself into a named job object before it starts the app. Every process the
# app starts then belongs to that job too (Windows assigns children to their parent's job), so
# Stop ends exactly this instance's processes with one TerminateJobObject call: no process
# snapshot, no reused process IDs. The job does not kill on close, so programs the app opens
# (e.g. a browser) survive a normal end of the app; only Stop ends them. An app can start a
# process outside the job with CREATE_BREAKAWAY_FROM_JOB (the job allows breakaway).

_own_job_handle = None  # kept open for the life of the watchdog: closing it deletes the job's name
_own_job_name = ""

JOB_OBJECT_QUERY = 0x0004
JOB_OBJECT_TERMINATE = 0x0008
JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
JOB_OBJECT_BASIC_LIMIT_INFORMATION_CLASS = 2
JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS = 3


def _job_api():
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.OpenJobObjectW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.OpenJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    return kernel


class _JobBasicLimits(ctypes.Structure):
    _fields_ = (
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    )


def create_own_job() -> str:
    """Put this process (the watchdog) into a new named job object; returns its name ("" on failure)."""
    global _own_job_handle, _own_job_name
    with process_identity(os.getpid()) as identity:
        if identity is None:
            return ""
        # PID plus creation time: unique, and never the name of another (earlier) instance's job.
        name = f"Local\\PyAppJob-{identity['pid']}-{identity['created']}"
    kernel = _job_api()
    handle = kernel.CreateJobObjectW(None, name)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = _JobBasicLimits(LimitFlags=JOB_OBJECT_LIMIT_BREAKAWAY_OK)
    kernel.SetInformationJobObject(
        handle, JOB_OBJECT_BASIC_LIMIT_INFORMATION_CLASS, ctypes.byref(limits), ctypes.sizeof(limits)
    )
    if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        error = ctypes.WinError(ctypes.get_last_error())
        kernel.CloseHandle(handle)
        raise error
    _own_job_handle, _own_job_name = handle, name
    return name


def terminate_job(name: Optional[str]) -> bool:
    """End every process of the named job; False if there is no such job (anymore)."""
    if not name:
        return False
    kernel = _job_api()
    handle = kernel.OpenJobObjectW(JOB_OBJECT_TERMINATE, False, name)
    if not handle:
        return False
    try:
        if not kernel.TerminateJobObject(handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())
        return True
    finally:
        kernel.CloseHandle(handle)


def open_job(name: Optional[str]) -> int:
    """A handle that can end the named job, or 0 if there is no such job; close it with close_job()."""
    if not name:
        return 0
    return _job_api().OpenJobObjectW(JOB_OBJECT_TERMINATE, False, name) or 0


def terminate_job_handle(handle: int) -> None:
    """End every process still in a job opened with open_job() (nothing to do for an empty job)."""
    kernel = _job_api()
    if not kernel.TerminateJobObject(handle, 1):
        raise ctypes.WinError(ctypes.get_last_error())


def close_job(handle: int) -> None:
    _job_api().CloseHandle(handle)


def job_process_ids(name: Optional[str]) -> Set[int]:
    """IDs of the processes currently in the named job (empty if it does not exist)."""
    if not name:
        return set()
    kernel = _job_api()
    handle = kernel.OpenJobObjectW(JOB_OBJECT_QUERY, False, name)
    if not handle:
        return set()
    try:
        capacity = 4096

        class _ProcessIdList(ctypes.Structure):
            _fields_ = (
                ("NumberOfAssignedProcesses", ctypes.c_uint32),
                ("NumberOfProcessIdsInList", ctypes.c_uint32),
                ("ProcessIdList", ctypes.c_size_t * capacity),
            )

        listing = _ProcessIdList()
        if not kernel.QueryInformationJobObject(
            handle, JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS, ctypes.byref(listing), ctypes.sizeof(listing), None
        ):
            return set()
        return {int(listing.ProcessIdList[i]) for i in range(listing.NumberOfProcessIdsInList)}
    finally:
        kernel.CloseHandle(handle)


def terminate_tree(root_pid: int):
    """Fallback without a job: force-terminate a process and its descendants via the Win32 API.

    Deliberately avoids taskkill/WMI, which fail on PCs with a broken WMI service.
    """
    from pyapp.DONT_CHANGE.scripts.windows_focus import process_tree

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    pids = process_tree([root_pid])
    failures = []
    # Root first, so the watchdog cannot react to its children ending.
    for pid in [root_pid] + sorted(pids - {root_pid}):
        handle = kernel.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if not handle:
            if pid == root_pid:
                failures.append(f"PID {pid}: cannot open process (error {ctypes.get_last_error()})")
            continue
        try:
            if not kernel.TerminateProcess(handle, 1) and pid == root_pid:
                failures.append(f"PID {pid}: terminate failed (error {ctypes.get_last_error()})")
        finally:
            kernel.CloseHandle(handle)
    if failures:
        raise RuntimeError("; ".join(failures))


def matches_identity(record: Dict[str, Any], current: Optional[Dict[str, Any]]):
    """Compare PID, creation time and executable path to reject stale or reused process IDs."""
    return current is not None and all(record.get(key) == current.get(key) for key in ("pid", "created", "image"))


def unique_log_path(path: Optional[str], run_id: Optional[str] = None):
    """Append a compact 12-character run suffix, preserving an empty disabled path."""
    if not path:
        return ""
    p = Path(path)
    # Keep 48 random bits while avoiding a full UUID in Windows log paths.
    suffix = (run_id or uuid.uuid4().hex)[:12]
    return str(p.with_name(p.stem + "_" + suffix + p.suffix))


def exit_code_looks_like_interpreter_crash(exit_code: object) -> bool:
    """Whether a process exit code is a common Windows crash code (NTSTATUS, signed or unsigned)."""
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        return False

    # NTSTATUS values can arrive as signed or unsigned integers.
    windows_crash_codes = {
        0xC0000005,  # access violation
        0xC00000FD,  # stack overflow
        0xC000001D,  # illegal instruction
        0xC0000096,  # privileged instruction
        0xC0000409,  # stack buffer overrun
    }
    return (exit_code & 0xFFFFFFFF) in windows_crash_codes
