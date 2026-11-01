"""Run ownership, cross-process locks, and atomic state for the Windows launcher."""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import json
import os
import subprocess
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


def clean_python_environment():
    """Retain application/proxy variables, excluding Python/package-tool injection."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.upper().startswith(("PYTHON", "PIP_", "UV_"))
    }
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_CONFIG_FILE"] = os.devnull
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
    """One atomic identity record per launcher; legacy bare PIDs are never killed."""

    def __init__(self, pid_path):
        """Derive registry and legacy cleanup paths from the configured PID indicator."""
        self.pid_path = Path(pid_path)
        self.directory = Path(str(pid_path) + ".d")
        # Kept only to clean up the old disk lock; new operations use a mutex.
        self.lock_path = str(pid_path) + ".lock"

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
        """Atomically record this launcher's verified identity and optional application child identity."""
        with self.lock(), process_identity(os.getpid()) as identity:
            if identity is None:
                raise RuntimeError("Cannot establish launcher process identity")
            if child_pid is not None:
                with process_identity(child_pid) as child:
                    identity["child"] = child
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
        # Remove abandoned atomic writes and markers from the former Stop protocol.
        for pattern in ("*.tmp", "*.stop"):
            for path in self.directory.glob(pattern):
                path.unlink(missing_ok=True)
        try:
            self.directory.rmdir()
        except OSError:
            pass  # Missing or not empty; never recursively delete unknown files.
        for path in (self.pid_path, Path(self.lock_path)):
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass  # An older launcher can still hold its legacy lock file.

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
                        # Retain the verified root handle until taskkill completes.
                        result = subprocess.run(
                            ["taskkill", "/PID", str(record["pid"]), "/T", "/F"],
                            capture_output=True,
                            text=True,
                            errors="replace",
                        )
                        if result.returncode:
                            raise RuntimeError(result.stderr or result.stdout)
                        stopped += 1
                        (self.directory / (str(record["pid"]) + ".json")).unlink(
                            missing_ok=True
                        )
                    except (OSError, RuntimeError) as error:
                        failures.append(str(error))
            self._cleanup_empty()
        return stopped, stale, failures


def matches_identity(record, current):
    """Compare PID, creation time and executable path to reject stale or reused process IDs."""
    return current is not None and all(
        record.get(key) == current.get(key) for key in ("pid", "created", "image")
    )


def unique_log_path(path, run_id=None):
    """Append the run identifier to a log filename, preserving an empty disabled path."""
    if not path:
        return ""
    p = Path(path)
    return str(p.with_name(p.stem + "_" + (run_id or uuid.uuid4().hex) + p.suffix))


def require_supported_architecture():
    """Reject managed runtime installation on architectures other than Windows AMD64."""
    architecture = os.environ.get(
        "PROCESSOR_ARCHITEW6432", os.environ.get("PROCESSOR_ARCHITECTURE", "")
    ).upper()
    if architecture != "AMD64":
        raise RuntimeError(
            "Managed runtimes currently require Windows x64 (AMD64). Detected: "
            + architecture
            + ". Native ARM64/x86 installation is not supported; use a separately managed Python with use_global_python=True."
        )


def resolve_global_python():
    """Resolve py or python to its actual interpreter executable using an isolated subprocess."""
    import shutil

    launcher = shutil.which("py") or shutil.which("python")
    if not launcher:
        raise RuntimeError(
            "Global-Python mode requires an installed py/python executable"
        )
    result = subprocess.run(
        [launcher, "-E", "-s", "-c", "import sys; print(sys.executable)"],
        env=clean_python_environment(),
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return result.stdout.strip()
