"""Run ownership, cross-process locks, and atomic state for the Windows launcher."""


from __future__ import annotations

import contextlib
import ctypes
import hashlib
import json
import os
import threading
import time
import uuid
from pathlib import Path

_local_locks = threading.local()


class FileLock:
    """A reentrant, process-shared lock; Windows releases it after a crash."""

    def __init__(self, path, timeout=120):
        """Store the normalized lock path and acquisition timeout."""
        self.path = str(Path(path).resolve())
        self.timeout = timeout

    def __enter__(self):
        """Acquire or reenter the checkout's file lock, waiting up to the configured timeout."""
        import msvcrt

        held = getattr(_local_locks, "held", None)
        if held is None:
            held = _local_locks.held = {}
        if self.path in held:
            held[self.path][1] += 1
            return self
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        stream = open(self.path, "a+b")
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

    def __exit__(self, *exc):
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


def atomic_json(path, payload):
    """Write JSON through a unique sibling file and atomically replace the destination."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def clean_python_environment(isolated=True):
    """Environment for the application: launcher/package-tool variables removed.

    isolated=False keeps the user's PYTHON* settings (package_environment =
    "interpreter_site_packages" runs the user's own interpreter as configured).
    """
    blocked = ("PIP_", "UV_", "VIRTUAL_ENV") + (("PYTHON",) if isolated else ())
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(blocked)}
    if isolated:
        env["PYTHONNOUSERSITE"] = "1"
    return env


@contextlib.contextmanager
def process_identity(pid):
    """Keep the process handle open while its creation time and image are checked."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
        ctypes.POINTER(wintypes.FILETIME)
    ] * 4
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

    def __init__(self, pid_path):
        """Derive the registry directory from the configured PID indicator path."""
        self.pid_path = Path(pid_path)
        self.directory = Path(str(pid_path) + ".d")

    @contextlib.contextmanager
    def lock(self, timeout=120):
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
        identity = os.path.normcase(os.path.realpath(self.pid_path))
        name = (
            "Global\\PyAppTemplateRegistry-"
            + hashlib.sha256(identity.encode("utf-8")).hexdigest()
        )
        handle = kernel.CreateMutexW(None, False, name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        owned = False
        try:
            result = kernel.WaitForSingleObject(handle, int(timeout * 1000))
            if result == 258:
                raise TimeoutError("Another launcher is busy: " + str(self.pid_path))
            # An abandoned mutex is acquired too; records are revalidated below.
            if result not in (0, 128):
                raise ctypes.WinError(ctypes.get_last_error())
            owned = True
            yield
        finally:
            if owned:
                kernel.ReleaseMutex(handle)
            kernel.CloseHandle(handle)

    def register(self, child_pid=None):
        """Atomically record this launcher's verified identity, its console window and optional app child."""
        with self.lock(), process_identity(os.getpid()) as identity:
            if identity is None:
                raise RuntimeError("Cannot establish launcher process identity")
            if child_pid is not None:
                with process_identity(child_pid) as child:
                    identity["child"] = child
            try:
                identity["console_hwnd"] = int(ctypes.windll.kernel32.GetConsoleWindow() or 0)
            except Exception:
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
        records, stale = [], 0
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

    def stop(self):
        """Terminate verified launcher trees directly, without a shutdown callback."""
        stopped, failures = 0, []
        with self.lock():
            records, stale = self.records()
            for record in records:
                with process_identity(record["pid"]) as current:
                    if not matches_identity(record, current):
                        stale += 1
                        (self.directory / (str(record["pid"]) + ".json")).unlink(
                            missing_ok=True
                        )
                        continue
                    try:
                        # The verified root handle stays open while the tree is terminated.
                        terminate_tree(record["pid"])
                        stopped += 1
                        (self.directory / (str(record["pid"]) + ".json")).unlink(
                            missing_ok=True
                        )
                    except (OSError, RuntimeError) as error:
                        failures.append(str(error))
            self._cleanup_empty()
        return stopped, stale, failures


def terminate_tree(root_pid):
    """Force-terminate a process and all its descendants via the Win32 API.

    Deliberately avoids taskkill/WMI, which fail on PCs with a broken WMI service.
    """
    from backend.DONT_CHANGE.scripts.windows_focus import process_tree

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


def matches_identity(record, current):
    """Compare PID, creation time and executable path to reject stale or reused process IDs."""
    return current is not None and all(
        record.get(key) == current.get(key) for key in ("pid", "created", "image")
    )


def unique_log_path(path, run_id=None):
    """Append a compact 12-character run suffix, preserving an empty disabled path."""
    if not path:
        return ""
    p = Path(path)
    # Keep 48 random bits while avoiding a full UUID in Windows log paths.
    suffix = (run_id or uuid.uuid4().hex)[:12]
    return str(p.with_name(p.stem + "_" + suffix + p.suffix))
