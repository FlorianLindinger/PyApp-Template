"""scripts/update_check.py: telling the developer about a newer launcher, at most once a day."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional
from unittest import mock

from project_location import DONT_CHANGE  # noqa: F401 - puts the code folder on sys.path

# isort: split

from pyapp.DONT_CHANGE.scripts import update_check

DAY = update_check.CHECK_INTERVAL_SECONDS
NEWER = {"version": "99.0.0", "date": "2026-12-01", "url": "https://example.org/release"}


class UpdateCheckTests(unittest.TestCase):
    def setUp(self):  # pyrefly: ignore[missing-override-decorator]
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patcher = mock.patch.object(update_check, "STATE_PATH", Path(folder.name) / "update_check.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.fetches: List[int] = []

    def fetch(self, answer: Optional[Dict[str, str]]):
        def fetch() -> Optional[Dict[str, str]]:
            self.fetches.append(1)
            return answer

        return fetch

    def test_versions_compare_as_numbers(self):
        self.assertGreater(update_check.version_key("v1.10.0"), update_check.version_key("1.9.3"))
        self.assertEqual(update_check.version_key("not a version"), ())

    def test_off_by_default_means_no_request_at_all(self):
        self.assertIsNone(update_check.available_update(False, now=0, fetch=self.fetch(NEWER)))
        self.assertEqual(self.fetches, [])

    def test_github_is_asked_at_most_once_a_day(self):
        fetch = self.fetch(NEWER)
        self.assertEqual(update_check.available_update(True, now=1000, fetch=fetch), NEWER)
        self.assertEqual(update_check.available_update(True, now=1000 + DAY - 1, fetch=fetch), NEWER)
        self.assertEqual(len(self.fetches), 1, "the remembered answer is used within a day")
        update_check.available_update(True, now=1000 + DAY, fetch=fetch)
        self.assertEqual(len(self.fetches), 2)

    def test_offline_shows_nothing_and_waits_a_day(self):
        self.assertIsNone(update_check.available_update(True, now=1000, fetch=self.fetch(None)))
        self.assertIsNone(update_check.available_update(True, now=2000, fetch=self.fetch(None)))
        self.assertEqual(len(self.fetches), 1, "an offline PC does not wait for the timeout on every start")

    def test_same_or_older_releases_are_not_shown(self):
        with mock.patch.object(update_check.paths, "LAUNCHER_VERSION", "2.0.0"):
            for version in ("2.0.0", "1.9.9"):
                update_check.write_state({})
                found = update_check.available_update(
                    True, now=0, fetch=self.fetch({"version": version, "date": "", "url": ""})
                )
                self.assertIsNone(found, version)

    def test_skip_this_version_and_dont_check_again_are_remembered_outside_the_settings(self):
        update_check.available_update(True, now=0, fetch=self.fetch(NEWER))
        update_check.remember_choice("s", "99.0.0")
        self.assertIsNone(update_check.available_update(True, now=1, fetch=self.fetch(NEWER)))
        newer_still = {**NEWER, "version": "100.0.0"}
        self.assertEqual(update_check.available_update(True, now=DAY + 1, fetch=self.fetch(newer_still)), newer_still)
        update_check.remember_choice("n", "100.0.0")
        requests = len(self.fetches)
        self.assertIsNone(update_check.available_update(True, now=10 * DAY, fetch=self.fetch(NEWER)))
        self.assertEqual(len(self.fetches), requests, "after 'don't check again' GitHub is not contacted")
        self.assertTrue(json.loads(update_check.STATE_PATH.read_text(encoding="utf-8"))["never"])

    def test_the_message_shows_both_versions_and_the_link(self):
        output = io.StringIO()
        with mock.patch.object(update_check, "available_update", return_value=NEWER), mock.patch(
            "sys.stdout", output
        ), mock.patch("pyapp.DONT_CHANGE.scripts.console_tools.ask", return_value="s"):
            update_check.tell_about_update(True)
        text = output.getvalue()
        for key in (update_check.paths.LAUNCHER_VERSION, "99.0.0", "2026-12-01", "https://example.org/release"):
            self.assertIn(key, text)
        self.assertEqual(json.loads(update_check.STATE_PATH.read_text(encoding="utf-8"))["skip_version"], "99.0.0")


if __name__ == "__main__":
    unittest.main()
