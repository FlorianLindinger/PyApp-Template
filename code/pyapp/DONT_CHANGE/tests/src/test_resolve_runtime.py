"""bootstrap/resolve_runtime.py: settings, version rules, and messages for company PCs."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Tuple
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "bootstrap"), *sys.path]):
    import resolve_runtime as tool

# isort: split

from pyapp.DONT_CHANGE.scripts.env import uv
from pyapp.DONT_CHANGE.scripts.standalone import python_request


class SettingsTests(unittest.TestCase):
    def test_plain_literals_are_read_and_the_last_one_wins(self):
        text = 'uv_cache = "global"\nuv_cache = "local"  # note\nflag: bool = True\nnothing = None\n'
        self.assertEqual(tool.read_settings(text), {"uv_cache": "local", "flag": True, "nothing": None})

    def test_expressions_count_as_missing(self):
        self.assertEqual(tool.read_settings('uv_cache = "a"\nuv_cache = "a" + "b"\nname = f(1)\n'), {"uv_cache": "a"})

    def test_empty_text_values_stay_empty(self):
        self.assertEqual(tool.read_settings('python_version = ""  # newest\n'), {"python_version": ""})

    def test_indented_lines_are_ignored(self):
        self.assertEqual(tool.read_settings('    uv_cache = "local"\n'), {})


class VersionTests(unittest.TestCase):
    def test_rules(self):
        for version, spec, expected in (
            ("0.11.32", "", True),
            ("0.11.32", "0.11.32", True),
            ("0.11.32", "==0.11.31", False),
            ("0.11.0", "0.11", True),
            ("0.11.32", ">=0.9,<1", True),
            ("1.2.0", ">=0.9,<1", False),
            ("0.11.32", "~=0.11", True),
            ("1.0.0", "~=0.11", False),
            ("0.11.32", "!=0.11.32", False),
        ):
            with self.subTest(version=version, spec=spec):
                self.assertEqual(tool.version_satisfies(version, spec), expected)

    def test_a_clause_that_makes_no_sense_is_reported(self):
        with self.assertRaises(tool.BootstrapError):
            tool.version_satisfies("1.0.0", "about 1")
        # Empty version parts: a message, not "invalid literal for int()".
        for spec in (">=0..9", "1.", ".5"):
            with self.subTest(spec=spec), self.assertRaises(tool.BootstrapError):
                tool.version_satisfies("1.0.0", spec)

    def test_exact_versions(self):
        self.assertEqual(tool.exact_version("0.11.32"), "0.11.32")
        self.assertEqual(tool.exact_version("==0.11.32"), "0.11.32")
        self.assertIsNone(tool.exact_version(">=0.11.32"))
        self.assertIsNone(tool.exact_version(""))


class FetchUvTests(unittest.TestCase):
    def test_range_downloads_the_selected_release_and_verifies_its_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder)
            archive = stage / "source.zip"
            with zipfile.ZipFile(archive, "w") as stream:
                stream.writestr("uv.exe", b"uv")
            content = archive.read_bytes()
            urls: List[str] = []

            def download(url: str, target: Path) -> None:
                urls.append(url)
                target.write_bytes(hashlib.sha256(content).hexdigest().encode() if url.endswith(".sha256") else content)

            with mock.patch.object(tool, "own_bootstrap_folder", return_value=None), mock.patch.object(
                tool, "matching_uv_release", return_value="0.9.9"
            ) as select, mock.patch.object(
                tool, "uv_release_target", return_value="x86_64-pc-windows-msvc"
            ), mock.patch.object(tool, "download", side_effect=download):
                extracted = tool.fetch_uv_folder(">=0.9,<0.10", stage)
            select.assert_called_once_with(">=0.9,<0.10", "uv-x86_64-pc-windows-msvc.zip", stage)
            self.assertEqual((extracted / "uv.exe").read_bytes(), b"uv")
            self.assertTrue(all("/download/0.9.9/" in url for url in urls))

    def test_exact_and_unrestricted_downloads_do_not_list_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            for spec, url_part in (("==0.9.9", "/download/0.9.9/"), ("", "/latest/download/")):
                with self.subTest(spec=spec), mock.patch.object(
                    tool, "own_bootstrap_folder", return_value=None
                ), mock.patch.object(tool, "matching_uv_release") as select, mock.patch.object(
                    tool, "download", side_effect=tool.BootstrapError("stop before network")
                ) as fetch:
                    with self.assertRaises(tool.BootstrapError):
                        tool.fetch_uv_folder(spec, Path(folder))
                    self.assertIn(url_part, fetch.call_args[0][0])
                    select.assert_not_called()

    def test_no_matching_release_keeps_the_installed_uv_and_cleans_staging(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder, "uv")
            destination.mkdir()
            (destination / "uv.exe").write_bytes(b"previous")
            with mock.patch.object(tool, "own_bootstrap_folder", return_value=None), mock.patch.object(
                tool, "matching_uv_release", side_effect=tool.BootstrapError("no matching release")
            ), self.assertRaises(tool.BootstrapError):
                tool.install_uv("<0.1", destination)
            self.assertEqual((destination / "uv.exe").read_bytes(), b"previous")
            self.assertEqual(list(Path(folder).iterdir()), [destination])

    def test_the_bootstrap_uv_is_taken_without_its_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            boot = Path(folder, "uv-bootstrap-1234")
            boot.mkdir()
            for name in ("uv.exe", "uvx.exe", "uv-x86_64-pc-windows-msvc.zip", "uv-x86_64-pc-windows-msvc.zip.sha256"):
                Path(boot, name).write_bytes(b"x")
            stage = Path(folder, "stage")
            stage.mkdir()
            with mock.patch.object(tool, "BOOTSTRAP_UV_PARENT", Path(folder)), mock.patch.object(
                tool, "uv_version_of", return_value="0.11.32"
            ), mock.patch.dict(os.environ, {"PYAPP_BOOT_UV": str(boot / "uv.exe")}):
                extracted = tool.fetch_uv_folder("", stage)
            self.assertEqual(sorted(p.name for p in extracted.iterdir()), ["uv.exe", "uvx.exe"])


class MatchingUvReleaseTests(unittest.TestCase):
    archive = "uv-x86_64-pc-windows-msvc.zip"

    def release(self, tag: str, **changes: object) -> Dict[str, object]:
        return {
            "tag_name": tag,
            "draft": False,
            "prerelease": False,
            "assets": [{"name": self.archive}, {"name": self.archive + ".sha256"}],
            **changes,
        }

    def select(self, spec: str, pages: List[List[Dict[str, object]]]) -> Tuple[str, List[str]]:
        urls: List[str] = []

        def download(url: str, target: Path) -> None:
            urls.append(url)
            target.write_text(json.dumps(pages[len(urls) - 1]), encoding="utf-8")

        with tempfile.TemporaryDirectory() as folder, mock.patch.object(tool, "download", side_effect=download):
            return tool.matching_uv_release(spec, self.archive, Path(folder)), urls

    def test_highest_matching_version_is_selected_numerically_not_by_api_order(self):
        selected, _ = self.select(
            ">=0.9,<0.10", [[self.release(tag) for tag in ("0.10.0", "0.9.2", "0.9.12", "0.9.9")]]
        )
        self.assertEqual(selected, "0.9.12")

    def test_compatible_and_excluded_versions(self):
        selected, _ = self.select("~=0.9.0,!=0.9.12", [[self.release(tag) for tag in ("0.10.0", "0.9.12", "0.9.9")]])
        self.assertEqual(selected, "0.9.9")

    def test_older_pages_are_checked_even_after_a_match(self):
        selected, urls = self.select("<0.10", [[self.release("0.9.2")] * 100, [self.release("0.9.12")]])
        self.assertEqual(selected, "0.9.12")
        self.assertTrue(urls[0].endswith("per_page=100&page=1"))
        self.assertTrue(urls[1].endswith("per_page=100&page=2"))

    def test_nonstable_or_incomplete_releases_are_skipped(self):
        releases = [
            self.release("0.9.20", draft=True),
            self.release("0.9.19", prerelease=True),
            self.release("0.9.18rc1"),
            self.release("0.9.17", assets=[]),
            self.release("0.9.16", assets=[{"name": self.archive}]),
            self.release("0.9.15"),
        ]
        selected, _ = self.select("<0.10", [releases])
        self.assertEqual(selected, "0.9.15")

    def test_no_match_has_an_actionable_error(self):
        with self.assertRaisesRegex(tool.BootstrapError, "No stable uv release satisfies uv_version '<0.1'"):
            self.select("<0.1", [[self.release("0.9.9")]])

    def test_invalid_metadata_has_a_bootstrap_error(self):
        for payload in ('{"message":"rate limited"}', "invalid json"):

            def download(_url: str, target: Path, content: str = payload) -> None:
                target.write_text(content, encoding="utf-8")

            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as folder, mock.patch.object(
                tool, "download", side_effect=download
            ), self.assertRaises(tool.BootstrapError):
                tool.matching_uv_release("<1", self.archive, Path(folder))


class UserPathTests(unittest.TestCase):
    def test_the_same_folder_in_other_spelling_is_not_added_again(self):
        stored = {"value": "%USERPROFILE%\\.local\\bin\\;C:\\Tools", "type": 1}  # REG_SZ
        key = mock.MagicMock()
        fake = mock.MagicMock(KEY_READ=1, KEY_SET_VALUE=2, HKEY_CURRENT_USER=3, REG_EXPAND_SZ=2)
        fake.CreateKeyEx.return_value.__enter__.return_value = key

        def query_value(*_arguments: object) -> Tuple[object, object]:
            return stored["value"], stored["type"]

        fake.QueryValueEx.side_effect = query_value

        def set_value(_key: object, _name: str, _reserved: int, kind: int, value: str) -> None:
            stored.update(value=value, type=kind)

        fake.SetValueEx.side_effect = set_value
        profile = os.environ.get("USERPROFILE", "C:\\Users\\user")
        with mock.patch.object(tool, "winreg", fake):
            tool.add_to_user_path(Path(profile.upper()) / ".local" / "bin")
            fake.SetValueEx.assert_not_called()
            tool.add_to_user_path(Path("C:\\New"))
        self.assertEqual(stored, {"value": "%USERPROFILE%\\.local\\bin\\;C:\\Tools;C:\\New", "type": 1})


class UnusableGlobalUvTests(unittest.TestCase):
    def test_a_global_uv_that_does_not_start_is_not_called_outdated(self):
        settings: Dict[str, object] = {"uv_install_if_missing": "never"}
        with mock.patch.object(tool, "find_global_uv", return_value=Path("C:\\uv.exe")), mock.patch.object(
            tool, "uv_version_of", return_value=None
        ), mock.patch.object(tool, "_start_problems", ["uv.exe was blocked by a policy."]), mock.patch.object(
            tool, "LOCAL_UV_EXE", Path("C:\\missing\\uv.exe")
        ), self.assertRaises(tool.BootstrapError) as raised:
            tool.resolve_uv(settings)
        message = str(raised.exception)
        for key in ("uv.exe", "blocked"):
            self.assertIn(key, message)
        self.assertNotIn("None", message)


class ConcurrentFirstStartTests(unittest.TestCase):
    """Two first starts at the same time (two projects, or one started twice) share no folder."""

    def test_only_a_download_folder_of_this_run_counts_as_its_own(self):
        parent = Path("C:\\Users\\user\\AppData\\Local\\PyApp-Template")
        with mock.patch.object(tool, "BOOTSTRAP_UV_PARENT", parent):
            for boot_uv, expected in (
                (parent / "uv-bootstrap-123" / "uv.exe", parent / "uv-bootstrap-123"),
                (parent / "uv" / "uv.exe", None),  # the shared uv, never removed
                (Path("C:\\tools\\uv-bootstrap-1\\uv.exe"), None),
                ("", None),
            ):
                with self.subTest(boot_uv=str(boot_uv)), mock.patch.dict(os.environ, {"PYAPP_BOOT_UV": str(boot_uv)}):
                    self.assertEqual(tool.own_bootstrap_folder(), expected)

    def test_a_run_removes_its_own_folder_and_old_leftovers_but_not_another_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            own, other, old = (parent / name for name in ("uv-bootstrap-1", "uv-bootstrap-2", "uv-bootstrap-3"))
            for path in (own, other, old):
                path.mkdir()
                (path / "uv.exe").write_bytes(b"x")
            hours_ago = time.time() - 2 * tool.STALE_BOOTSTRAP_SECONDS
            os.utime(old, (hours_ago, hours_ago))
            with mock.patch.object(tool, "BOOTSTRAP_UV_PARENT", parent), mock.patch.dict(
                os.environ, {"PYAPP_BOOT_UV": str(own / "uv.exe")}
            ):
                tool.remove_bootstrap_folders()
            self.assertEqual(sorted(p.name for p in parent.iterdir()), ["uv-bootstrap-2"])

    def test_the_shared_lock_is_exclusive_across_processes(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder, "uv.lock")
            holder = "import sys, time; sys.path.insert(0, sys.argv[1]); import resolve_runtime as r\n"
            holder += "from pathlib import Path\nwith r.file_lock(Path(sys.argv[2]), 'busy'):\n"
            holder += "    print('locked', flush=True); time.sleep(3)\n"
            # Test subprocesses execute fixed fixture/helper code using the local interpreter or Git.
            process = subprocess.Popen(  # noqa: S603
                [sys.executable, "-I", "-c", holder, str(DONT_CHANGE / "bootstrap"), str(lock)],
                stdout=subprocess.PIPE,
                text=True,
            )
            try:
                self.assertEqual(process.stdout.readline().strip() if process.stdout else "", "locked")
                started = time.monotonic()
                with tool.file_lock(lock, "busy"):
                    waited = time.monotonic() - started
            finally:
                process.wait(timeout=30)
                if process.stdout:
                    process.stdout.close()
            self.assertGreater(waited, 1.5, "the second start did not wait for the first one")

    def test_a_global_uv_installed_meanwhile_is_used_instead_of_copied_over(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            tool, "SHARED_UV_LOCK", Path(folder, "uv.lock")
        ), mock.patch.object(tool, "find_global_uv", return_value=Path("C:\\bin\\uv.exe")), mock.patch.object(
            tool, "uv_version_of", return_value="0.11.32"
        ), mock.patch.object(tool, "_install_global_uv") as install:
            self.assertEqual(tool.install_global_uv(""), Path("C:\\bin\\uv.exe"))
        install.assert_not_called()


class CompanyPcTests(unittest.TestCase):
    def test_a_refused_program_is_explained(self):
        error = OSError()
        error.winerror = 1260  # blocked by group policy
        message = tool.explain_start_failure("uv.exe", error)
        self.assertIn("company policy", message)
        self.assertIn('python_source = "system"', message)

    def test_other_start_failures_are_not_blamed_on_a_policy(self):
        self.assertNotIn("policy", tool.explain_start_failure("uv.exe", OSError("broken")))

    def test_a_program_that_cannot_start_is_remembered(self):
        error = OSError()
        error.winerror = 1260
        problems: List[str] = []
        with mock.patch.object(tool.subprocess, "run", side_effect=error), mock.patch.object(
            tool, "_start_problems", problems
        ):
            self.assertIsNone(tool.uv_version_of("uv.exe"))
            self.assertIn("company policy", tool._start_problems[0])

    def test_system_python_downloads_nothing(self):
        with mock.patch.dict(os.environ, {"UV_MANAGED_PYTHON": "1"}):
            tool.set_uv_environment({}, "system")
            self.assertEqual(os.environ["UV_PYTHON_PREFERENCE"], "only-system")
            self.assertEqual(os.environ["UV_PYTHON_DOWNLOADS"], "never")
            self.assertNotIn("UV_MANAGED_PYTHON", os.environ)

    def test_no_dialog_when_the_window_is_visible(self):
        with mock.patch.dict(os.environ, {"PYAPP_ENTRYPOINT_NO_PAUSE": "1"}), mock.patch("ctypes.windll") as windll:
            tool.show_failure_dialog("x")
            windll.user32.MessageBoxW.assert_not_called()

    def test_a_blocked_download_says_what_to_do(self):
        refused = tool.urllib.error.URLError("refused")
        with mock.patch.object(tool.urllib.request, "urlopen", side_effect=refused), self.assertRaises(
            tool.BootstrapError
        ) as raised:
            tool.download("https://github.com/x", DONT_CHANGE / "tmp" / "never-written")
        self.assertIn("firewall", str(raised.exception))
        self.assertIn("make_self_contained", str(raised.exception))


USER_CACHE = r"D:\my-uv-cache"
UV_SETTINGS = {"python_source": "uv_user", "uv_user_python_visible_globally": True, "use_system_certificates": False}
# uv variables a user may have set for all programs.
USER_UV_VARIABLES = {
    "UV_CACHE_DIR": USER_CACHE,
    "UV_OFFLINE": "1",
    "UV_FROZEN": "1",
    "UV_LOCKED": "1",
    "UV_NO_SYNC": "1",
    "UV_PYTHON_DOWNLOADS": "never",
    "UV_INDEX_URL": "https://example.invalid/simple",
}


class UvEnvironmentTests(unittest.TestCase):
    """The bootstrap and the launcher give uv the same environment (audit F14)."""

    def both(self, uv_cache: str) -> Tuple[Dict[str, str], Dict[str, str]]:
        """(the bootstrap's environment, the launcher's) for a user who set USER_UV_VARIABLES."""
        settings: Dict[str, object] = {**UV_SETTINGS, "uv_cache": uv_cache}
        with mock.patch.dict(os.environ, USER_UV_VARIABLES):
            launcher = uv.uv_environment(SimpleNamespace(**settings))
            tool.set_uv_environment(settings, "uv_user")
            bootstrap = dict(os.environ)
        return bootstrap, launcher

    def test_both_remove_the_same_variables(self):
        self.assertEqual(set(tool.OWN_UV_VARIABLES), set(uv._OWN_UV_VARIABLES))

    def test_variables_that_change_what_uv_does_are_removed(self):
        for environment in self.both("global"):
            for name in ("UV_OFFLINE", "UV_FROZEN", "UV_LOCKED", "UV_NO_SYNC"):
                self.assertNotIn(name, environment)
            self.assertEqual(environment["UV_PYTHON_DOWNLOADS"], "automatic")
            self.assertEqual(environment["UV_INDEX_URL"], "https://example.invalid/simple")

    def test_a_users_cache_folder_wins_over_the_global_cache(self):
        for environment in self.both("global"):
            self.assertEqual(environment["UV_CACHE_DIR"], USER_CACHE)
        for environment in self.both("local"):
            self.assertTrue(environment["UV_CACHE_DIR"].endswith("uv-cache"))
            self.assertNotEqual(environment["UV_CACHE_DIR"], USER_CACHE)

    def test_the_batch_stage_clears_the_same_behavior_variables(self):
        text = (DONT_CHANGE / "bootstrap" / "resolve_runtime.bat").read_text(encoding="utf-8")
        for name in ("UV_OFFLINE", "UV_FROZEN", "UV_LOCKED", "UV_NO_SYNC"):
            self.assertIn(f'set "{name}="', text)
        self.assertIn('if not defined visible set "visible=True"', text)


class PythonRequestTests(unittest.TestCase):
    def test_ranges_are_converted_like_the_launcher_does(self):
        for value in (
            "3.12-3.14",
            "3.14-3.12",
            "3.12-3.19.1",
            " 3.19.1 - 3.12 ",
            "3-3.12",
            "3.12",
            ">=3.12",
            "",
            "a-b",
        ):
            with self.subTest(value=value):
                self.assertEqual(tool.range_specifier(value), python_request.range_specifier(value))

    def resolve(self, offered: object, install_codes: List[int]) -> Tuple[List[List[str]], int]:
        """Install a missing Python; returns the install commands and how often a newer uv was fetched."""
        commands: List[List[str]] = []

        def run_live(_uv: object, arguments: List[str]) -> int:
            commands.append(arguments)
            return install_codes[len(commands) - 1]

        newer_uv = mock.Mock(return_value=Path("newer-uv.exe"))

        with mock.patch.multiple(
            tool,
            set_uv_environment=mock.DEFAULT,
            remove_broken_python_links=mock.DEFAULT,
            project_python_request=mock.Mock(return_value="3.12-3.14"),
            find_python=mock.Mock(side_effect=[None, "python.exe"]),
            run_live=run_live,
            python_offered=mock.Mock(return_value=offered),
            install_newer_shared_uv=newer_uv,
            run_captured=mock.Mock(return_value=(0, ["3.13.1"])),
            available_summary=mock.Mock(return_value=""),
        ):
            with contextlib.suppress(tool.BootstrapError):
                tool.resolve_python({}, Path("uv.exe"))
            return commands, newer_uv.call_count

    def test_a_range_is_installed_as_a_specifier(self):
        commands, _ = self.resolve(True, [0])
        self.assertEqual(commands, [["python", "install", ">=3.12,<3.15"]])

    def test_no_newer_uv_when_this_uv_knows_the_python(self):
        self.assertEqual(self.resolve(True, [1])[1], 0)

    def test_a_newer_uv_when_this_one_does_not_know_it_or_cannot_tell(self):
        for offered in (False, None):
            with self.subTest(offered=offered):
                commands, fetched = self.resolve(offered, [1, 0])
                self.assertEqual((len(commands), fetched), (2, 1))


class CacheTests(unittest.TestCase):
    def test_batch_special_characters_are_kept(self):
        text = tool.cache_text("C:\\a%b\\uv.exe", "C:\\p.exe", "s")
        self.assertIn('set "PYAPP_UV=C:\\a%%b\\uv.exe"', text)
        self.assertTrue(text.startswith("rem ascii\r\n"))

    def test_non_ascii_paths_are_marked(self):
        self.assertTrue(tool.cache_text("C:\\Müller\\uv.exe", "p", "s").startswith("rem utf-8"))


# Stands in for resolve_runtime.bat: counts its runs and writes the cache like resolve_runtime.py.
FAKE_RESOLVER_BAT = '@echo off\r\n"%PYAPP_TEST_PYTHON%" "%~dp0fake_resolve.py" "%PYAPP_STAMP%"\r\n'
FAKE_RESOLVER_PY = """
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
with open(root / "resolved.txt", "a") as counter:
    counter.write("x")
