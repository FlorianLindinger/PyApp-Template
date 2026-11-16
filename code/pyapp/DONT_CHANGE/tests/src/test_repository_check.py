"""pyapp_tools/check_repository: problems that break clones, other PCs or Windows."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Set
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "pyapp_tools" / "src"), *sys.path]):
    import _paths  # noqa: F401 - imported by the tool; the tools folder is only on sys.path here
    import check_repository as tool


class NameCheckTests(unittest.TestCase):
    def test_case_only_differences(self):
        found = tool.case_conflicts(["docs/Readme.md", "docs/README.md", "other.md"])
        self.assertEqual([p.detail for p in found], ["docs/Readme.md / docs/README.md"])

    def test_names_windows_cannot_use(self):
        names = ["ok/file.py", "aux.txt", "logs/con", "a:b.txt", "trailing./x", "space /y", "fine.name.txt"]
        found = {p.detail: p.check for p in tool.windows_unsafe(names, Path("C:/r"))}
        self.assertEqual(
            found,
            {
                "aux.txt": "Reserved Windows name",
                "logs/con": "Reserved Windows name",
                "a:b.txt": "Character Windows forbids",
                "trailing./x": "Ends with a dot or space",
                "space /y": "Ends with a dot or space",
            },
        )

    def test_long_paths(self):
        found = tool.windows_unsafe(["a" * 250], Path("C:/r"))
        self.assertEqual([p.check for p in found], ["Long path"])

    def test_tracked_caches_and_environments(self):
        names = ["app/__pycache__/x.cpython-314.pyc", ".venv/Scripts/python.exe", "lib/mod.pyc", "app/main.py"]
        self.assertEqual(len(tool.generated_tracked(names)), 3)


@unittest.skipIf(shutil.which("git") is None, "needs Git")
class GitCheckTests(unittest.TestCase):
    """A real temporary repository for the checks that ask Git."""

    def new_repository(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.git("init", "-q")

    def git(self, *arguments: str) -> None:
        # Fixed Git commands in a temporary test repository.
        subprocess.run(  # noqa: S603
            ["git", "-C", str(self.root), "-c", "core.autocrlf=false", *arguments],  # noqa: S607
            check=True,
            capture_output=True,
        )

    def write(self, name: str, data: bytes = b"x\n") -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_a_clean_repository_passes(self):
        self.new_repository()
        self.write(".gitignore", b"/logs/\n")
        self.write("main.py")
        self.git("add", ".")
        self.assertEqual(tool.all_problems(self.root, 5.0), [])

    def launcher_ignore_fixture(self) -> None:
        """Use the shipped rules under deliberately broad parent patterns in a disposable repo."""
        self.new_repository()
        self.write(
            ".gitignore",
            b"*.py\n*.md\n*.cmd\n*.sh\n*.json\n*.lock\n*.ico\n*.png\n*.gitignore\n.gitattributes\n.python-version\ndev_tools/\nDONT_CHANGE/\ngenerated/\nicons/\ntests/\n",
        )
        base = DONT_CHANGE.parent
        for relative in (
            ".gitignore",
            "DONT_CHANGE/.gitignore",
            "DONT_CHANGE/tests/tmp/.gitignore",
            "DONT_CHANGE/pyapp_tools/zip_releases/.gitignore",
        ):
            self.write("code/pyapp/" + relative, (base / relative).read_bytes())

    def ignored_paths(self, names: List[str]) -> Set[str]:
        for name in names:
            if not (self.root / name).exists():
                self.write(name)
        return set(
            tool.git(
                "check-ignore", "--no-index", "--stdin", stdin="\n".join(names) + "\n", root=self.root
            ).splitlines()
        )

    def test_launcher_sources_and_portable_generated_files_override_parent_patterns(self):
        self.launcher_ignore_fixture()
        files = [
            "code/pyapp/" + name
            for name in (
                "developer_settings.py",
                ".gitignore",
                "DONT_CHANGE/.gitattributes",
                "README.md",
                "Developer Tools.cmd",
                "Start without launcher --LINUX.sh",
                "dev_tools/packages/add_packages.cmd",
                "DONT_CHANGE/runtime/new_module.py",
                "icons/icon.ico",
                "icons/icon.png",
                "tests/test_example.py",
                "generated/README.md",
                "generated/uv.lock",
                "generated/.python-version",
                "generated/auto_generated_icons.json",
            )
        ]
        self.assertEqual(self.ignored_paths(files), set())

    def test_launcher_protection_keeps_runtime_artifacts_and_deeper_exclusions_ignored(self):
        self.launcher_ignore_fixture()
        files = [
            "code/pyapp/" + name
            for name in (
                "__pycache__/settings.cpython-314.pyc",
                "DONT_CHANGE/runtime/loose.pyc",
                ".ruff_cache/check",
                "tests/.pytest_cache/check",
                "dev_tools/.mypy_cache/check",
                ".venv/bin/python",
                "node_modules/package/index.js",
                "generated/pyproject.toml",
                "generated/browser_terminal_key.txt",
                "generated/shortcuts_created_by_setup.json",
                "generated/.venv/Scripts/python.exe",
                "generated/uv-download-staging/uv.exe",
                "generated/future-local-state.json",
                "DONT_CHANGE/tmp/runtime.cmd",
                "DONT_CHANGE/tests/tmp/probe.txt",
                "DONT_CHANGE/pyapp_tools/zip_releases/release.zip",
            )
        ]
        self.assertEqual(self.ignored_paths(files), set(files))

    def test_launcher_rules_cannot_override_an_excluded_ancestor(self):
        self.launcher_ignore_fixture()
        self.write(".gitignore", b"/code/\n")
        names = ["code/pyapp/developer_settings.py"]
        self.assertEqual(self.ignored_paths(names), set(names))
        self.write(".gitignore", b"/code/\n!/code/\n")
        self.assertEqual(self.ignored_paths(names), set())

    def test_tracked_files_that_are_ignored(self):
        self.new_repository()
        self.write("build/out.txt")
        self.git("add", "build/out.txt")
        self.write(".gitignore", b"build/\n")
        self.assertEqual([p.detail for p in tool.tracked_but_ignored(self.root)], ["build/out.txt"])

    def test_an_exception_inside_an_excluded_folder_has_no_effect(self):
        self.new_repository()
        # "keep/" excludes the folder itself, so Git never sees the "!" line; "keep/*" would work.
        self.write(".gitignore", b"keep/\n!keep/.gitkeep\nworks/*\n!works/.gitkeep\n")
        self.write("keep/.gitkeep", b"")
        self.write("works/.gitkeep", b"")
        found = tool.broken_exceptions(self.root)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].detail.startswith("keep/.gitkeep"))

    def test_mixed_line_endings(self):
        self.new_repository()
        self.write("mixed.txt", b"a\r\nb\nc\r\n")
        self.write("crlf.txt", b"a\r\nb\r\n")
        self.write("lf.txt", b"a\nb\n")
        self.write("image.bin", b"\0\r\n\n")
        self.git("add", ".")
        self.assertEqual([p.detail for p in tool.mixed_line_endings(self.root)], ["mixed.txt (2 CRLF, 1 LF)"])

    def test_nested_repositories_but_not_in_ignored_folders(self):
        self.new_repository()
        self.write(".gitignore", b"/cache/\n")
        (self.root / "vendor" / "lib" / ".git").mkdir(parents=True)
        (self.root / "cache" / "source" / ".git").mkdir(parents=True)
        self.assertEqual([p.detail for p in tool.nested_repositories(self.root)], ["vendor/lib"])

    def test_why_a_path_is_ignored_or_kept(self):
        self.new_repository()
        self.write(".gitignore", b"keep/*\n!keep/.gitkeep\n")
        self.write("keep/.gitkeep", b"")
        self.write("keep/data.csv")
        answers = dict(tool.why_ignored(["keep/data.csv", "keep/.gitkeep", "main.py"], self.root))
        self.assertEqual(answers["keep/data.csv"], ".gitignore:1:keep/*")
        self.assertEqual(answers["keep/.gitkeep"], ".gitignore:2:!keep/.gitkeep")
        self.assertEqual(answers["main.py"], "")

    def test_ignored_files_are_listed_by_folder_and_size(self):
        self.new_repository()
        self.write(".gitignore", b"/cache/\nlogs/*.txt\n")
        self.write("cache/a.bin", b"\0" * 3000)
        self.write("cache/sub/b.bin", b"\0" * 1000)
        self.write("logs/one.txt", b"x" * 10)
        self.write("logs/two.txt", b"x" * 20)
        self.write("logs/.gitkeep", b"")
        self.git("add", "logs/.gitkeep")
        self.assertEqual(tool.ignored_entries(self.root), [("cache/", 4000, 2), ("logs/", 30, 2)])

    def test_large_files(self):
        self.new_repository()
        self.write("big.bin", b"\0" * 2_200_000)
        self.write("small.txt")
        found = tool.oversized(["big.bin", "small.txt"], 2.0, self.root)
        self.assertEqual([p.detail for p in found], ["big.bin (2.1 MB)"])


if __name__ == "__main__":
    unittest.main()
