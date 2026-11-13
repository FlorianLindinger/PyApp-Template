"""Static checks of the shipped batch, settings and config files, the READMEs and the test groups (any OS)."""

import re
import unittest

from project_location import CODE, DONT_CHANGE, PROJECT_ROOT


def batch_files():
    files = list(PROJECT_ROOT.glob("*.cmd")) + list(CODE.glob("pyapp/**/*.cmd")) + list(CODE.glob("pyapp/**/*.bat"))
    return [f for f in files if ".venv" not in f.parts]


class LauncherFileTests(unittest.TestCase):
    def test_batch_and_settings_files_use_crlf(self):
        # The settings files are opened in Notepad and edited by the launcher, which keeps CRLF.
        settings = [CODE / "pyapp" / "developer_settings.py", DONT_CHANGE / "data" / "dev_settings_default.py"]
        for path in batch_files() + settings:
            raw = path.read_bytes()
            self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"), f"{path.name} must use CRLF line endings")

    def test_referenced_scripts_exist(self):
        pattern = re.compile(r'(?:PYAPP_ENTRY_SCRIPT=|call ")%~dp0([^"%]+?\.(?:py|bat|cmd))', re.IGNORECASE)
        checked = 0
        for path in batch_files():
            for relative in pattern.findall(path.read_text(encoding="utf-8", errors="replace")):
                if "tmp" in relative.replace("\\", "/").split("/"):
                    continue  # created at runtime
                target = (path.parent / relative.replace("\\", "/")).resolve()
                self.assertTrue(target.is_file(), f'{path.name} refers to missing "{relative}"')
                checked += 1
        self.assertGreater(checked, 20)

    def test_the_file_tables_name_existing_files(self):
        """The READMEs describe every file; a rename must not leave them pointing at nothing."""
        # The tables name files relative to the folder their section is about.
        bases = [DONT_CHANGE / folder for folder in ("", "scripts", "runtime", "actions", "bootstrap", "B", "data")]
        missing = []
        for line in (DONT_CHANGE / "README.md").read_text(encoding="utf-8").splitlines():
            first_cell = line.split("|")[1] if line.startswith("| `") else ""
            for quoted in re.findall(r"`([^`]+)`", first_cell):
                name = quoted.rstrip("/")
                if not re.fullmatch(r"[\w.-]+(/[\w.-]+)*", name) or ("." not in name and "/" not in name):
                    continue  # not a path: a shortcut name, a placeholder, ...
                if name.startswith("tmp"):
                    continue  # created at runtime
                if not any((base / name).exists() for base in bases):
                    missing.append(name)
        self.assertEqual(missing, [], "named in DONT_CHANGE/README.md, but not found")
        from groups import all_test_files

        readme = (DONT_CHANGE / "tests" / "README.md").read_text(encoding="utf-8")
        listed = set(re.findall(r"(?m)^\| `(test_\w+\.py)`", readme))
        self.assertEqual(listed, {path.name for path in all_test_files()}, "tests/README.md file table")

    def test_runner_and_every_tool_have_a_main(self):
        self.assertIn("scripts\\entrypoint.py", (DONT_CHANGE / "bootstrap" / "run.bat").read_text(encoding="utf-8"))
        for tool in [*list((DONT_CHANGE / "actions").glob("*.py")), DONT_CHANGE / "scripts" / "dev_tools" / "main.py"]:
            self.assertRegex(tool.read_text(encoding="utf-8"), r"\ndef main\(", tool.name)

    def test_bootstrap_and_launcher_agree_on_the_environment_folder(self):
        settings = (DONT_CHANGE / "backend_settings.py").read_text(encoding="utf-8")
        self.assertIn('GENERATED_DIR = BACKEND_DIR + "\\\\generated"', settings)
        script = (DONT_CHANGE / "bootstrap" / "resolve_runtime.py").read_text(encoding="utf-8")
        self.assertIn('GENERATED_DIR = BACKEND_DIR / "generated"', script)
        batch = (DONT_CHANGE / "bootstrap" / "ensure_runtime.bat").read_text(encoding="utf-8")
        self.assertIn("..\\..\\generated\\.python-version", batch)

    def test_the_runtime_cache_stamp_names_every_bootstrap_setting(self):
        from pyapp.DONT_CHANGE.scripts.config import BOOTSTRAP_SETTINGS

        batch = (DONT_CHANGE / "bootstrap" / "ensure_runtime.bat").read_text(encoding="utf-8")
        self.assertEqual(sorted(re.findall(r'if "%%A"=="(\w+)"', batch)), sorted(BOOTSTRAP_SETTINGS))

    def test_the_bootstrap_avoids_what_antivirus_programs_distrust(self):
        for name in ("resolve_runtime.py", "ensure_runtime.bat", "run.bat"):
            text = (DONT_CHANGE / "bootstrap" / name).read_text(encoding="utf-8").lower()
            for pattern in ("| iex", "invoke-expression", "certutil.exe -", "dllimport"):
                self.assertNotIn(pattern, text, f"{name} uses {pattern}")

    def test_the_setup_runs_no_powershell_script(self):
        for name in ("resolve_runtime.bat", "ensure_runtime.bat", "run.bat"):
            text = (DONT_CHANGE / "bootstrap" / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("executionpolicy", text, name)
            self.assertNotIn(".ps1", text, name)

    def test_the_app_runs_in_utf8_mode(self):
        from pyapp.DONT_CHANGE.scripts.env.venv import APP_PYTHON_FLAGS

        self.assertEqual(APP_PYTHON_FLAGS[APP_PYTHON_FLAGS.index("-X") + 1], "utf8")

    def test_changelog_names_the_launcher_version(self):
        settings_text = (DONT_CHANGE / "backend_settings.py").read_text(encoding="utf-8")
        version = re.search(r'^LAUNCHER_VERSION = "(\d+\.\d+\.\d+)"', settings_text, re.MULTILINE)
        self.assertIsNotNone(version, "LAUNCHER_VERSION missing in backend_settings.py")
        changelog = (DONT_CHANGE / "CHANGELOG.md").read_text(encoding="utf-8")
        newest = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.MULTILINE)
        self.assertIsNotNone(newest, "CHANGELOG.md has no version heading")
        self.assertEqual(newest.group(1), version.group(1), "the newest CHANGELOG.md entry must match LAUNCHER_VERSION")


class TestFolderTests(unittest.TestCase):
    def test_every_test_file_is_in_exactly_one_group(self):
        from groups import GROUPS, all_test_files

        listed = [name for names in GROUPS.values() for name in names]
        self.assertEqual(len(listed), len(set(listed)), "a file is in more than one group")
        found = [path.name for path in all_test_files()]
        # Groups name files without their folder.
        self.assertEqual(len(found), len(set(found)), "two test folders have a file of the same name")
        self.assertEqual(sorted(listed), sorted(found), "groups.py must list every test file")
        # Each group has its own section in tests/README.md and its own launcher.
        readme = (DONT_CHANGE / "tests" / "README.md").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"(?m)^### `(\w+)`", readme), list(GROUPS), "tests/README.md group sections")
        for name in GROUPS:
            launcher = DONT_CHANGE / "tests" / f"run_{name}_tests.cmd"
            self.assertIn(f'run_launcher_tests.cmd" {name} ', launcher.read_text(encoding="utf-8"), launcher.name)


if __name__ == "__main__":
    unittest.main()
