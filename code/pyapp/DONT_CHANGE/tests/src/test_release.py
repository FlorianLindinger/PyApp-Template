"""tools/release: version numbers, the changelog and the zip."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "pyapp_tools" / "src"), *sys.path]):
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

    def test_an_unreleased_section_can_already_name_its_version(self):
        text = "## 0.0.1 - unreleased\n\n- x\n"
        self.assertEqual(release.unreleased_notes(text), "- x")
        self.assertIn("## 0.0.2 - 2026-02-02", release.with_released_changelog(text, "0.0.2", "2026-02-02"))


class ZipTests(unittest.TestCase):
    def test_zip_has_a_top_level_folder_and_the_new_version(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            launcher = root / release.LAUNCHER_FOLDER
            launcher.mkdir(parents=True)
            (launcher / "pyapp_settings.py").write_text('LAUNCHER_VERSION = "1.2.4"\n', encoding="utf-8")
            files = [release.LAUNCHER_FOLDER + "pyapp_settings.py", release.LAUNCHER_FOLDER + "gone.py"]
            with mock.patch.object(release, "PROJECT_ROOT", root):
                target = release.build_zip("1.2.4", files)
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(archive.namelist(), ["DONT_CHANGE/pyapp_settings.py"])


class FailedReleaseTests(unittest.TestCase):
    def release_in(self, folder: str, build_zip: mock.Mock) -> Path:
        """release.main(["patch"]) on fake files in folder; returns the protected baseline path."""
        settings, changelog = Path(folder) / "pyapp_settings.py", Path(folder) / "CHANGELOG.md"
        settings.write_bytes(b'LAUNCHER_VERSION = "1.2.3"\r\nPROTECTED = {"PROTECTED_PATHS": ["run.bat"]}\r\n')
        changelog.write_bytes(CHANGELOG.replace("\n", "\r\n").encode("utf-8"))
        baseline = Path(folder) / "protected_baseline.json"
        with mock.patch.multiple(
            release,
            SETTINGS_PATH=settings,
            CHANGELOG_PATH=changelog,
            BASELINE_PATH=baseline,
            git=mock.Mock(return_value=""),
            tracked_launcher_files=mock.Mock(return_value=[]),
            build_zip=build_zip,
        ), mock.patch("builtins.print"):
            release.main(["patch", "--skip-tests"])
        return baseline

    def test_a_failed_zip_leaves_version_changelog_and_protected_lists_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            files = (Path(folder) / "pyapp_settings.py", Path(folder) / "CHANGELOG.md")
            with self.assertRaises(OSError):
                self.release_in(folder, mock.Mock(side_effect=OSError("disk full")))
            self.assertIn(b'"1.2.3"', files[0].read_bytes())
            self.assertIn(b"## unreleased", files[1].read_bytes())
            self.assertFalse((Path(folder) / "protected_baseline.json").exists())

    def test_a_release_saves_what_is_protected_with_its_version(self):
        import json

        with tempfile.TemporaryDirectory() as folder:
            zip_path = Path(folder) / "release.zip"
            zip_path.write_bytes(b"")
            baseline = self.release_in(folder, mock.Mock(return_value=zip_path))
            data = json.loads(baseline.read_text(encoding="utf-8"))
        self.assertEqual((data["launcher_version"], data["PROTECTED_PATHS"]), ("1.2.4", ["run.bat"]))

    def test_the_slow_checks_run_unless_quick(self):
        with mock.patch.object(release, "slow_checks_pass", return_value=False) as slow, mock.patch.object(
            release, "tests_pass", return_value=True
        ), mock.patch.object(release, "git", return_value=""), mock.patch("builtins.print"):
            self.assertEqual(release.main([]), 1)  # a failed slow check stops the release
            slow.assert_called_once()
            self.assertEqual(release.main(["--quick"]), 0)
            slow.assert_called_once()

    def test_a_wrong_version_in_the_zip_is_refused_without_leaving_a_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            launcher = root / release.LAUNCHER_FOLDER
            launcher.mkdir(parents=True)
            (launcher / "pyapp_settings.py").write_text('LAUNCHER_VERSION = "1.2.3"\n', encoding="utf-8")
            with mock.patch.object(release, "PROJECT_ROOT", root), self.assertRaises(RuntimeError):
                release.build_zip("1.2.4", [release.LAUNCHER_FOLDER + "pyapp_settings.py"])
            self.assertEqual(list((root / release.LAUNCHER_FOLDER / release.RELEASES_FOLDER).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
