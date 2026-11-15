"""Public app environment: resolved paths and titles, disabled values, and no filesystem side effects."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import project_location
from pyapp.DONT_CHANGE.runtime import bg_watchdog as watchdog


class AppEnvironmentTests(unittest.TestCase):
    def settings(self, **changes: object) -> SimpleNamespace:
        return SimpleNamespace(
            **{
                "program_name": "Example {app}",
                "environment_for_main_py": {"CUSTOM": "kept", "PROGRAM_NAME": "overridden"},
                "user_settings_path": "../settings.py",
                "enable_crash_log": True,
                "crash_log_path": "crashes/report.txt",
                "crash_log_path_is_relative_to_start_folder_if_relative": True,
                "start_in_shortcut_folder": False,
                "close_after_failure": False,
                "close_after_success": True,
                **changes,
            }
        )

    def test_paths_and_titles_are_resolved_without_creating_folders(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"PYAPP_START_DIR": folder}):
            log = Path(folder, "logs", "current.log")
            with mock.patch.object(watchdog, "clean_python_environment", return_value={}):
                env = watchdog.app_environment(self.settings(), True, str(log), "app-id")
            self.assertEqual(env["USER_SETTINGS_PATH"], str(project_location.CODE / "settings.py"))
            self.assertEqual(env["PROJECT_DIR"], str(project_location.PROJECT_ROOT))
            self.assertEqual(env["START_DIR"], folder)
            self.assertEqual(env["LOG_DIR"], str(log.parent))
            self.assertEqual(env["LOG_PATH"], str(log))
            self.assertEqual(env["CRASH_LOG_DIR"], str(Path(folder, "crashes")))
            self.assertEqual(env["TITLE_AFTER_SUCCESS"], "[Finished] Example {app}")
            self.assertEqual(env["TITLE_AFTER_FAILURE"], "[Failure] Example {app}")
            self.assertEqual(list(Path(folder).iterdir()), [])
            for name in ("SUCCESS", "FAILURE", "SETTINGS", "LOG", "CRASH_LOG", "OPEN_CODE"):
                self.assertEqual(env[name + "_ICON_PATH"], getattr(watchdog.paths, name + "_ICON_PATH"))
            self.assertNotIn("LAUNCHER_VERSION", env)
            self.assertEqual(env["CUSTOM"], "kept")
            self.assertEqual(env["PROGRAM_NAME"], "Example {app}")
            self.assertEqual(env["APP_ID"], "app-id")

    def test_disabled_paths_are_empty_and_existing_flags_are_preserved(self):
        with mock.patch.object(watchdog, "clean_python_environment", return_value={}):
            env = watchdog.app_environment(self.settings(user_settings_path="", enable_crash_log=False), False, "", "")
        for name in ("USER_SETTINGS_PATH", "LOG_PATH", "LOG_DIR", "CRASH_LOG_DIR"):
            self.assertEqual(env[name], "")
        self.assertEqual(env["PROGRAM_HAS_TERMINAL"], "0")
        self.assertEqual(env["WDIR_IS_SCRIPT_DIR"], "1")
        self.assertEqual(env["CLOSE_AFTER_FAILURE"], "0")
        self.assertEqual(env["CLOSE_AFTER_SUCCESS"], "1")

    def test_crash_logs_relative_to_settings_and_absolute_user_settings(self):
        configured = str(project_location.PROJECT_ROOT / "other" / "settings.py")
        with mock.patch.object(watchdog, "clean_python_environment", return_value={}):
            env = watchdog.app_environment(
                self.settings(
                    user_settings_path=configured, crash_log_path_is_relative_to_start_folder_if_relative=False
                ),
                True,
                "",
                "",
            )
        self.assertEqual(env["USER_SETTINGS_PATH"], configured)
        self.assertEqual(env["CRASH_LOG_DIR"], str(Path(watchdog.paths.DEV_SETTINGS_DIR, "crashes")))

    def test_start_dir_fallback_uses_cwd_and_internal_environment_is_removed(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            watchdog, "clean_python_environment", return_value={"PYAPP_RUN_DIR": "internal", "OTHER": "kept"}
        ):
            env = watchdog.app_environment(self.settings(start_in_shortcut_folder=True), True, "", "")
        self.assertEqual(env["START_DIR"], str(Path.cwd()))
        self.assertEqual(env["WDIR_IS_SCRIPT_DIR"], "0")
        self.assertNotIn("PYAPP_RUN_DIR", env)
        self.assertEqual(env["OTHER"], "kept")


if __name__ == "__main__":
    unittest.main()
