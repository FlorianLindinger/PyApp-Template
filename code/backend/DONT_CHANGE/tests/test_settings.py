"""developer_settings.py: validation, friendly errors, and editing without damaging the file."""

import re
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import support
from project_location import CODE, DONT_CHANGE

# isort: split

from backend.DONT_CHANGE.scripts import config, entrypoint
from backend.DONT_CHANGE.scripts.errors import SettingsError


def append(lines):
    return lambda text: text + "".join(line + "\r\n" for line in lines)


class ValidationTests(unittest.TestCase):
    def test_shipped_settings_are_valid(self):
        with support.temporary_settings() as (_, load):
            config.validate(load())

    def test_wrong_values_are_reported_by_name(self):
        bad = [
            'close_after_failure = "no"',
            "play_sound_after_failure = 3",
            "print_prepend = 5",
            'terminal_shortcut_name = "  "',
            "stop_timeout_seconds = -1",
            'instance_policy = "sometimes"',
            'main_script_path = "notes.txt"',
            'environment_for_main_py = {"A": 1}',
            'packages = ["requests", "  "]',
            "error_date_format = 5",
        ]
        with support.temporary_settings(append(bad)) as (_, load), self.assertRaises(SettingsError) as raised:
            config.validate(load())
        message = str(raised.exception)
        for line in bad:
            self.assertIn(line.split(" =")[0], message)

    def test_bootstrap_settings_must_be_unique_and_unindented(self):
        lines = ['uv_cache = "local"', "if True:", '    uv_prefer = "local"']
        with support.temporary_settings(append(lines)):
            problems = config._bootstrap_literal_problems()
        self.assertTrue(any("uv_cache is set 2 times" in p for p in problems), problems)
        self.assertTrue(any(p.startswith("uv_prefer (line") for p in problems), problems)

    def test_errors_in_the_file_get_a_line_number_instead_of_a_traceback(self):
        def typo(text):
            return text.replace("start_menu_shortcuts = True", "start_menu_shortcuts = Ture")

        with support.temporary_settings(typo) as (_, load):
            try:
                load()
            except NameError as error:  # not assertRaises: it drops the traceback that is inspected
                problem = entrypoint.settings_file_problem(error)
            else:
                self.fail("the typo did not raise NameError")
        self.assertIsNotNone(problem)
        self.assertIn("NameError", problem)
        self.assertRegex(problem, r"line \d+")
        self.assertIn("capital letter", problem)

    def test_errors_elsewhere_are_not_blamed_on_the_settings(self):
        self.assertIsNone(entrypoint.settings_file_problem(ValueError("x")))


class DefaultsTests(unittest.TestCase):
    """Settings missing in an older developer_settings.py fall back to data/dev_settings_default.py."""

    DEFAULTS = DONT_CHANGE / "data" / "dev_settings_default.py"

    def test_defaults_file_is_complete_and_valid(self):
        defaults = self.DEFAULTS.read_text(encoding="utf-8")
        with support.temporary_settings(lambda text: defaults) as (_, load):
            config.validate(load())

    @staticmethod
    def settings_part(path):
        """The file without its header and without the block that opens it when run directly."""
        text = path.read_text(encoding="utf-8")
        text = text[text.index("from __future__ import annotations\n") :]
        end = text.find("# open this file if someone runs it")
        return re.sub(r"\s*# =+\s*$", "", (text if end < 0 else text[:end]).rstrip())

    def test_defaults_file_is_identical_to_the_shipped_settings(self):
        project = CODE / "backend" / "developer_settings.py"
        if not re.search(r'(?m)^program_name = "PyApp-Template"', project.read_text(encoding="utf-8")):
            self.skipTest("a project made from the template has its own settings")
        self.maxDiff = None
        self.assertEqual(
            self.settings_part(project).splitlines(),
            self.settings_part(self.DEFAULTS).splitlines(),
            "data/dev_settings_default.py must match developer_settings.py (settings, values and comments)",
        )

    def test_missing_settings_get_their_defaults(self):
        def drop(text):
            text = re.sub(r"(?m)^start_minimized\b.*\n", "", text)
            text = re.sub(r"(?m)^terminal_shortcut_name\b.*\n", "", text)
            return text.replace('program_name = "PyApp-Template"', 'program_name = "Other App"')

        with support.temporary_settings(drop) as (_, load):
            module = load()
            filled = config.fill_missing_settings(module)
            self.assertEqual(sorted(filled), ["start_minimized", "terminal_shortcut_name"])
            self.assertIs(module.start_minimized, False)
            self.assertEqual(module.terminal_shortcut_name, "Other App")  # f"{program_name}" of the project
            config.validate(module)

    def test_editing_a_missing_setting_appends_it(self):
        with support.temporary_settings(lambda text: re.sub(r"(?m)^uv_version\b.*\n", "", text)) as (path, load):
            config.edit_settings({"uv_version": ">=0.9"})
            self.assertEqual(load().uv_version, ">=0.9")
            self.assertIn("\r\n", path.read_bytes().decode("utf-8")[-20:])

    def test_bootstrap_defaults_match_the_defaults_file(self):
        script = (DONT_CHANGE / "bootstrap" / "resolve_runtime.ps1").read_text(encoding="utf-8")
        found = re.findall(r"Get-Setting \$settings '(\w+)' ('[^']*'|\$true|\$false)", script)
        self.assertGreaterEqual(len(found), 8)
        expressions = config.default_setting_expressions(str(self.DEFAULTS))
        for name, literal in found:
            expected = {"$true": True, "$false": False}.get(literal, literal.strip("'"))
            self.assertEqual(expressions[name].value, expected, f"default of {name} in resolve_runtime.ps1")


