"""The github_actions setting: Setup creates, updates and removes only its own workflow files."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import List

import support
from project_location import DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE.scripts import config
from pyapp.DONT_CHANGE.scripts.app_workflows import sync_app_workflows
from pyapp.DONT_CHANGE.scripts.errors import SettingsError


class SyncTests(unittest.TestCase):
    def setUp(self):  # pyrefly: ignore[missing-override-decorator]
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.source = Path(folder.name) / "source"
        self.target = Path(folder.name) / "repo" / ".github" / "workflows"
        self.source.mkdir()
        (self.source / "leaks.yml").write_text("one", encoding="utf-8")

    def sync(self, wanted: List[str]):
        return sync_app_workflows(wanted, str(self.source), str(self.target))

    def test_nothing_wanted_creates_no_folder(self):
        self.assertEqual(self.sync([]), ([], []))
        self.assertFalse(self.target.exists())

    def test_added_then_unchanged_then_updated(self):
        self.assertEqual(self.sync(["leaks"]), (["leaks"], []))
        self.assertEqual((self.target / "pyapp-app-leaks.yml").read_text(encoding="utf-8"), "one")
        self.assertEqual(self.sync(["leaks"]), ([], []))
        (self.source / "leaks.yml").write_text("two", encoding="utf-8")
        self.assertEqual(self.sync(["leaks"]), (["leaks"], []))

    def test_only_its_own_files_are_removed(self):
        self.sync(["leaks"])
        (self.target / "my-own.yml").write_text("mine", encoding="utf-8")
        self.assertEqual(self.sync([]), ([], ["leaks"]))
        self.assertTrue((self.target / "my-own.yml").exists())
        self.assertFalse((self.target / "pyapp-app-leaks.yml").exists())


class SettingTests(unittest.TestCase):
    def test_every_choice_has_a_workflow_file(self):
        for name in config.APP_WORKFLOWS:
            self.assertTrue((DONT_CHANGE / "data" / "workflows" / f"{name}.yml").is_file(), name)

    def test_the_default_is_off(self):
        with support.temporary_settings() as (_, load):
            self.assertEqual(load().github_actions, [])

    def test_unknown_names_are_reported(self):
        def bad(text: str):
            return text + 'github_actions = ["nope"]\r\n'

        with support.temporary_settings(bad) as (_, load), self.assertRaises(SettingsError) as raised:
            config.validate(load())
        self.assertIn("github_actions", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
