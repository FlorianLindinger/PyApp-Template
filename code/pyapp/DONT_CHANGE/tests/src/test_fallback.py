"""actions/start_without_launcher.py: starting the app without the launcher, from a copy of the project."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Tuple

from project_location import DONT_CHANGE

SCRIPT = DONT_CHANGE / "actions" / "start_without_launcher.py"

APP = """\
import os, sys
print("args", sys.argv[1:], os.environ.get("MODE"), os.environ.get("PROGRAM_NAME"), os.getcwd())
sys.exit(3)
"""


def load_script():
    spec = importlib.util.spec_from_file_location("start_without_launcher_under_test", str(SCRIPT))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FallbackStartTests(unittest.TestCase):
    def project(self, settings: str) -> Path:
        """A minimal project with only the fallback script of DONT_CHANGE: nothing else of the launcher."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        # Resolved: the script shows long paths, while the temporary folder may be given in the short 8.3 form.
        code = Path(folder.name).resolve() / "code"
        (code / "pyapp" / "DONT_CHANGE" / "actions").mkdir(parents=True)
        shutil.copyfile(SCRIPT, code / "pyapp" / "DONT_CHANGE" / "actions" / SCRIPT.name)
        (code / "pyapp" / "developer_settings.py").write_text(settings, encoding="utf-8")
        (code / "app").mkdir()
        (code / "app" / "run.py").write_text(APP, encoding="utf-8")
        return code

    def start(self, code: Path, *arguments: str) -> Tuple[int, str]:
        # Test subprocesses execute fixed fixture code using the local interpreter.
        completed = subprocess.run(  # noqa: S603
            [sys.executable, str(code / "pyapp" / "DONT_CHANGE" / "actions" / SCRIPT.name), *arguments],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYAPP_FALLBACK_SOURCE": "path", "PYAPP_FALLBACK_VENV": "missing"},
            timeout=60,
            check=False,
        )
        return completed.returncode, completed.stdout + completed.stderr

    def test_the_app_runs_with_its_settings_and_its_exit_code_is_kept(self):
        settings = (
            'program_name = "Probe"\n'
            'main_script_path = "..\\\\app\\\\run.py"\n'
            'args_for_main_py = ["a b"]\n'
            'environment_for_main_py = {"MODE": "x"}\n'
            'terminal_shortcut_name = f"{program_name}"  # not a literal: skipped, not an error\n'
            'packages = """\nno-such-package-pyapp>=1  # comment\n"""\n'
        )
        code = self.project(settings)
        exit_code, output = self.start(code, "more")
        self.assertEqual(exit_code, 3, output)
        self.assertIn(f"args ['a b', 'more'] x Probe {code / 'app'}", output)
        self.assertIn("no-such-package-pyapp  ✗ missing", output)  # a long name keeps its distance
        self.assertIn("does not exist yet", output)  # the state of the app's environment

    def test_settings_that_do_not_parse_still_allow_a_start(self):
        code = self.project('main_script_path = "..\\\\app\\\\run.py"\nbroken = (\n')
        # The default main script (code/main.py) is used instead, and its absence is reported.
        exit_code, output = self.start(code)
        self.assertEqual(exit_code, 1, output)
        self.assertIn("could not be read", output)
        self.assertIn("The main script does not exist", output)

    def test_requirement_names(self):
        names = load_script().requirement_names(
            "# comment\nrequests>=2  # web\nnumpy==2.* \\\n    --hash=sha256:aa\npkg @ https://x.org/a#egg=pkg\n\n"
        )
        self.assertEqual(names, ["requests", "numpy", "pkg"])


if __name__ == "__main__":
    unittest.main()
