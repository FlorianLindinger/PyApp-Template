"""Prepare a launcher release: check, bump the version, finish the changelog and build the zip.

    release.bat                     only check whether a release is possible
    release.bat patch               also: 1.2.3 -> 1.2.4 (minor, major, or an exact version)
    release.bat 1.0.0 --allow-dirty release although there are uncommitted changes

The notes come from the "## unreleased" section of CHANGELOG.md, which becomes "## <version> - <date>";
a new empty section is added above it. The zip holds the files of DONT_CHANGE that Git tracks, in a
top-level DONT_CHANGE folder, and is written to DONT_CHANGE/pyapp_tools/zip_releases (Git keeps only its
.gitkeep, so the zips stay on this PC). Nothing is committed or tagged: review the result, then commit it.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import _ui
from _paths import DONT_CHANGE_DIR, PROJECT_ROOT

SETTINGS_PATH = DONT_CHANGE_DIR / "backend_settings.py"
CHANGELOG_PATH = DONT_CHANGE_DIR / "CHANGELOG.md"
RUNNER = DONT_CHANGE_DIR / "tests" / "run_regressions.py"
LAUNCHER_FOLDER = "code/pyapp/DONT_CHANGE/"
# Inside the launcher, but ignored by Git (DONT_CHANGE/.gitignore), so a zip never contains older zips.
RELEASES_FOLDER = "pyapp_tools/zip_releases"
VERSION_LINE = re.compile(r'^LAUNCHER_VERSION = "(\d+\.\d+\.\d+)"', flags=re.MULTILINE)
# "## unreleased", or "## 1.2.3 - unreleased" while LAUNCHER_VERSION already names that coming version.
UNRELEASED = re.compile(r"^## (?:(\d+\.\d+\.\d+) - )?unreleased[ \t]*$", flags=re.MULTILINE | re.IGNORECASE)
RELEASED = re.compile(r"^## (\d+\.\d+\.\d+) - (?!unreleased)", flags=re.MULTILINE | re.IGNORECASE)
NEXT_HEADING = re.compile(r"^## ", flags=re.MULTILINE)
SHOWN_FAILURE_LINES = 40


def as_tuple(version: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def next_version(current: str, request: str) -> str:
    """The version for "patch", "minor", "major" or an exact X.Y.Z."""
    major, minor, patch = as_tuple(current)
    if request == "major":
        return f"{major + 1}.0.0"
    if request == "minor":
        return f"{major}.{minor + 1}.0"
    if request == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if not re.fullmatch(r"\d+\.\d+\.\d+", request):
        raise RuntimeError(f'"{request}" is not patch, minor, major or a version like 1.2.3.')
    return request


def current_version(settings_text: str) -> str:
    match = VERSION_LINE.search(settings_text)
    if not match:
        raise RuntimeError("LAUNCHER_VERSION was not found in backend_settings.py.")
    return match.group(1)


def unreleased_notes(changelog: str) -> str:
    """The text of the unreleased section; a release without notes is refused."""
    match = UNRELEASED.search(changelog)
    if not match:
        raise RuntimeError('CHANGELOG.md has no "## unreleased" section.')
    following = NEXT_HEADING.search(changelog, match.end())
    notes = changelog[match.end() : following.start() if following else len(changelog)].strip()
    if not notes:
        raise RuntimeError('The "## unreleased" section of CHANGELOG.md is empty. Describe the changes first.')
    return notes


def check_version_is_new(current: str, new: str, changelog: str) -> None:
    released = RELEASED.findall(changelog)
    if new in released:
        raise RuntimeError(f"Version {new} was already released according to CHANGELOG.md.")
    if as_tuple(new) < as_tuple(current):
        raise RuntimeError(f"Version {new} is older than the current version {current}.")


def with_released_changelog(changelog: str, version: str, date: str) -> str:
    """Date the unreleased section and start a new, empty one above it."""
    match = UNRELEASED.search(changelog)
    if not match:
        raise RuntimeError('CHANGELOG.md has no "## unreleased" section.')
    return changelog[: match.start()] + f"## unreleased\n\n## {version} - {date}" + changelog[match.end() :]


def with_version(settings_text: str, version: str) -> str:
    return VERSION_LINE.sub(f'LAUNCHER_VERSION = "{version}"', settings_text, count=1)


def read_text(path: Path) -> Tuple[str, bool]:
    raw = path.read_bytes().decode("utf-8")
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def write_text(path: Path, text: str, crlf: bool) -> None:
    path.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def git(*arguments: str) -> str:
    # Fixed Git commands in the project folder.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(PROJECT_ROOT), "-c", "core.quotepath=off", *arguments],  # noqa: S607
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.decode("utf-8", "replace").strip() or "git failed")
    return completed.stdout.decode("utf-8", "replace")


def tracked_launcher_files() -> List[str]:
    return [name for name in git("ls-files", "-z", "--", LAUNCHER_FOLDER).split("\0") if name]


def archive_name(path: str) -> str:
    """Where a tracked file goes in the zip: replacing the folder is how a project updates."""
    return "DONT_CHANGE/" + path[len(LAUNCHER_FOLDER) :]


def build_zip(version: str, files: List[str]) -> Path:
    target = PROJECT_ROOT / LAUNCHER_FOLDER / RELEASES_FOLDER / f"PyApp-Template-launcher-{version}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in files:
                source = PROJECT_ROOT / name
                if source.is_file():
                    archive.write(source, archive_name(name))
        with zipfile.ZipFile(temporary) as archive:
            damaged = archive.testzip()
            if damaged:
                raise RuntimeError(f"The zip is damaged at {damaged}.")
            settings = archive.read("DONT_CHANGE/backend_settings.py").decode("utf-8")
        if current_version(settings) != version:
            raise RuntimeError("The zip does not contain the new version.")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)  # a failed attempt leaves no half-written zip
    return target


def tests_pass() -> bool:
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("PYAPP_")}
    # This Python runs this checkout's fixed test runner.
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-B", "-X", "utf8", str(RUNNER), "-q"],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        for line in completed.stdout.decode("utf-8", "replace").splitlines()[-SHOWN_FAILURE_LINES:]:
            _ui.info(line)
    return completed.returncode == 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", nargs="?", help="patch, minor, major or an exact version; empty = only check")
    parser.add_argument("--allow-dirty", action="store_true", help="allow uncommitted changes")
    parser.add_argument("--skip-tests", action="store_true", help="do not run the launcher tests")
    arguments = parser.parse_args(argv)

    settings_text, settings_crlf = read_text(SETTINGS_PATH)
    changelog, changelog_crlf = read_text(CHANGELOG_PATH)
    current = current_version(settings_text)
    new = next_version(current, arguments.version) if arguments.version else None
    uncommitted = [line for line in git("status", "--porcelain").splitlines() if line.strip()]

    _ui.heading("Launcher release")
    _ui.fields(
        [
            ("Current version", current),
            ("New version", new or "(only checking)"),
            ("Uncommitted files", len(uncommitted)),
        ]
    )
    notes = unreleased_notes(changelog)
    _ui.fields([("Changelog notes", f"{len(notes.splitlines())} lines")])
    if new:
        check_version_is_new(current, new, changelog)
    if uncommitted and not arguments.allow_dirty:
        _ui.error("Commit your changes first, or use --allow-dirty. The zip should match a commit.")
        return 1
    if not arguments.skip_tests:
        _ui.step("Running the launcher tests ...")
        if not tests_pass():
            _ui.error("The launcher tests failed, so nothing was changed.")
            return 1
    if not new:
        _ui.success("A release is possible. Run this again with patch, minor, major or a version.")
        return 0

    # The zip is built from the edited files, so they are written first and put back if anything
    # fails: a retry then makes the same release instead of skipping a version.
    originals = {path: path.read_bytes() for path in (SETTINGS_PATH, CHANGELOG_PATH)}
    try:
        write_text(SETTINGS_PATH, with_version(settings_text, new), settings_crlf)
        today = datetime.date.today().isoformat()
        write_text(CHANGELOG_PATH, with_released_changelog(changelog, new, today), changelog_crlf)
        _ui.step("Building the zip ...")
        target = build_zip(new, tracked_launcher_files())
    except BaseException:
        for path, data in originals.items():
            path.write_bytes(data)
        _ui.error(f"The release failed; {SETTINGS_PATH.name} and {CHANGELOG_PATH.name} are unchanged.")
        raise
    _ui.fields([("Zip", target), ("Size", f"{target.stat().st_size / 1_048_576:.1f} MB")])
    _ui.blank_line()
    _ui.success(f"Launcher {new} is ready. Review the changes, then commit them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
