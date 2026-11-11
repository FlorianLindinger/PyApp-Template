"""scripts/entrypoint.py: how every launcher tool is run (exit codes, prompts, error messages)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import List, Sequence
from unittest import mock

from project_location import DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE.scripts import entrypoint
from pyapp.DONT_CHANGE.scripts.errors import SetupError


class RunFileTests(unittest.TestCase):
    def tool(self, source: str):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name, "tool.py")
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return path

    def run_tool(self, source: str, arguments: Sequence[str] = ()):
        prompts: List[str] = []
        with mock.patch.object(entrypoint, "acknowledge", prompts.append), mock.patch.object(
            entrypoint, "_show_console"
        ):
            code = entrypoint.run_file(self.tool(source), arguments)
        return code, prompts

    def test_exit_codes(self):
        cases = {
            "def main():\n    pass\n": 0,
            "def main():\n    return 4\n": 4,
            "import sys\ndef main():\n    sys.exit(2)\n": 2,
            "def main():\n    raise KeyboardInterrupt\n": 130,
            "def main():\n    raise ValueError('x')\n": 1,
            "from pyapp.DONT_CHANGE.scripts.errors import LaunchCancelled\ndef main():\n    raise LaunchCancelled()\n": 0,
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(self.run_tool(source)[0], expected)

    def test_prompts(self):
        self.assertEqual(self.run_tool("def main():\n    pass\n")[1], [])
        self.assertEqual(
            self.run_tool("pause_on_success = True\ndef main():\n    pass\n")[1], ["Press Enter to close this window."]
        )
        source = "pause_on_success = True\ndef main():\n    global pause_on_success\n    pause_on_success = False\n"
        self.assertEqual(self.run_tool(source)[1], [], "main() turning the pause off must be respected")
        self.assertEqual(len(self.run_tool("def main():\n    raise ValueError('x')\n")[1]), 1, "failures always wait")

    def test_arguments_reach_the_tool(self):
        source = "import sys\nresult = []\ndef main():\n    return 0 if sys.argv[1:] == ['a', 'b c'] else 9\n"
        self.assertEqual(self.run_tool(source, ["a", "b c"])[0], 0)

    def test_expected_problems_are_recognised_by_class(self):
        self.assertEqual(entrypoint.expected_problem(SetupError("fix this")), "fix this")
        self.assertIsNone(entrypoint.expected_problem(RuntimeError("bug")))


class RunnerProcessTests(unittest.TestCase):
    def test_runner_as_bootstrap_runs_it(self):
        with tempfile.TemporaryDirectory() as folder:
            tool = Path(folder, "tool.py")
            tool.write_text(
                "import sys\nfrom pyapp.DONT_CHANGE.scripts.errors import SettingsError\n"
                "def main():\n    print('argv', sys.argv[1:])\n    if sys.argv[1:] == ['bad']:\n"
                "        raise SettingsError('python_version is wrong')\n",
                encoding="utf-8",
            )
            command = [sys.executable, "-I", "-S", str(DONT_CHANGE / "scripts" / "entrypoint.py"), str(tool)]
            env = {**os.environ, "PYAPP_ENTRYPOINT_NO_PAUSE": "1"}
            # Test subprocesses execute fixed fixture/helper code using the local interpreter or Git.
            good = subprocess.run(  # noqa: S603
                [*command, "a", "b c"], capture_output=True, text=True, env=env, timeout=60, check=False
            )
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertIn("argv ['a', 'b c']", good.stdout)
            # Test subprocesses execute fixed fixture/helper code using the local interpreter or Git.
            bad = subprocess.run([*command, "bad"], capture_output=True, text=True, env=env, timeout=60, check=False)  # noqa: S603
            self.assertEqual(bad.returncode, 1)
            self.assertIn("ERROR  python_version is wrong", bad.stderr)
            self.assertNotIn("Traceback", bad.stderr)


if __name__ == "__main__":
    unittest.main()
