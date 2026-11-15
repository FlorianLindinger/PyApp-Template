"""actions/start_without_launcher.py: starting the app without the launcher, from a copy of the project."""

from __future__ import annotations

import importlib.util
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path
from typing import Dict, Optional, Tuple

from project_location import DONT_CHANGE

SCRIPT = DONT_CHANGE / "actions" / "start_without_launcher.py"
LINUX_START = DONT_CHANGE.parent / "Start without launcher --LINUX.sh"

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
    def test_explicit_working_directory_is_used_and_a_missing_one_is_reported(self):
        code = self.project('main_script_path = "../app/run.py"\nworking_directory = "../work"\n')
        working = code / "work"
        working.mkdir()
        status, output = self.start(code)
        self.assertEqual(status, 3, output)
        self.assertIn(str(working), output)
        working.rmdir()
        status, output = self.start(code)
        self.assertEqual(status, 1, output)
        self.assertIn("working_directory does not exist", output)

    def select_linux_python(self, code: Path, command: str) -> None:
        shell = code / "pyapp" / LINUX_START.name
        shell.write_text(
            shell.read_text(encoding="utf-8").replace('python_command=""', "python_command=" + shlex.quote(command)),
            encoding="utf-8",
        )

    def test_linux_shell_entrypoint_has_lf_line_endings(self):
        raw = LINUX_START.read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.startswith(b"#!/bin/sh\n"))

    def project(self, settings: str) -> Path:
        """A minimal project with only the fallback script of DONT_CHANGE: nothing else of the launcher."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        # Resolved: the script shows long paths, while the temporary folder may be given in the short 8.3 form.
        code = Path(folder.name).resolve() / "code"
        (code / "pyapp" / "DONT_CHANGE" / "actions").mkdir(parents=True)
        shutil.copyfile(SCRIPT, code / "pyapp" / "DONT_CHANGE" / "actions" / SCRIPT.name)
        shutil.copyfile(LINUX_START, code / "pyapp" / LINUX_START.name)
        (code / "pyapp" / "developer_settings.py").write_text(settings, encoding="utf-8")
        (code / "app").mkdir()
        (code / "app" / "run.py").write_text(APP, encoding="utf-8")
        return code

    def start(
        self,
        code: Path,
        *arguments: str,
        linux: bool = False,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str]:
        # Fixed shell/interpreter and repository-owned fixture scripts, without shell interpolation.
        command = (
            ["/bin/sh", str(code / "pyapp" / LINUX_START.name)]
            if linux
            else [sys.executable, str(code / "pyapp" / "DONT_CHANGE" / "actions" / SCRIPT.name)]
        )
        completed = subprocess.run(  # noqa: S603
            [*command, *arguments],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYAPP_FALLBACK_SOURCE": "path", "PYAPP_FALLBACK_VENV": "missing", **(env or {})},
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
        self.assertIn("Change main_script_path in developer_settings.py", output)
        self.assertIn("make sure the Python file exists at this path", output)

    def test_nested_main_imports_code_root_without_losing_local_or_existing_pythonpath(self):
        code = self.project('main_script_path = "../app/run.py"\n')
        (code / "root_helper.py").write_text('VALUE = "root"\n', encoding="utf-8")
        (code / "app" / "local_helper.py").write_text('VALUE = "local"\n', encoding="utf-8")
        (code / "collision.py").write_text('VALUE = "wrong priority"\n', encoding="utf-8")
        (code / "app" / "collision.py").write_text('VALUE = "script first"\n', encoding="utf-8")
        external = code / "extra imports"
        external.mkdir()
        (external / "extra_helper.py").write_text('VALUE = "extra"\n', encoding="utf-8")
        (code / "app" / "run.py").write_text(
            "import root_helper, local_helper, collision, extra_helper\n"
            "print(root_helper.VALUE, local_helper.VALUE, collision.VALUE, extra_helper.VALUE)\n",
            encoding="utf-8",
        )
        status, output = self.start(code, env={"PYTHONPATH": str(external)})
        self.assertEqual(status, 0, output)
        self.assertIn("root local script first extra", output)

    def test_requirement_names(self):
        names = load_script().requirement_names(
            "# comment\nrequests>=2  # web\nnumpy==2.* \\\n    --hash=sha256:aa\npkg @ https://x.org/a#egg=pkg\n\n"
        )
        self.assertEqual(names, ["requests", "numpy", "pkg"])

    @unittest.skipUnless(os.name == "posix", "Linux/POSIX shell")
    def test_linux_shell_uses_system_python_and_preserves_arguments_and_paths(self):
        code = self.project(
            'program_name = "Probe"\nmain_script_path = "..\\\\app\\\\run.py"\nargs_for_main_py = ["a b"]\nenvironment_for_main_py = {"MODE": "x"}\n'
        )
        status, output = self.start(code, "more with spaces", "$(literal)", linux=True, cwd=code.parent)
        self.assertEqual(status, 3, output)
        self.assertIn("['a b', 'more with spaces', '$(literal)'] x Probe", output)
        self.assertIn(str(code / "app"), output)
        self.assertIn("system Python", output)

    @unittest.skipUnless(os.name == "posix", "Linux/POSIX shell")
    def test_linux_shell_uses_an_explicit_python_path_with_spaces(self):
        code = self.project('main_script_path = "../app/run.py"\n')
        environment = code / "chosen environment"
        venv.EnvBuilder(with_pip=False).create(environment)
        self.select_linux_python(code, str(environment / "bin" / "python"))
        status, output = self.start(code, linux=True)
        self.assertEqual(status, 3, output)
        self.assertIn(str(environment / "bin" / "python"), output)
        self.assertIn("Python selected by python_command", output)

    @unittest.skipUnless(os.name == "posix", "Linux/POSIX shell")
    def test_linux_shell_ignores_the_generated_environment(self):
        code = self.project('main_script_path = "../app/run.py"\n')
        generated_python = code / "pyapp" / "generated" / ".venv" / "bin" / "python"
        generated_python.parent.mkdir(parents=True)
        generated_python.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        generated_python.chmod(0o755)
        status, output = self.start(code, linux=True)
        self.assertEqual(status, 3, output)
        self.assertIn("system Python", output)
        self.assertNotIn("the app's environment", output)

    @unittest.skipUnless(os.name == "posix", "Linux/POSIX shell")
    def test_linux_shell_selects_a_versioned_command_on_path(self):
        code = self.project('main_script_path = "../app/run.py"\n')
        commands = code / "commands"
        commands.mkdir()
        command = f"python{sys.version_info.major}.{sys.version_info.minor}"
        (commands / command).symlink_to(sys.executable)
        self.select_linux_python(code, command)
        status, output = self.start(code, linux=True, env={"PATH": str(commands)})
        self.assertEqual(status, 3, output)
        self.assertIn("Python selected by python_command", output)

    @unittest.skipUnless(os.name == "posix", "Linux/POSIX shell")
    def test_linux_shell_resolves_relative_python_paths_from_its_own_folder(self):
        code = self.project('main_script_path = "../app/run.py"\n')
        commands = code / "pyapp" / "my python $(literal)"
        commands.mkdir()
        (commands / "python").symlink_to(sys.executable)
        self.select_linux_python(code, "my python $(literal)/python")
        status, output = self.start(code, linux=True, cwd=code.parent)
        self.assertEqual(status, 3, output)

    @unittest.skipUnless(os.name == "posix", "Linux/POSIX shell")
    def test_linux_shell_does_not_substitute_system_python_for_an_invalid_selection(self):
        code = self.project('main_script_path = "../app/run.py"\n')
        self.select_linux_python(code, "no-such-python-pyapp")
        status, output = self.start(code, linux=True)
        self.assertEqual(status, 1, output)
        self.assertIn("Selected Python does not start or is older than 3.8", output)
        self.assertIn("Change python_command", output)

    @unittest.skipUnless(os.name == "posix", "Linux/POSIX shell")
    def test_linux_shell_reports_missing_python_and_missing_helper(self):
        code = self.project("")
        empty_path = code / "empty-path"
        empty_path.mkdir()
        status, output = self.start(code, linux=True, env={"PATH": str(empty_path)})
        self.assertEqual(status, 1)
        self.assertIn("No working Python 3.8+ found", output)
        (code / "pyapp" / "DONT_CHANGE" / "actions" / SCRIPT.name).unlink()
        status, output = self.start(code, linux=True)
        self.assertEqual(status, 1)
        self.assertIn("Fallback helper not found", output)


if __name__ == "__main__":
    unittest.main()
