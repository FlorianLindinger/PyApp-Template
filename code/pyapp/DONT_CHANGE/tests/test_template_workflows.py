"""scripts/template_workflows.py: Setup removes the template's own workflows from an app, and only then."""

from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Optional

from project_location import PROJECT_ROOT

# isort: split

from pyapp.DONT_CHANGE.scripts import template_workflows as tool

WORKFLOWS = PROJECT_ROOT / ".github" / "workflows"
GUARD = re.compile(r"(?m)^    if: endsWith\(github\.repository, '/PyApp-Template'\)\s*$")


def job_bodies(text: str):
    """(name, body) of each job of a workflow file."""
    jobs = text.replace("\r\n", "\n").split("\njobs:\n", 1)[1]
    return re.findall(r"(?m)^  ([\w-]+):\n((?:    .*\n|\n)*)", jobs)


class ShippedWorkflowTests(unittest.TestCase):
    def test_every_template_workflow_is_a_known_version_that_never_runs_in_an_app(self):
        current = sorted(WORKFLOWS.glob("pyapp-template-*.yml")) if WORKFLOWS.is_dir() else []
        if not current:
            self.skipTest("this copy has no template workflows")
        for path in current:
            with self.subTest(workflow=path.name):
                jobs = job_bodies(path.read_text(encoding="utf-8"))
                self.assertTrue(jobs)
                for name, body in jobs:
                    self.assertRegex(body, GUARD, f"job {name} would also run in an app")
                digest = tool.workflow_hash(path.read_bytes())
                self.assertIn(
                    digest,
                    tool.KNOWN_TEMPLATE_WORKFLOWS.get(path.name, frozenset()),
                    f"add {digest} to KNOWN_TEMPLATE_WORKFLOWS[{path.name!r}] in scripts/template_workflows.py",
                )


@unittest.skipUnless(sorted(WORKFLOWS.glob("pyapp-template-*.yml")), "this copy has no template workflows")
class RemovalTests(unittest.TestCase):
    def setUp(self):  # pyrefly: ignore[missing-override-decorator]
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.workflows = self.root / ".github" / "workflows"
        self.workflows.mkdir(parents=True)
        for path in WORKFLOWS.glob("pyapp-template-*.yml"):
            shutil.copyfile(path, self.workflows / path.name)

    def origin(self, url: Optional[str]) -> None:
        (self.root / ".git").mkdir()
        remote = f'[remote "origin"]\n\turl = {url}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n' if url else ""
        (self.root / ".git" / "config").write_text("[core]\n\tbare = false\n" + remote, encoding="utf-8")

    def remove(self):
        return tool.remove_template_workflows(str(self.root))

    def test_an_app_loses_the_unchanged_template_workflows_and_the_empty_folders(self):
        for url in ("https://github.com/someone/My-App.git", None):
            with self.subTest(url=url):
                self.setUp()
                self.origin(url)
                self.assertTrue(self.remove())
                self.assertFalse((self.root / ".github").exists())

    def test_a_downloaded_copy_without_git_is_an_app(self):
        self.assertTrue(self.remove())
        self.assertFalse((self.root / ".github").exists())

    def test_the_template_and_its_forks_keep_them(self):
        for url in ("https://github.com/someone/PyApp-Template.git", "git@github.com:x/pyapp-template"):
            with self.subTest(url=url):
                self.setUp()
                self.origin(url)
                self.assertEqual(self.remove(), [])
                self.assertTrue(any(self.workflows.iterdir()))

    def test_anything_else_in_the_folders_keeps_everything(self):
        for name in ("own workflow", "dependabot", "edited", "subfolder"):
            with self.subTest(case=name):
                self.setUp()  # a new folder each time: self.root and self.workflows change
                self.origin("https://github.com/someone/My-App.git")
                if name == "own workflow":
                    (self.workflows / "build.yml").write_text("x", encoding="utf-8")
                elif name == "dependabot":
                    (self.root / ".github" / "dependabot.yml").write_text("x", encoding="utf-8")
                elif name == "edited":
                    next(self.workflows.iterdir()).write_text("changed", encoding="utf-8")
                else:
                    (self.workflows / "more").mkdir()
                before = sorted(str(p) for p in (self.root / ".github").rglob("*"))
                self.assertEqual(self.remove(), [])
                self.assertEqual(sorted(str(p) for p in (self.root / ".github").rglob("*")), before)

    def test_line_endings_do_not_matter(self):
        for path in self.workflows.iterdir():
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.assertTrue(self.remove())

    def test_a_git_file_instead_of_a_folder_keeps_everything(self):
        (self.root / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
        self.assertEqual(self.remove(), [])


if __name__ == "__main__":
    unittest.main()
