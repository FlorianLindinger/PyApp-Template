"""developer_settings.py: validation, friendly errors, and editing without damaging the file."""

import unittest

import support
from project_location import CODE

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
            'close_after_crash = "no"',
            "play_sound_after_failure = 3",
            "settings_sub_icon_scale = 2",
            'log_sub_icon_alignment = "middle-ish"',
            "print_prepend = 5",
            'terminal_shortcut_name = "  "',
            "stop_timeout_seconds = -1",
            'instance_policy = "sometimes"',
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

    def test_unknown_setting_is_an_error(self):
        with support.temporary_settings(), self.assertRaises(SettingsError):
            config.edit_settings({"no_such_setting": 1})


class ShippedFileTests(unittest.TestCase):
    def test_settings_file_uses_crlf(self):
        raw = (CODE / "backend" / "developer_settings.py").read_bytes()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))


if __name__ == "__main__":
    unittest.main()
