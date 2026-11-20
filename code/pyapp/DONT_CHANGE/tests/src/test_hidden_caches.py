"""scripts/hidden_caches.py and pyapp_tools/src/_git.py: small helpers with Windows and Git edge cases."""

from __future__ import annotations

import ctypes
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import support  # noqa: F401 - makes the template importable
from project_location import DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE.scripts import hidden_caches

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "pyapp_tools" / "src"), *sys.path]):
    import _git


def _is_hidden(path: Path) -> bool:
    return bool(ctypes.windll.kernel32.GetFileAttributesW(str(path)) & hidden_caches.FILE_ATTRIBUTE_HIDDEN)


@unittest.skipUnless(os.name == "nt", "Windows file attributes")
class HiddenCachesTests(unittest.TestCase):
    def test_cache_folders_in_the_known_places_are_hidden_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cache = root / "__pycache__"
            ruff = root / "tests" / ".ruff_cache"
            deeper = root / "package" / "__pycache__"
            normal = root / "data"
            for path in (cache, ruff, deeper, normal):
                path.mkdir(parents=True)
            with mock.patch.object(hidden_caches, "_parents", return_value=[str(root), str(root / "tests")]):
                hidden_caches.hide_cache_folders()
                hidden_caches.hide_cache_folders()  # already hidden: stays hidden, no error
            self.assertTrue(_is_hidden(cache))
            self.assertTrue(_is_hidden(ruff))
            self.assertFalse(_is_hidden(deeper), "only the listed folders are checked, without a walk")
            self.assertFalse(_is_hidden(normal))

    def test_missing_folders_and_failures_never_raise(self):
        with mock.patch.object(hidden_caches, "_parents", return_value=["Z:\\does\\not\\exist"]):
            hidden_caches.hide_cache_folders()
        with mock.patch.object(hidden_caches, "_parents", side_effect=OSError("boom")), mock.patch.object(
            hidden_caches, "note_ignored"
        ) as noted:
            hidden_caches.hide_cache_folders()
        noted.assert_called_once()


class GitMessageTests(unittest.TestCase):
    def test_message_names_the_command_and_gives_a_hint_for_known_causes(self):
        message = _git.explain(
            ["log", "-1"],
            128,
            b"fatal: detected dubious ownership in repository at 'D:/x'\n\tgit config --global --add safe.directory D:/x\n",
        )
        self.assertIn('"git log -1" failed with exit code 128', message)
        self.assertIn("safe.directory D:/x", message)
        self.assertIn("Hint: Git does not trust this folder", message)

    def test_unknown_errors_keep_gits_text_without_a_guess(self):
        message = _git.explain(["push"], 1, "remote: something unusual\n")
        self.assertIn("remote: something unusual", message)
        self.assertNotIn("Hint:", message)
        self.assertIn("(no error output)", _git.explain(["status"], 2, b""))

    def test_a_missing_git_is_named(self):
        missing = FileNotFoundError(2, "not found")
        with mock.patch.object(_git.subprocess, "run", side_effect=missing), self.assertRaises(RuntimeError) as raised:
            _git.run(["git", "status"])
        self.assertIn("Git was not found", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
