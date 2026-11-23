"""scripts/entrypoint.py: how every launcher tool is run (exit codes, prompts, error messages)."""

from __future__ import annotations

import os
import shutil
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


@mock.patch.dict(os.environ, {"NO_COLOR": "1"})
class RunFileTests(unittest.TestCase):
    def tool(self, source: str):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name, "tool.py")
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return path

    def run_tool(self, source: str, arguments: Sequence[str] = (), batch_pauses: bool = False):
        prompts: List[str] = []
        # The test runner itself is started through run.bat, which sets this variable.
        environment = {"PYAPP_BATCH_PAUSES_ON_FAILURE": "1" if batch_pauses else ""}
        with mock.patch.object(entrypoint, "acknowledge", prompts.append), mock.patch.object(
            entrypoint, "_show_console"
        ), mock.patch.dict(os.environ, environment):
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

    def test_after_a_failure_only_run_bat_waits_when_it_says_so(self):
        # run.bat waits after every failure itself (also when Python cannot start the entrypoint):
        # the entrypoint must not ask a second time, but a success with pause_on_success still asks.
        for source in (
            "def main():\n    raise ValueError('x')\n",
            "from pyapp.DONT_CHANGE.scripts.errors import SetupError\ndef main():\n    raise SetupError('x')\n",
            "import sys\ndef main():\n    sys.exit(3)\n",
            "pause_on_success = True\ndef main():\n    return 2\n",
        ):
            with self.subTest(source=source):
                self.assertEqual(self.run_tool(source, batch_pauses=True)[1], [])
                self.assertEqual(len(self.run_tool(source)[1]), 1, "without run.bat the entrypoint waits itself")
        self.assertEqual(
            self.run_tool("pause_on_success = True\ndef main():\n    pass\n", batch_pauses=True)[1],
            ["Press Enter to close this window."],
        )

    def test_expected_problems_are_recognised_by_class(self):
        self.assertEqual(entrypoint.expected_problem(SetupError("fix this")), "fix this")
        self.assertIsNone(entrypoint.expected_problem(RuntimeError("bug")))


@mock.patch.dict(os.environ, {"NO_COLOR": "1"})
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

    def test_app_modules_named_like_stdlib_modules_do_not_shadow_the_launchers(self):
        """code/random.py etc. belong to the app; the launcher imports most stdlib modules lazily."""
        with tempfile.TemporaryDirectory() as folder:
            code = Path(folder, "code")
            launcher = code / "pyapp" / "DONT_CHANGE"
            # The entrypoint finds the code folder from its own location, so it must run from a copy.
            shutil.copytree(DONT_CHANGE / "scripts", launcher / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copyfile(DONT_CHANGE / "pyapp_settings.py", launcher / "pyapp_settings.py")
            shadowing = ("random", "signal", "json", "uuid")
            for name in shadowing:
                (code / f"{name}.py").write_text(
                    f"raise RuntimeError('app {name}.py was imported')\n", encoding="utf-8"
                )
            tool = Path(folder, "tool.py")
            tool.write_text(f"def main():\n    import {', '.join(shadowing)}\n", encoding="utf-8")
            # Test subprocesses execute fixed fixture/helper code using the local interpreter or Git.
            completed = subprocess.run(  # noqa: S603
                [sys.executable, "-I", "-S", str(launcher / "scripts" / "entrypoint.py"), str(tool)],
                capture_output=True,
                text=True,
                env={**os.environ, "PYAPP_ENTRYPOINT_NO_PAUSE": "1"},
                timeout=60,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
