"""Static checks of the shipped batch, settings and config files, the READMEs and the test groups (any OS)."""

import ast
import re
import sys
import unittest
from typing import Dict, Set

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
        bases = [
            DONT_CHANGE / folder
            for folder in ("", "scripts", "scripts/actions", "scripts/runtime", "scripts/bootstrap", "B", "data")
        ]
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
        self.assertIn(
            "..\\entrypoint.py", (DONT_CHANGE / "scripts" / "bootstrap" / "run.bat").read_text(encoding="utf-8")
        )
        for tool in [
            *list((DONT_CHANGE / "scripts" / "actions").glob("*.py")),
            DONT_CHANGE / "scripts" / "dev_tools" / "main.py",
        ]:
            self.assertRegex(tool.read_text(encoding="utf-8"), r"\ndef main\(", tool.name)

    def test_bootstrap_and_launcher_agree_on_the_environment_folder(self):
        settings = (DONT_CHANGE / "pyapp_settings.py").read_text(encoding="utf-8")
        self.assertIn('GENERATED_DIR = BACKEND_DIR + "\\\\generated"', settings)
        script = (DONT_CHANGE / "scripts" / "bootstrap" / "resolve_runtime.py").read_text(encoding="utf-8")
        self.assertIn('GENERATED_DIR = BACKEND_DIR / "generated"', script)
        batch = (DONT_CHANGE / "scripts" / "bootstrap" / "ensure_runtime.bat").read_text(encoding="utf-8")
        self.assertIn("..\\..\\generated\\.python-version", batch)

    def test_the_runtime_cache_stamp_names_every_bootstrap_setting(self):
        from pyapp.DONT_CHANGE.scripts.config import BOOTSTRAP_SETTINGS

        batch = (DONT_CHANGE / "scripts" / "bootstrap" / "ensure_runtime.bat").read_text(encoding="utf-8")
        self.assertEqual(sorted(re.findall(r'if "%%A"=="(\w+)"', batch)), sorted(BOOTSTRAP_SETTINGS))

    def test_the_bootstrap_avoids_what_antivirus_programs_distrust(self):
        for name in ("resolve_runtime.py", "ensure_runtime.bat", "run.bat"):
            text = (DONT_CHANGE / "scripts" / "bootstrap" / name).read_text(encoding="utf-8").lower()
            for pattern in ("| iex", "invoke-expression", "certutil.exe -", "dllimport"):
                self.assertNotIn(pattern, text, f"{name} uses {pattern}")

    def test_the_setup_runs_no_powershell_script(self):
        for name in ("resolve_runtime.bat", "ensure_runtime.bat", "run.bat"):
            text = (DONT_CHANGE / "scripts" / "bootstrap" / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("executionpolicy", text, name)
            self.assertNotIn(".ps1", text, name)

    def test_the_app_runs_in_utf8_mode(self):
        from pyapp.DONT_CHANGE.scripts.env.venv import APP_PYTHON_FLAGS

        self.assertEqual(APP_PYTHON_FLAGS[APP_PYTHON_FLAGS.index("-X") + 1], "utf8")

    def test_changelog_names_the_launcher_version(self):
        settings_text = (DONT_CHANGE / "pyapp_settings.py").read_text(encoding="utf-8")
        version = re.search(r'^LAUNCHER_VERSION = "(\d+\.\d+\.\d+)"', settings_text, re.MULTILINE)
        self.assertIsNotNone(version, "LAUNCHER_VERSION missing in pyapp_settings.py")
        changelog = (DONT_CHANGE / "CHANGELOG.md").read_text(encoding="utf-8")
        newest = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.MULTILINE)
        self.assertIsNotNone(newest, "CHANGELOG.md has no version heading")
        self.assertEqual(newest.group(1), version.group(1), "the newest CHANGELOG.md entry must match LAUNCHER_VERSION")


# Folders whose README files are not the project's documentation (installed or generated content).
SKIPPED_PARTS = {".git", ".venv", "node_modules", "tmp", "__pycache__", ".ruff_cache", "site-packages"}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def readme_files():
    return [path for path in PROJECT_ROOT.rglob("README.md") if not SKIPPED_PARTS.intersection(path.parts)]


