"""developer_settings.py: validation, friendly errors, and editing without damaging the file."""

from __future__ import annotations

import ast
import importlib.util
import os
import py_compile
import re
import tempfile
import types
import unittest
from pathlib import Path
from typing import Callable, Iterable, List, Set
from unittest import mock

import support
from project_location import CODE, DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE.scripts import config, entrypoint
from pyapp.DONT_CHANGE.scripts.errors import SettingsError


def append(lines: Iterable[str]) -> Callable[[str], str]:
    return lambda text: text + "".join(line + "\r\n" for line in lines)


class ValidationTests(unittest.TestCase):
    def test_packages_accepts_only_strings(self):
        empty_list: List[str] = []
        for value in (["requests", "numpy>=2"], empty_list, ("requests",), None, 42):
            with self.subTest(value=value), support.temporary_settings(append([f"packages = {value!r}"])) as (_, load):
                module = load()
                with self.assertRaises(SettingsError) as raised:
                    config.validate(module)
                self.assertIn("packages", str(raised.exception))
                self.assertIn("requirements string", str(raised.exception))
                with self.assertRaises(SettingsError):
                    config.all_packages(module)
        for value in ("", "requests", "requests\nnumpy>=2\n"):
            with self.subTest(value=value), support.temporary_settings(append([f"packages = {value!r}"])) as (_, load):
                module = load()
                config.validate(module)
                self.assertEqual(module.packages, value)
                self.assertEqual(config.all_packages(module), value.splitlines())

    DISABLED_TEXT_SETTINGS = (
        "requirements_path",
        "user_settings_path",
        "log_path",
        "crash_log_path",
        "print_prepend",
        "input_prepend",
        "log_print_prepend",
        "log_input_prepend",
        "terminal_bg_color",
        "terminal_text_color",
        "tab_bar_color",
        *config.SHORTCUT_NAME_SETTINGS,
    )

    def test_empty_strings_disable_optional_text_settings(self):
        with support.temporary_settings(append(f'{name} = ""' for name in self.DISABLED_TEXT_SETTINGS)) as (_, load):
            module = load()
            config.validate(module)
            self.assertEqual(config.requirements_file_entries(module), [])
            self.assertIsNone(config.requirements_file_path(module))
            for name in self.DISABLED_TEXT_SETTINGS:
                self.assertEqual(getattr(module, name), "", name)

    def test_empty_user_settings_path_reports_that_the_feature_is_disabled(self):
        from pyapp.DONT_CHANGE.actions import open_file

        with support.temporary_settings(append(['user_settings_path = ""'])) as (_, load), mock.patch.object(
            open_file, "settings", load
        ), mock.patch.object(open_file.sys, "argv", ["open_file.py", "settings"]), self.assertRaises(
            SettingsError
        ) as raised:
            open_file.main()
        self.assertIn('user_settings_path is ""', str(raised.exception))

    def test_none_is_rejected_with_the_empty_string_alternative(self):
        with support.temporary_settings(append(f"{name} = None" for name in self.DISABLED_TEXT_SETTINGS)) as (
            _,
            load,
        ), self.assertRaises(SettingsError) as raised:
            config.validate(load())
        message = str(raised.exception)
        for name in self.DISABLED_TEXT_SETTINGS:
            with self.subTest(name=name):
                diagnostic = next(
                    line for line in message.splitlines() if re.match(re.escape(name) + r"(?:\s*=|:)", line.strip())
                )
                self.assertIn('""', diagnostic)
                self.assertNotIn("or None", diagnostic)

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

    def test_uv_version_must_be_readable_by_the_bootstrap(self):
        def with_uv_version(value: str) -> Callable[[str], str]:
            # Replaced, not appended: a [bootstrap] setting may be defined only once.
            return lambda text: re.sub(r"(?m)^uv_version = .*$", f'uv_version = "{value}"', text)

        for value in (">=0..9", "1.", "0.11.32,,>="):
            with self.subTest(value=value), support.temporary_settings(with_uv_version(value)) as (_, load):
                with self.assertRaises(SettingsError) as raised:
                    config.validate(load())
                self.assertIn("uv_version", str(raised.exception))
        for value in ("", "0.11.32", ">=0.9,<1", "~=0.11", "==0.11.32, !=0.11.31"):
            with self.subTest(value=value), support.temporary_settings(with_uv_version(value)) as (_, load):
                self.assertEqual(load().uv_version, value)
                config.validate(load())

    def test_terminal_colors(self):
        code = config.terminal_color_code
        # `color 9` would make the text light blue: a missing half is the console default instead.
        self.assertEqual((code("9", ""), code("", "F"), code("9", "F"), code("", "")), ("97", "0F", "9F", ""))
        for lines in (
            ['terminal_bg_color = "9"', 'terminal_text_color = "9"'],
            ['terminal_bg_color = "7"', 'terminal_text_color = ""'],
        ):
            with self.subTest(lines=lines), support.temporary_settings(append(lines)) as (_, load):
                with self.assertRaises(SettingsError) as raised:
                    config.validate(load())
                self.assertIn("terminal_bg_color and terminal_text_color", str(raised.exception))

    def test_stop_timeout_must_be_finite(self):
        for value in ('float("inf")', 'float("nan")', "-0.5"):
            with self.subTest(value=value):
                line = f"stop_timeout_seconds = {value}"
                with support.temporary_settings(append([line])) as (_, load), self.assertRaises(SettingsError):
                    config.validate(load())
        finite = append(["stop_timeout_seconds = 0", "stop_timeout_seconds = 2.5"])
        with support.temporary_settings(finite) as (_, load):
            config.validate(load())

    def test_the_bootstrap_tags_name_exactly_the_settings_the_bootstrap_reads(self):
        # "[bootstrap]" in a setting's comment tells people its extra rules (validated below).
        tagged: Set[str] = set()
        comments: List[str] = []
        for line in (CODE / "pyapp" / "developer_settings.py").read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                comments.append(line)
                continue
            assignment = re.match(r"(\w+)\s*(?::[^=]*)?=", line)
            if assignment and any("[bootstrap]" in comment for comment in comments):
                tagged.add(assignment.group(1))
            comments = []
        self.assertEqual(sorted(tagged), sorted(config.BOOTSTRAP_SETTINGS))

    def test_bootstrap_settings_must_be_unique_and_unindented(self):
        lines = ['uv_cache = "local"', "if True:", '    uv_prefer = "local"']
        with support.temporary_settings(append(lines)):
            problems = config._bootstrap_literal_problems()
        self.assertTrue(any("uv_cache is set 2 times" in p for p in problems), problems)
        self.assertTrue(any(p.startswith("uv_prefer (line") for p in problems), problems)

    def test_errors_in_the_file_get_a_line_number_instead_of_a_traceback(self):
        def typo(text: str):
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
    def settings_part(path: Path):
        """Compare values and comments; internal defaults may annotate otherwise untyped empty containers."""
        text = path.read_text(encoding="utf-8")
        text = text[text.index("# IMPORTANT:\n") :]
        text = re.sub(r"(?m)^(\w+): [^=\n]+ =", r"\1 =", text)
        end = text.find("# open this file if someone runs it")
        return re.sub(r"\s*# =+\s*$", "", (text if end < 0 else text[:end]).rstrip())

    def test_defaults_file_is_identical_to_the_shipped_settings(self):
        project = CODE / "pyapp" / "developer_settings.py"
        if not re.search(r'(?m)^program_name = "PyApp-Template"', project.read_text(encoding="utf-8")):
            self.skipTest("a project made from the template has its own settings")
        self.maxDiff = None
        self.assertEqual(
            self.settings_part(project).splitlines(),
            self.settings_part(self.DEFAULTS).splitlines(),
            "data/dev_settings_default.py must match developer_settings.py (settings, values and comments)",
        )

    def test_missing_settings_get_their_defaults(self):
        def drop(text: str):
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
        script = (DONT_CHANGE / "bootstrap" / "resolve_runtime.py").read_text(encoding="utf-8")
        found = re.findall(r'setting\(settings, "(\w+)", ("[^"]*"|True|False)\)', script)
        self.assertGreaterEqual(len(found), 8)
        expressions = config.default_setting_expressions(str(self.DEFAULTS))
        for name, literal in found:
            expected = {"True": True, "False": False}.get(literal, literal.strip('"'))
            expression = expressions[name]
            if not isinstance(expression, ast.Constant):
                self.fail(f"The bootstrap default of {name} must be a literal.")
            self.assertEqual(expression.value, expected, f"default of {name} in resolve_runtime.py")