class MainScriptTests(unittest.TestCase):
    def check(self, relative):
        """Validate main_script_path pointing at a file below a temporary code folder."""
        with tempfile.TemporaryDirectory() as folder:
            code = Path(folder) / "code"
            script = code / relative
            script.parent.mkdir(parents=True)
            script.write_text("", encoding="utf-8")
            (code / "backend").mkdir(exist_ok=True)
            with support.temporary_settings(append([f'main_script_path = r"{script}"'])) as (
                _,
                load,
            ), mock.patch.object(config, "PYTHON_SCRIPTS_DIR", str(code)), mock.patch.object(
                config, "BACKEND_DIR", str(code / "backend")
            ):
                config.validate(load())

    def test_any_file_in_the_code_folder_is_allowed(self):
        self.check("start.py")
        self.check("app/gui/run.pyw")

    def test_the_backend_folder_is_refused(self):
        with self.assertRaises(SettingsError) as raised:
            self.check("backend/run.py")
        self.assertIn("main_script_path", str(raised.exception))

    def test_a_missing_file_is_refused(self):
        with support.temporary_settings(append(['main_script_path = "..\\\\no_such_file.py"'])) as (
            _,
            load,
        ), self.assertRaises(SettingsError) as raised:
            config.validate(load())
        self.assertIn("does not exist", str(raised.exception))


class EditingTests(unittest.TestCase):
    def test_edit_keeps_crlf_comments_and_writes_safe_literals(self):
        value = 'Flo\'s "App" C:\\x'

        def with_comment(text):
            return text + 'uv_cache = "global"  # trailing comment\r\n'

        with support.temporary_settings(with_comment) as (path, load):
            config.edit_settings({"program_name": value, "uv_cache": "local", "python_version": "3.13"})
            raw = path.read_bytes()
            module = load()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"), "line endings changed")
        self.assertEqual(module.program_name, value)
        self.assertEqual(module.terminal_shortcut_name, value)  # f-strings still follow program_name
        self.assertEqual(module.uv_cache, "local")  # the last definition is the one Python uses
        self.assertIn(b'uv_cache = "local"  # trailing comment', raw)

    def test_list_setting_round_trip(self):
        packages = ['pywin32; sys_platform == "win32"', "requests>=2", "a\\b"]
        with support.temporary_settings() as (_, load):
            config.set_list_setting("packages", packages)
            self.assertEqual(load().packages, packages)
            config.set_list_setting("packages", [])
            self.assertEqual(load().packages, [])

    def test_pasted_requirements_block(self):
        text = "# pasted\nrequests>=2  # via x\n\nnumpy==2.1 --hash=sha256:ab --hash=sha256:cd\npkg @ https://x.org/a#egg=pkg\n"
        self.assertEqual(
            config.parse_requirements(text), ["requests>=2", "numpy==2.1", "pkg @ https://x.org/a#egg=pkg"]
        )
        block = ['packages = """', "requests>=2  # via x", "numpy==2.1", '"""']
        with support.temporary_settings(append(block)) as (_, load):
            config.validate(load())
            config.set_list_setting("packages", ["a", "b>=1"])
            self.assertEqual(load().packages.split(), ["a", "b>=1"])  # still a block

    def test_settings_turn_a_block_into_a_list(self):
        module = types.SimpleNamespace(packages="requests\nnumpy>=2\n", MISSING_SETTINGS_FILLED_IN=[])
        with mock.patch.object(config.importlib, "import_module", return_value=module):
            self.assertEqual(config.settings().packages, ["requests", "numpy>=2"])

    def test_bad_line_in_a_block_is_named(self):
        block = ['packages = """', "requests", "-r base.txt", '"""']
        with support.temporary_settings(append(block)) as (_, load), self.assertRaises(SettingsError) as raised:
            config.validate(load())
        self.assertIn("-r base.txt", str(raised.exception))

    def test_unknown_setting_is_an_error(self):
        with support.temporary_settings(), self.assertRaises(SettingsError):
            config.edit_settings({"no_such_setting": 1})


class ShippedFileTests(unittest.TestCase):
    def test_settings_file_uses_crlf(self):
        raw = (CODE / "backend" / "developer_settings.py").read_bytes()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))


if __name__ == "__main__":
    unittest.main()
