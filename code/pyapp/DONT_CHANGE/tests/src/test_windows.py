"""Windows-only: file lock, process registry, job objects and graceful Stop with real processes."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from typing import Any, Callable, Dict
from unittest import mock

from project_location import CODE

if os.name == "nt":
    from pyapp.DONT_CHANGE.scripts import runtime_state
    from pyapp.DONT_CHANGE.scripts.standalone import file_tools

CREATE_NEW_CONSOLE = 0x00000010

# A venv's python.exe is a stub that starts the real interpreter as a child, with another PID.
PYTHON = getattr(sys, "_base_executable", sys.executable)

INSTANCE = """
import ctypes, os, subprocess, sys, time
ctypes.windll.kernel32.SetConsoleCtrlHandler(None, False)  # some shells pass on "ignore Ctrl+C"
sys.path.insert(0, {code!r})
from pyapp.DONT_CHANGE.scripts import runtime_state
from pyapp.DONT_CHANGE.scripts.standalone import processes
processes.create_own_job()
registry = runtime_state.ProcessRegistry({registry!r})
grandchild = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
registry.register(grandchild.pid)
with open({ready!r}, "w") as stream:
    stream.write(str(grandchild.pid))
try:
    # Ends by itself (without its child) once the test creates the exit file.
    for _ in range(1200):
        if os.path.exists({exit_file!r}):
            sys.exit(0)
        time.sleep(0.1)
except KeyboardInterrupt:
    with open({marker!r}, "w") as stream:
        stream.write("interrupted")
