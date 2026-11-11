"""scripts/template_repo.py: Setup turns on the Git hooks in the template's own repository only."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional

import project_location  # also makes this checkout's code importable
from pyapp.DONT_CHANGE.scripts import template_repo


class FakeGit:
    """Answers the few git commands the function uses; records what it changed."""

    def __init__(self, remote: Optional[str], hooks_path: Optional[str] = None):
        self.remote = remote
        self.config: Dict[str, str] = {} if hooks_path is None else {"core.hooksPath": hooks_path}

    def __call__(self, arguments: List[str]) -> Optional[str]:
        if arguments == ["remote", "get-url", "origin"]:
            return self.remote
        if arguments == ["config", "--local", "--get", "core.hooksPath"]:
            return self.config.get("core.hooksPath")
        if arguments[:2] == ["config", "--local"] and len(arguments) == 4:
            self.config[arguments[2]] = arguments[3]
            return ""
        raise AssertionError(f"unexpected git command: {arguments}")


class TemplateHooksTests(unittest.TestCase):
    def enable(self, git: FakeGit, with_git_folder: bool = True) -> bool:
        with tempfile.TemporaryDirectory() as folder:
            if with_git_folder:
                (Path(folder) / ".git").mkdir()
            return template_repo.enable_template_git_hooks(folder, git)

    def test_a_clone_of_the_template_gets_the_hooks(self):
        for remote in (
            "https://github.com/FlorianLindinger/PyApp-Template.git",
            "https://github.com/someone/pyapp-template",
            "git@github.com:someone/PyApp-Template.git",
        ):
            with self.subTest(remote=remote):
                git = FakeGit(remote)
                self.assertTrue(self.enable(git))
                self.assertEqual(git.config["core.hooksPath"], template_repo.HOOKS_PATH)

    def test_an_app_built_from_the_template_is_left_alone(self):
        for remote in ("https://github.com/someone/My-App.git", "https://github.com/someone/PyApp-Template-fork", None):
            with self.subTest(remote=remote):
                git = FakeGit(remote)
                self.assertFalse(self.enable(git))
                self.assertEqual(git.config, {})

    def test_an_existing_hooks_path_is_never_replaced(self):
        git = FakeGit("https://github.com/x/PyApp-Template.git", hooks_path=".husky")
        self.assertFalse(self.enable(git))
        self.assertEqual(git.config["core.hooksPath"], ".husky")

    def test_nothing_happens_outside_a_git_repository(self):
        git = FakeGit("https://github.com/x/PyApp-Template.git")
        self.assertFalse(self.enable(git, with_git_folder=False))
        self.assertEqual(git.config, {})

    def test_the_hooks_path_exists(self):
        hooks = project_location.PROJECT_ROOT / template_repo.HOOKS_PATH
        self.assertTrue((hooks / "pre-commit").is_file())
        self.assertTrue((hooks / "pre-push").is_file())


if __name__ == "__main__":
    unittest.main()
