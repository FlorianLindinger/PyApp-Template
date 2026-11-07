"""Static checks of the batch, PowerShell and config files (any OS)."""

import re
import unittest

from project_location import CODE, DONT_CHANGE, PROJECT_ROOT


def batch_files():
    files = list(PROJECT_ROOT.glob("*.cmd")) + list(CODE.glob("backend/**/*.cmd")) + list(CODE.glob("backend/**/*.bat"))
    return [f for f in files if ".venv" not in f.parts]


class LauncherFileTests(unittest.TestCase):
    def test_batch_files_use_crlf(self):
        for path in batch_files():
            raw = path.read_bytes()
            self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"), f"{path.name} must use CRLF line endings")

    def test_referenced_scripts_exist(self):
        pattern = re.compile(r'(?:PYAPP_ENTRY_SCRIPT=|call ")%~dp0([^"%]+?\.(?:py|bat|cmd))', re.IGNORECASE)
        checked = 0
        for path in batch_files():
            for relative in pattern.findall(path.read_text(encoding="utf-8", errors="replace")):
                target = (path.parent / relative.replace("\\", "/")).resolve()
                self.assertTrue(target.is_file(), f'{path.name} refers to missing "{relative}"')
                checked += 1
        self.assertGreater(checked, 20)

    def test_runner_and_every_tool_have_a_main(self):
        self.assertIn("scripts\\entrypoint.py", (DONT_CHANGE / "bootstrap" / "run.bat").read_text(encoding="utf-8"))
        for tool in list((DONT_CHANGE / "actions").glob("*.py")) + [DONT_CHANGE / "scripts" / "dev_tools.py"]:
            self.assertRegex(tool.read_text(encoding="utf-8"), r"\ndef main\(", tool.name)

    def test_changelog_names_the_launcher_version(self):
        settings_text = (DONT_CHANGE / "backend_settings.py").read_text(encoding="utf-8")
        version = re.search(r'^LAUNCHER_VERSION = "(\d+\.\d+\.\d+)"', settings_text, re.MULTILINE)
        self.assertIsNotNone(version, "LAUNCHER_VERSION missing in backend_settings.py")
        changelog = (DONT_CHANGE / "CHANGELOG.md").read_text(encoding="utf-8")
        newest = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.MULTILINE)
        self.assertIsNotNone(newest, "CHANGELOG.md has no version heading")
        self.assertEqual(newest.group(1), version.group(1), "the newest CHANGELOG.md entry must match LAUNCHER_VERSION")

    def test_lint_configs_target_python_3_8(self):
        self.assertIn('target-version = "py38"', (DONT_CHANGE / "ruff.toml").read_text(encoding="utf-8"))
        self.assertIn('python-version = "3.8"', (DONT_CHANGE / "pyrefly.toml").read_text(encoding="utf-8"))

    def test_launcher_code_stays_python_3_8_compatible(self):
        forbidden = {
            r"^\s*match .+:\s*$": "match statement",
            r"\.removeprefix\(|\.removesuffix\(": "str.removeprefix/removesuffix",
            r"\bfunctools\.cache\b|from functools import cache\b": "functools.cache",
            r"zip\([^)]*strict=": "zip(strict=...)",
        }
        for path in DONT_CHANGE.rglob("*.py"):
            if path.name == "test_launcher_files.py":  # this file names the patterns
                continue
            text = path.read_text(encoding="utf-8")
            for pattern, what in forbidden.items():
                self.assertIsNone(
                    re.search(pattern, text, re.MULTILINE), f"{path.name} uses {what} (needs Python > 3.8)"
                )
            if re.search(r"\b(?:list|dict|tuple|set)\[|\w \| None", text) and path.name not in (
                "_pyapp.py",
                "script_wrapper.py",
            ):
                self.assertIn(
                    "from __future__ import annotations", text, f"{path.name} needs the __future__ import for 3.8"
                )


if __name__ == "__main__":
    unittest.main()