"""


def wait_for(condition: Callable[[], bool], seconds: float = 20.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.1)
    return False


def running(pid: int):
    with runtime_state.process_identity(pid) as identity:
        return identity is not None


@unittest.skipUnless(os.name == "nt", "Windows only")
class StructureTests(unittest.TestCase):
    def test_propvariant_has_the_windows_size(self):
        import ctypes

        from pyapp.DONT_CHANGE.scripts.standalone.com_tools import PROPVARIANT

        self.assertEqual(ctypes.sizeof(PROPVARIANT), 24 if ctypes.sizeof(ctypes.c_void_p) == 8 else 16)


# pid: creation time; None = ended or not readable
TREE_CREATED: Dict[int, Any] = {100: 50, 101: 60, 102: 70, 200: 10, 300: None, 301: 80}
# (pid, parent pid): 200 is older than 100, so its parent was another process with PID 100.
TREE_PARENTS = ((100, 4), (101, 100), (102, 101), (200, 100), (300, 100), (301, 300), (0, 0))


@unittest.skipUnless(os.name == "nt", "Windows only")
class ProcessTreeTests(unittest.TestCase):
    """A reused parent PID must not make an unrelated process a child (audit F16)."""

    def tree(self, *roots: Any) -> Any:
        from pyapp.DONT_CHANGE.scripts.standalone.processes import descendants

        return descendants(roots, TREE_PARENTS, TREE_CREATED.get)

    def test_children_created_after_their_parent_are_found(self):
        self.assertEqual(self.tree(100), {100, 101, 102})

    def test_an_older_process_with_a_reused_parent_pid_is_left_out(self):
        self.assertNotIn(200, self.tree(100))

    def test_a_child_whose_age_cannot_be_read_is_left_out_with_its_children(self):
        self.assertFalse({300, 301} & self.tree(100))

    def test_roots_are_kept_and_empty_roots_ignored(self):
        self.assertEqual(self.tree(None, 0, 200), {200})

    def test_the_real_tree_of_this_process_contains_a_new_child(self):
        from pyapp.DONT_CHANGE.scripts.standalone.processes import process_tree

        child = subprocess.Popen([PYTHON, "-c", "import time; time.sleep(30)"])  # noqa: S603
        try:
            self.assertIn(child.pid, process_tree([os.getpid()]))
        finally:
            child.kill()
            child.wait()


class WindowsProcessTests(unittest.TestCase):
    # typing.override requires Python 3.12; keep this override dependency-free on 3.8.
    def setUp(self):  # pyrefly: ignore[missing-override-decorator]
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.registry = runtime_state.ProcessRegistry(self.folder / "running")
        self.exit_file = self.folder / "exit"

    def start_instance(self, new_console: bool = False):
        ready, marker = self.folder / "ready", self.folder / "marker"
        script = self.folder / "instance.py"
        script.write_text(
            INSTANCE.format(
                code=str(CODE),
                registry=str(self.registry.directory),
                ready=str(ready),
                marker=str(marker),
                exit_file=str(self.exit_file),
            ),
            encoding="utf-8",
        )
        # A console of its own (for the Ctrl+C test), but hidden: a visible one flashes up during
        # every test run and pre-push hook, and with Windows Terminal as the default terminal it
        # opens a whole window that closes again like a crash.
        startup = subprocess.STARTUPINFO()
        if new_console:
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0  # SW_HIDE
        # Test subprocesses execute fixed fixture/helper code using the local interpreter or Git.
        process = subprocess.Popen(  # noqa: S603
            [PYTHON, "-E", "-s", str(script)],
            creationflags=CREATE_NEW_CONSOLE if new_console else 0,
            startupinfo=startup,
        )
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        self.assertTrue(wait_for(ready.exists), "the test instance did not start")
        time.sleep(0.2)
        return process, int(ready.read_text()), marker

    def test_records_name_the_job(self):
        process, _, _ = self.start_instance()
        records, _ = self.registry.records()
        self.assertEqual([r["pid"] for r in records], [process.pid])
        self.assertTrue(records[0]["job"].startswith("Local\\PyAppJob-"))
        self.assertIn(records[0]["child"]["pid"], runtime_state.job_process_ids(records[0]["job"]))
        self.registry.stop(0)

    def test_stop_ends_the_whole_job(self):
        process, grandchild, _ = self.start_instance()
        stopped, _, failures = self.registry.stop(0)
        self.assertEqual((stopped, failures), (1, []))
        self.assertTrue(wait_for(lambda: process.poll() is not None))
        self.assertTrue(wait_for(lambda: not running(grandchild)), "a child of the app survived Stop")
        self.assertEqual(self.registry.records()[0], [])

    def test_graceful_stop_sends_ctrl_c_to_console_apps(self):
        process, _, marker = self.start_instance(new_console=True)
        stopped, _, failures = self.registry.stop(10)
        self.assertEqual((stopped, failures), (1, []))
        self.assertTrue(wait_for(lambda: process.poll() is not None))
        self.assertTrue(marker.exists(), "the app did not get Ctrl+C before it was terminated")

    def test_graceful_stop_also_ends_what_a_closed_instance_left_running(self):
        process, grandchild, _ = self.start_instance()

        # Only the instance itself reacts to the close request; its child keeps running.
        def close_only_the_instance(record: Dict[str, Any]) -> None:
            self.exit_file.touch()

        with mock.patch.object(runtime_state, "request_close", side_effect=close_only_the_instance):
            stopped, _, failures = self.registry.stop(10)
        self.assertEqual((stopped, failures), (1, []))
        self.assertTrue(wait_for(lambda: process.poll() is not None))
        self.assertTrue(wait_for(lambda: not running(grandchild)), "a child of the app survived Stop")
        self.assertEqual(self.registry.records()[0], [])

    def test_a_watchdog_error_ends_the_app_it_started(self):
        from pyapp.DONT_CHANGE.runtime import bg_watchdog

        ready = self.folder / "grandchild"
        app_source = (
            "import subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
            f"open({str(ready)!r}, 'w').write(str(child.pid))\n"
            "time.sleep(120)\n"
        )
        # Test subprocesses execute fixed fixture code using the local interpreter.
        app = subprocess.Popen([PYTHON, "-c", app_source], stdout=subprocess.PIPE)  # noqa: S603
        self.addCleanup(lambda: app.kill() if app.poll() is None else None)
        self.assertTrue(wait_for(ready.exists), "the test app did not start")
        grandchild = int(ready.read_text())
        bg_watchdog.end_started_app(app)
        self.assertIsNotNone(app.poll())
        self.assertTrue(wait_for(lambda: not running(grandchild)), "a child of the app survived")
        bg_watchdog.end_started_app(app)  # an ended app is fine
        bg_watchdog.end_started_app(None)  # so is none

    def test_stop_refuses_an_endless_timeout(self):
        with self.assertRaises(ValueError):
            self.registry.stop(float("inf"))

    def test_file_lock_is_reentrant_and_exclusive(self):
        path = self.folder / "test.lock"
        # Test subprocesses execute fixed fixture/helper code using the local interpreter or Git.
        holder = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    f"""
                    import os, sys, time
                    sys.path.insert(0, {str(CODE)!r})
                    from pyapp.DONT_CHANGE.scripts.standalone.file_tools import FileLock
                    with FileLock({str(path)!r}):
                        open({str(path) + ".held"!r}, "w").close()
                        # Held until the test is done with it (at most 30 s), not for a fixed time.
                        for _ in range(600):
                            if os.path.exists({str(path) + ".release"!r}):
                                break
                            time.sleep(0.05)
                    """
                ),
            ]
        )
        self.addCleanup(holder.kill)
        self.assertTrue(wait_for(lambda: Path(str(path) + ".held").exists()))
        with self.assertRaises(TimeoutError), file_tools.FileLock(path, timeout=0.3):
            pass
        Path(str(path) + ".release").touch()
        holder.wait(timeout=30)
        with file_tools.FileLock(path, timeout=5), file_tools.FileLock(path, timeout=0.1):
            pass  # reentrant within one thread


if __name__ == "__main__":
    unittest.main()