fake = str(root / "fake.exe")
stamp = sys.argv[1].replace("%", "%%")
lines = ["rem ascii", f'set "PYAPP_UV={fake}"', f'set "PYAPP_PYTHON={fake}"', f'set "PYAPP_CACHED_STAMP={stamp}"']
(root / "tmp" / "runtime.cmd").write_text("\\n".join(lines) + "\\n", encoding="utf-8")
"""
SETTINGS = '# settings\npython_version = "3.14"\nuv_version: str = ""  # any\nprogram_name = "x"\n'


@unittest.skipUnless(os.name == "nt", "Windows only")
class RuntimeCacheTests(unittest.TestCase):
    """bootstrap/ensure_runtime.bat: when the cached uv and Python can be reused."""

    def project(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        bootstrap = root / "DONT_CHANGE" / "bootstrap"
        bootstrap.mkdir(parents=True)
        shutil.copyfile(DONT_CHANGE / "bootstrap" / "ensure_runtime.bat", bootstrap / "ensure_runtime.bat")
        (bootstrap / "resolve_runtime.bat").write_bytes(FAKE_RESOLVER_BAT.encode("ascii"))
        (bootstrap / "fake_resolve.py").write_text(FAKE_RESOLVER_PY, encoding="utf-8")
        (root / "DONT_CHANGE" / "fake.exe").touch()
        (root / "generated").mkdir()
        (root / "generated" / ".python-version").write_text("3.14\n", encoding="utf-8")
        (root / "developer_settings.py").write_text(SETTINGS, encoding="utf-8")
        return root

    def resolutions(self, root: Path) -> int:
        """Run ensure_runtime.bat; return how often the runtime has been resolved so far."""
        # Fixed test batch file in a temporary folder.
        subprocess.run(  # noqa: S603
            ["cmd.exe", "/d", "/c", str(root / "DONT_CHANGE" / "bootstrap" / "ensure_runtime.bat")],  # noqa: S607
            env={**os.environ, "PYAPP_TEST_PYTHON": sys.executable},
            check=True,
            capture_output=True,
        )
        counter = root / "DONT_CHANGE" / "resolved.txt"
        return len(counter.read_text(encoding="utf-8")) if counter.exists() else 0

    def edit_unnoticeably(self, path: Path, old: str, new: str) -> None:
        """Same size and modification time: what the old time-and-size stamp could not see."""
        modified = path.stat().st_mtime
        path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        os.utime(str(path), (modified, modified))

    def test_unchanged_projects_reuse_the_cache(self):
        root = self.project()
        self.assertEqual(self.resolutions(root), 1)
        self.assertEqual(self.resolutions(root), 1)

    def test_a_same_size_edit_of_a_bootstrap_setting_resolves_again(self):
        root = self.project()
        self.resolutions(root)
        self.edit_unnoticeably(root / "developer_settings.py", '"3.14"', '"3.13"')
        self.assertEqual(self.resolutions(root), 2)
        self.edit_unnoticeably(root / "generated" / ".python-version", "3.14", "3.13")
        self.assertEqual(self.resolutions(root), 3)

    def test_special_characters_in_values_keep_the_cache_working(self):
        root = self.project()
        settings = root / "developer_settings.py"
        settings.write_text(SETTINGS.replace('""  # any', '">=0.9"  # a & b | c "q" 100% <x> ^up'), encoding="utf-8")
        self.assertEqual(self.resolutions(root), 1)
        self.assertEqual(self.resolutions(root), 1)


if __name__ == "__main__":
    unittest.main()
