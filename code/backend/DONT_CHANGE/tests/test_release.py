"""tools/release: version numbers, the changelog and the zip."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "scripts" / "tools"), *sys.path]):
    import release

CHANGELOG = "# Log\n\n## unreleased\n\n- A change.\n\n## 1.2.3 - 2026-01-01\n\n- Old.\n"


class VersionTests(unittest.TestCase):
    def test_bumps(self):
        self.assertEqual(release.next_version("1.2.3", "patch"), "1.2.4")
        self.assertEqual(release.next_version("1.2.3", "minor"), "1.3.0")
        self.assertEqual(release.next_version("1.2.3", "major"), "2.0.0")
        self.assertEqual(release.next_version("1.2.3", "4.5.6"), "4.5.6")

    def test_nonsense_is_refused(self):
        with self.assertRaises(RuntimeError):
            release.next_version("1.2.3", "1.2")

    def test_old_or_repeated_versions_are_refused(self):
        with self.assertRaises(RuntimeError):
            release.check_version_is_new("1.2.3", "1.2.2", CHANGELOG)
        with self.assertRaises(RuntimeError):
            release.check_version_is_new("1.2.3", "1.2.3", CHANGELOG)
        release.check_version_is_new("1.2.3", "1.2.4", CHANGELOG)

    def test_only_the_version_line_changes(self):
        text = 'A = "1"\nLAUNCHER_VERSION = "1.2.3"\nB = "1.2.3"\n'
        self.assertEqual(release.with_version(text, "2.0.0"), 'A = "1"\nLAUNCHER_VERSION = "2.0.0"\nB = "1.2.3"\n')


class ChangelogTests(unittest.TestCase):
    def test_notes_are_required(self):
        self.assertEqual(release.unreleased_notes(CHANGELOG), "- A change.")
        with self.assertRaises(RuntimeError):
            release.unreleased_notes("## unreleased\n\n## 1.2.3 - 2026-01-01\n")
        with self.assertRaises(RuntimeError):
            release.unreleased_notes("## 1.2.3 - 2026-01-01\n")

    def test_subheadings_belong_to_the_notes(self):
        self.assertIn("Fixes", release.unreleased_notes("## unreleased\n\n### Fixes\n\n- x\n"))

    def test_the_section_gets_its_version_and_a_new_one_starts(self):
        result = release.with_released_changelog(CHANGELOG, "1.2.4", "2026-02-02")
        self.assertTrue(result.startswith("# Log\n\n## unreleased\n\n## 1.2.4 - 2026-02-02\n\n- A change.\n"))
        with self.assertRaises(RuntimeError):
            release.unreleased_notes(result)

    def test_the_older_heading_form_works(self):
        text = "## 0.0.1 - unreleased\n\n- x\n"
        self.assertEqual(release.unreleased_notes(text), "- x")
        self.assertIn("## 0.0.2 - 2026-02-02", release.with_released_changelog(text, "0.0.2", "2026-02-02"))


class ZipTests(unittest.TestCase):
    def test_zip_has_a_top_level_folder_and_the_new_version(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            launcher = root / release.LAUNCHER_FOLDER
            launcher.mkdir(parents=True)
            (launcher / "backend_settings.py").write_text('LAUNCHER_VERSION = "1.2.4"\n', encoding="utf-8")
            files = [release.LAUNCHER_FOLDER + "backend_settings.py", release.LAUNCHER_FOLDER + "gone.py"]
            with mock.patch.object(release, "PROJECT_ROOT", root):
                target = release.build_zip("1.2.4", files)
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(archive.namelist(), ["DONT_CHANGE/backend_settings.py"])

    def test_a_wrong_version_in_the_zip_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            launcher = root / release.LAUNCHER_FOLDER
            launcher.mkdir(parents=True)
            (launcher / "backend_settings.py").write_text('LAUNCHER_VERSION = "1.2.3"\n', encoding="utf-8")
            with mock.patch.object(release, "PROJECT_ROOT", root), self.assertRaises(RuntimeError):
                release.build_zip("1.2.4", [release.LAUNCHER_FOLDER + "backend_settings.py"])


if __name__ == "__main__":
    unittest.main()
