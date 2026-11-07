"""Windows-only: file lock, process registry, job objects and graceful Stop with real processes."""

import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from project_location import CODE

if os.name == "nt":
    from backend.DONT_CHANGE.scripts import runtime_state

CREATE_NEW_CONSOLE = 0x00000010

INSTANCE = """
import os, subprocess, sys, time
sys.path.insert(0, {code!r})
from backend.DONT_CHANGE.scripts import runtime_state
runtime_state.create_own_job()
registry = runtime_state.ProcessRegistry({registry!r})
grandchild = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
registry.register(grandchild.pid)
with open({ready!r}, "w") as stream:
    stream.write(str(grandchild.pid))
try:
    time.sleep(120)
except KeyboardInterrupt:
    with open({marker!r}, "w") as stream:
        stream.write("interrupted")
"""


def wait_for(condition, seconds=20.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.1)
    return False


def running(pid):
    with runtime_state.process_identity(pid) as identity:
        return identity is not None


@unittest.skipUnless(os.name == "nt", "Windows only")
class WindowsProcessTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.registry = runtime_state.ProcessRegistry(self.folder / "running")

    def start_instance(self, new_console=False):
        ready, marker = self.folder / "ready", self.folder / "marker"
        script = self.folder / "instance.py"
        script.write_text(
            INSTANCE.format(
                code=str(CODE), registry=str(self.registry.directory), ready=str(ready), marker=str(marker)
            ),
            encoding="utf-8",
        )
        process = subprocess.Popen(
            [sys.executable, "-E", "-s", str(script)], creationflags=CREATE_NEW_CONSOLE if new_console else 0
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

    def test_file_lock_is_reentrant_and_exclusive(self):
        path = self.folder / "test.lock"
        holder = subprocess.Popen(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    f"""
                    import sys, time
                    sys.path.insert(0, {str(CODE)!r})
                    from backend.DONT_CHANGE.scripts.runtime_state import FileLock
                    with FileLock({str(path)!r}):
                        open({str(path) + ".held"!r}, "w").close()
                        time.sleep(5)
                    """
                ),
            ]
        )
        self.addCleanup(holder.kill)
        self.assertTrue(wait_for(lambda: Path(str(path) + ".held").exists()))
        with self.assertRaises(TimeoutError), runtime_state.FileLock(path, timeout=0.3):
            pass
        holder.wait(timeout=30)
        with runtime_state.FileLock(path, timeout=5), runtime_state.FileLock(path, timeout=0.1):
            pass  # reentrant within one thread


if __name__ == "__main__":
    unittest.main()