def heading_anchors(text: str):
    """The #anchors GitHub gives a document's headings (lowercase, punctuation dropped, "-" for spaces)."""
    anchors: Set[str] = set()
    seen: Dict[str, int] = {}
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", re.sub(r"```.*?```", "", text, flags=re.DOTALL)):
        slug = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # a link in a heading keeps its text
        slug = re.sub(r"[^\w\- ]", "", re.sub(r"<[^>]+>", "", slug).strip().lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")  # GitHub numbers repeated headings
    return anchors


class StandaloneTests(unittest.TestCase):
    def test_standalone_modules_need_nothing_but_the_standard_library_and_each_other(self):
        # scripts/standalone promises: copy a file (plus the siblings it names) anywhere and it works.
        # So no launcher imports and no packages; siblings only by relative import, named in the
        # docstring; and a file that runs as a script imports no siblings (relative imports need a package).
        folder = DONT_CHANGE / "scripts" / "standalone"
        files = sorted(folder.glob("*.py"))
        siblings = {path.stem for path in files}
        self.assertGreater(len(files), 1)
        stdlib = getattr(sys, "stdlib_module_names", None)  # Python 3.10+
        for path in files:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
            docstring = ast.get_docstring(tree) or ""
            runs_as_script = 'if __name__ == "__main__":' in text
            with self.subTest(path.name):
                self.assertIn("Standalone:", docstring, "the docstring states the promise")
                for node in ast.walk(tree):
                    where = f"{path.name}:{getattr(node, 'lineno', 0)}"
                    if isinstance(node, ast.ImportFrom) and node.level:
                        self.assertEqual(node.level, 1, f"{where}: only siblings in this folder")
                        self.assertFalse(runs_as_script, f"{where}: a file run as a script cannot import siblings")
                        used = [node.module] if node.module else [alias.name for alias in node.names]
                        for name in used:
                            self.assertIn(name, siblings, f"{where}: no sibling {name}.py")
                            self.assertIn(f"{name}.py", docstring, f"{where}: name {name}.py in the docstring")
                        continue
                    if isinstance(node, ast.ImportFrom):
                        names = [node.module or ""]
                    elif isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                    else:
                        continue
                    for name in names:
                        top = name.split(".")[0]
                        self.assertNotEqual(top, "pyapp", f"{where}: imports the launcher")
                        self.assertNotIn(top, siblings, f"{where}: import siblings relatively (from . import {top})")
                        if stdlib is not None:
                            self.assertIn(top, stdlib, f"{where}: {name} is not standard library")


class ReadmeLinkTests(unittest.TestCase):
    def test_links_in_the_readmes_point_to_existing_files_and_headings(self):
        import urllib.parse

        files = readme_files()
        self.assertGreaterEqual(len(files), 5)
        broken = []
        for readme in files:
            text = re.sub(r"```.*?```", "", readme.read_text(encoding="utf-8"), flags=re.DOTALL)  # not code examples
            for target in MARKDOWN_LINK.findall(text):
                if re.match(r"[a-z][a-z0-9+.-]*:", target):
                    continue  # https:, mailto:, ...: not checked offline
                path, _, anchor = target.partition("#")
                document = (readme.parent / urllib.parse.unquote(path)).resolve() if path else readme
                if PROJECT_ROOT.resolve() not in document.parents and document != PROJECT_ROOT.resolve():
                    continue  # leaves the repository, e.g. GitHub's ../../archive/... download link
                place = f"{readme.relative_to(PROJECT_ROOT).as_posix()}: {target}"
                if not document.exists():
                    broken.append(place + "  (no such file)")
                elif (
                    anchor
                    and document.suffix == ".md"
                    and anchor not in heading_anchors(document.read_text(encoding="utf-8"))
                ):
                    broken.append(place + "  (no such heading)")
        self.assertEqual(broken, [], "broken links in README files")

    def test_heading_anchors_follow_github(self):
        # The README headings use an en dash (U+2013), which GitHub drops like other punctuation.
        text = "# Tests, linting and type checking\n## `actions/` \u2013 entry tools\n## Notes\n## Notes\n"
        self.assertEqual(
            heading_anchors(text),
            {"tests-linting-and-type-checking", "actions--entry-tools", "notes", "notes-1"},
        )


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
