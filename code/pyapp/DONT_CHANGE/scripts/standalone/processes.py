"""Processes on Windows: safe identities, process trees, job objects and crash exit codes.

Standalone: copy this file anywhere. Standard library only (ctypes); Windows only.

- process_identity / matches_identity: a process ID plus creation time and program path, because
  Windows reuses the numbers of ended processes.
- descendants / process_tree: a process and everything it started, without reused-PID mistakes.
- Job objects: put this process into a named job, so every process it starts belongs to it and
  can be ended with one call (create_own_job, terminate_job, job_process_ids, ...).
- terminate_tree: the fallback without a job. exit_code_looks_like_interpreter_crash: NTSTATUS codes.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
from ctypes import wintypes
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, Set, Tuple

TH32CS_SNAPPROCESS = 0x00000002


@contextlib.contextmanager
def process_identity(pid: int) -> Generator[Optional[Dict[str, Any]], None, None]:
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
    # A process ID alone is not a safe identity: Windows reuses the number of an ended process. So a
    # record stores the process's creation time and program path too, and both must still match.
    # 0x1000 = PROCESS_QUERY_LIMITED_INFORMATION: enough to read these values, nothing more.
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
            # 259 = STILL_ACTIVE: the exit code Windows reports while a process is still running.
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


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def _creation_time(pid: int) -> Optional[int]:
    """The process's creation time (FILETIME ticks), or None if it ended or cannot be queried."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        creation, end, system, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(
            handle, ctypes.byref(creation), ctypes.byref(end), ctypes.byref(system), ctypes.byref(user)
        ):
            return None
        return (creation.dwHighDateTime << 32) | creation.dwLowDateTime
    finally:
        kernel.CloseHandle(handle)


def descendants(
    root_pids: Iterable[Optional[int]],
    parents: Iterable[Tuple[int, int]],
    created: Callable[[int], Optional[int]],
) -> Set[int]:
    """The roots and every process whose parent chain leads to one of them.

    parents holds (pid, parent pid) pairs. Windows keeps a process's parent PID after the parent
    ends, and PIDs are reused: a process whose long-gone parent had a PID that a root has now
    would look like the root's child. So a child counts only if it was created no earlier than
    its parent. A child whose creation time cannot be read is left out: leaving a process
    running is far less harmful than ending or focusing an unrelated program.
    """
    children: Dict[int, List[int]] = {}
    for pid, parent in parents:
        if pid != parent:  # the System Idle Process is its own parent
            children.setdefault(parent, []).append(pid)
    times: Dict[int, Optional[int]] = {}

    def time_of(pid: int) -> Optional[int]:
        if pid not in times:
            times[pid] = created(pid)
        return times[pid]

    result: Set[int] = set()
    pending = [pid for pid in root_pids if pid]
    while pending:
        pid = pending.pop()
        if pid in result:
            continue
        result.add(pid)
        parent_time = time_of(pid) if children.get(pid) else None
        if parent_time is None:
            continue
        for child in children[pid]:
            child_time = time_of(child)
            if child_time is not None and child_time >= parent_time:
                pending.append(child)
    return result


def process_tree(root_pids: Iterable[Optional[int]]) -> Set[int]:
    """The given processes and all their descendants (see descendants for the PID-reuse check)."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry)]
    snapshot = kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    parents = []
    try:
        entry = _ProcessEntry()
        entry.dwSize = ctypes.sizeof(_ProcessEntry)
        ok = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            parents.append((entry.th32ProcessID, entry.th32ParentProcessID))
            ok = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return descendants(root_pids, parents, _creation_time)


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


def _job_api() -> ctypes.WinDLL:
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
    # A job object is a Windows container for processes: every process the watchdog starts later, and
    # every process those start, lands in the same job. Stop then ends the whole job in one call.
    handle = kernel.CreateJobObjectW(None, name)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    # BREAKAWAY_OK: a process may still be started outside the job on purpose (restart helpers,
    # notifications that must outlive the run). No "kill on close": programs the app opened survive
    # a normal end of the app.
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


def own_job_name() -> str:
    """The name create_own_job() gave this process's job ("" before it ran or if it failed)."""
    return _own_job_name


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


def terminate_tree(root_pid: int) -> None:
    """Fallback without a job: force-terminate a process and its descendants via the Win32 API.

    Deliberately avoids taskkill/WMI, which fail on PCs with a broken WMI service.
    """
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    pids = process_tree([root_pid])
    failures = []
    # Root first, so the watchdog cannot react to its children ending.
    for pid in [root_pid, *sorted(pids - {root_pid})]:
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


def matches_identity(record: Dict[str, Any], current: Optional[Dict[str, Any]]) -> bool:
    """Compare PID, creation time and executable path to reject stale or reused process IDs."""
    return current is not None and all(record.get(key) == current.get(key) for key in ("pid", "created", "image"))


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
        0xC0000374,  # heap corruption
        0xC0000094,  # integer division by zero
        0xC000008E,  # floating-point division by zero
        0xC0000090,  # invalid floating-point operation
        0xC0000091,  # floating-point overflow
        0xC0000095,  # integer overflow
        0xC0000006,  # in-page error (e.g. failed DLL paging)
        0xC0000135,  # DLL not found
        0xC0000142,  # DLL failed to initialize
        0xE06D7363,  # unhandled C++ exception
    }
    # Not every code >= 0xC0000000: sys.exit(-1) arrives as 0xFFFFFFFF and is an ordinary exit.
    return (exit_code & 0xFFFFFFFF) in windows_crash_codes