class MainScriptTests(unittest.TestCase):
    def check(self, relative: str):
        """Validate main_script_path pointing at a file below a temporary code folder."""
        with tempfile.TemporaryDirectory() as folder:
            code = Path(folder) / "code"
            script = code / relative
            script.parent.mkdir(parents=True)
            script.write_text("", encoding="utf-8")
            (code / "pyapp").mkdir(exist_ok=True)
            with support.temporary_settings(append([f'main_script_path = r"{script}"'])) as (
                _,
                load,
            ), mock.patch.object(config, "PYTHON_SCRIPTS_DIR", str(code)), mock.patch.object(
                config, "BACKEND_DIR", str(code / "pyapp")
            ):
                config.validate(load())

    def test_any_file_in_the_code_folder_is_allowed(self):
        self.check("start.py")
        self.check("app/gui/run.pyw")

    def test_the_backend_folder_is_refused(self):
        with self.assertRaises(SettingsError) as raised:
            self.check("pyapp/run.py")
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

        def with_comment(text: str):
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

    def test_edit_keeps_parentheses_around_a_value_on_its_own_lines(self):
        def parenthesized(text: str):
            return text + '\r\nuv_version = (\r\n    "0.1.0"\r\n)  # note\r\nlast_line = 1\r\n'

        with support.temporary_settings(parenthesized) as (path, load):
            config.edit_settings({"uv_version": "0.2.0"})
            module = load()
            self.assertEqual((module.uv_version, module.last_line), ("0.2.0", 1))
            self.assertIn(")  # note", path.read_bytes().decode("utf-8"))

    def test_a_quick_edit_of_the_same_length_is_not_hidden_by_old_bytecode(self):
        with support.temporary_settings() as (path, load):
            config.edit_settings({"uv_cache": "local"})
            py_compile.compile(str(path), cfile=importlib.util.cache_from_source(str(path)))
            self.assertEqual(load().uv_cache, "local")
            modified = path.stat().st_mtime
            config.edit_settings({"uv_cache": "share"})  # same length
            # Same size and modification time as recorded in the .pyc: it would still look valid.
            os.utime(str(path), (modified, modified))
            self.assertEqual(load().uv_cache, "share")

    def test_strings_with_line_breaks_and_controls_stay_valid_python(self):
        value = 'a\nb\rc\td\x00e\x7f "q" \\ 名前 😀'
        with support.temporary_settings() as (path, load):
            config.edit_settings({"program_name": value})
            ast.parse(path.read_text(encoding="utf-8"))
            self.assertEqual(load().program_name, value)

    def test_values_that_cannot_be_written_leave_the_file_unchanged(self):
        with support.temporary_settings() as (path, _):
            before = path.read_bytes()
            for value in (float("inf"), float("nan")):
                with self.assertRaises(SettingsError):
                    config.edit_settings({"stop_timeout_seconds": value})
            self.assertEqual(path.read_bytes(), before)

    def test_package_entries_with_line_breaks_are_rejected_without_writing(self):
        block = ['packages = """', "requests", '"""']
        with support.temporary_settings(append(block)) as (path, _):
            before = path.read_bytes()
            with self.assertRaises(SettingsError):
                config.set_list_setting("packages", ["a\nb", "c"])
            self.assertEqual(path.read_bytes(), before)

    def test_package_string_round_trip_preserves_quotes_and_backslashes(self):
        packages = ['pywin32; sys_platform == "win32"', "requests>=2", "a\\b"]
        with support.temporary_settings() as (_, load):
            config.set_list_setting("packages", packages)
            self.assertIsInstance(load().packages, str)
            self.assertEqual(config.package_entries(load()), packages)
            config.set_list_setting("packages", [])
            self.assertIsInstance(load().packages, str)
            self.assertEqual(config.package_entries(load()), [])

    def test_pasted_requirements_with_hash_continuation_lines(self):
        text = (
            "numpy==1.0 \\\n    --hash=sha256:aa \\\n    --hash=sha256:bb\n"
            "    # via app\nrequests>=2,<3 \\\n    --hash=sha256:cc\n"
        )
        self.assertEqual(config.parse_requirements(text), ["numpy==1.0", "requests>=2,<3"])
        self.assertEqual(config.parse_requirements("last==1 \\\n  --hash=sha256:dd \\"), ["last==1"])

    def test_pasted_requirements_block(self):
        text = "# pasted\nrequests>=2  # via x\n\nnumpy==2.1 --hash=sha256:ab --hash=sha256:cd\npkg @ https://x.org/a#egg=pkg\n"
        self.assertEqual(
            config.parse_requirements(text), ["requests>=2", "numpy==2.1", "pkg @ https://x.org/a#egg=pkg"]
        )
        block = ['packages = """', "requests>=2  # via x", "numpy==2.1", '"""']
        with support.temporary_settings(append(block)) as (path, load):
            config.validate(load())
            config.set_list_setting("packages", ["a", "b>=1"])
            self.assertEqual(support.load_settings_file(path).packages.split(), ["a", "b>=1"])  # still a block

    def test_comments_in_a_requirements_block_survive_edits(self):
        block = [
            'packages = """',
            "# GUI",
            "requests>=2  # pinned because of the proxy bug",
            "",
            "# numerics",
            "numpy>=2",
            "scipy==1.0 --hash=sha256:aa",
            "six  # only for py2 code",
            '"""',
        ]
        with support.temporary_settings(append(block)) as (path, load):
            # Kept, upgraded (same package), removed and added entries at once.
            config.set_list_setting("packages", ["requests>=2", "numpy>=2.1", "scipy==1.0", "pillow"])
            self.assertEqual(config.package_entries(load()), ["requests>=2", "numpy>=2.1", "scipy==1.0", "pillow"])
            text = path.read_text(encoding="utf-8")
            expected = [
                "# GUI",
                "requests>=2  # pinned because of the proxy bug",
                "",
                "# numerics",
                "numpy>=2.1",
                "scipy==1.0 --hash=sha256:aa",
                "pillow",
                '"""',
            ]
            self.assertIn("\n".join(expected), text)
            self.assertNotIn("six", text)
            # Upgrading an entry keeps the comment that explains it.
            config.set_list_setting("packages", ["requests>=2.32", "numpy>=2.1", "scipy==1.0", "pillow"])
            self.assertIn("requests>=2.32  # pinned because of the proxy bug\n", path.read_text(encoding="utf-8"))
            # Removing every package keeps the notes, so they are there when packages come back.
            config.set_list_setting("packages", [])
            self.assertEqual(config.package_entries(load()), [])
            self.assertIn("# numerics", path.read_text(encoding="utf-8"))

    def test_a_block_with_backslashes_is_regenerated(self):
        """Written back between plain triple quotes, a backslash from an escape would change the value."""
        # Kept as is, the comment's "\t" and "\n" would become a tab and a line break: "ew" a package.
        block = ['packages = r"""', r"# built from C:\temp\new", "numpy", '"""']
        with support.temporary_settings(append(block)) as (_, load):
            config.set_list_setting("packages", ["requests"])
            self.assertEqual(config.package_entries(load()), ["requests"])

    def test_settings_keep_the_packages_string(self):
        module = types.SimpleNamespace(packages="requests\nnumpy>=2\n", MISSING_SETTINGS_FILLED_IN=[])
        with mock.patch.object(config.importlib, "import_module", return_value=module):
            self.assertEqual(config.settings().packages, "requests\nnumpy>=2\n")
            self.assertEqual(config.package_entries(config.settings()), ["requests", "numpy>=2"])

    def test_bad_line_in_a_block_is_named(self):
        block = ['packages = """', "requests", "-r base.txt", '"""']
        with support.temporary_settings(append(block)) as (_, load), self.assertRaises(SettingsError) as raised:
            config.validate(load())
        self.assertIn("-r base.txt", str(raised.exception))

    def test_unknown_setting_is_an_error(self):
        with support.temporary_settings(), self.assertRaises(SettingsError):
            config.edit_settings({"no_such_setting": 1})


if __name__ == "__main__":
    unittest.main()
