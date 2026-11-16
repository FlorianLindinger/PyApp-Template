"""Power, startup, bounded recovery, argument entry points and app compilation tools."""

from __future__ import annotations

import ctypes
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from project_location import DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE.pyapp_tools.src import _ui
from pyapp.DONT_CHANGE.runtime import bg_watchdog
from pyapp.DONT_CHANGE.runtime._pyapp import ExitMode
from pyapp.DONT_CHANGE.scripts import (
    batch_shortcuts,
    config,
    console_tools,
    power,
    runtime_state,
    terminal_window,
    windows_focus,
)
from pyapp.DONT_CHANGE.scripts.dev_tools import compilation


class RuntimeOptions(unittest.TestCase):
    def test_instance_focus_recovers_a_tray_hidden_window(self):
        with mock.patch.object(windows_focus.ctypes, "WinDLL") as dll:
            user = dll.return_value
            user.IsWindow.return_value = True
            user.IsIconic.return_value = False
            user.IsWindowVisible.return_value = False
            self.assertTrue(windows_focus.focus_window(123))
            user.ShowWindow.assert_called_once_with(123, 9)

    def test_color_support_and_explicit_opt_out(self):
        with mock.patch.object(_ui, "_interactive", return_value=False), mock.patch.object(_ui, "_prepare_console"):
            for environment, colored in (
                ({"FORCE_COLOR": "1"}, True),
                ({"GITHUB_ACTIONS": "true"}, True),
                ({"FORCE_COLOR": "0", "GITHUB_ACTIONS": "true"}, False),
                ({"NO_COLOR": "1", "FORCE_COLOR": "1"}, False),
            ):
                with mock.patch.dict(os.environ, environment, clear=True):
                    self.assertEqual("\x1b[" in _ui.styled("result", _ui.GOOD), colored)

    def test_new_options_default_off_and_require_booleans(self):
        s = SimpleNamespace()
        config.fill_missing_settings(s)
        for name in (
            "start_maximized",
            "prevent_sleep",
            "keep_display_awake",
            "generate_batch_shortcuts_for_args_launch",
        ):
            self.assertIs(getattr(s, name), False)
            with mock.patch.object(s, name, "yes"), self.assertRaisesRegex(config.SettingsError, name):
                config.validate(s)

    def test_power_requests_and_release_use_independent_flags(self):
        with mock.patch.object(power.ctypes, "WinDLL") as dll:
            kernel = dll.return_value
            for system, display, bits in ((True, False, 1), (False, True, 2), (True, True, 3), (False, False, 0)):
                power.set_awake(system, display)
                kernel.SetThreadExecutionState.assert_called_with(power.ES_CONTINUOUS | bits)
            kernel.SetThreadExecutionState.return_value = 0
            with self.assertRaises(OSError):
                power.set_awake(True, False)

    def test_foreground_recovers_hidden_non_minimized_windows_without_shrinking_maximized_ones(self):
        with mock.patch.dict(os.environ, {"PYAPP_TERMINAL_WINDOW": "fixture"}), mock.patch(
            "pyapp.DONT_CHANGE.scripts.taskbar_status.terminal_window", return_value=123
        ), mock.patch.object(ctypes, "WinDLL") as dll:
            user = dll.return_value
            user.IsIconic.return_value = False
            user.IsWindowVisible.return_value = False
            console_tools.foreground_terminal()
            user.ShowWindow.assert_called_once_with(123, 9)
            user.SetForegroundWindow.assert_called_once_with(123)
            user.reset_mock()
            user.IsWindowVisible.return_value = True
            console_tools.foreground_terminal()
            user.ShowWindow.assert_not_called()
            user.SetForegroundWindow.assert_called_once_with(123)

    def test_start_maximized_uses_the_owned_window_and_requires_a_dedicated_wt_window(self):
        s = SimpleNamespace(start_maximized=True)
        config.fill_missing_settings(s)
        self.assertTrue(terminal_window.needs_window(s))
        with mock.patch.object(terminal_window.ctypes, "WinDLL") as dll, mock.patch.object(
            terminal_window, "apply_window_settings"
        ), mock.patch("pyapp.DONT_CHANGE.scripts.taskbar_status.remember_window") as remember:
            dll.return_value.GetConsoleWindow.return_value = 123
            terminal_window.configure(s, "conhost")
            remember.assert_called_once_with(123)
            dll.return_value.ShowWindow.assert_called_once_with(123, 3)

    def test_crash_statuses_accept_signed_and_unsigned_but_not_ordinary_exits(self):
        for code in (0xC0000374, 0xC0000135, 0xC0000094, 0xC000008E, 0xC0000090, 0xC0000091, 0xC0000095):
            self.assertTrue(runtime_state.exit_code_looks_like_interpreter_crash(code))
            self.assertTrue(runtime_state.exit_code_looks_like_interpreter_crash(code - 2**32))
        for code in (True, None, 0, 1, -1, 0xC000013A):
            self.assertFalse(runtime_state.exit_code_looks_like_interpreter_crash(code))

    def test_recovery_arguments_and_inherited_recursion_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script = root / "main.py"
            script.write_text("pass\n", encoding="utf-8")
            s = SimpleNamespace(
                after_interpreter_crash_script=str(script), main_script_path=str(script), args_for_main_py=["a"]
            )
            with mock.patch.object(bg_watchdog.subprocess, "Popen") as create, mock.patch.object(
                bg_watchdog.threading, "Thread"
            ):
                result = bg_watchdog.launch_crash_cleanup(
                    s, ExitMode.NO_REPORT, 0xC0000374, [sys.executable], {}, folder, "", root, ["b c", ""]
                )
                self.assertIn("cleanup started", result)
                self.assertEqual(create.call_args.args[0][-4:], ["a", "b c", "", "crashed"])
                self.assertEqual(create.call_args.kwargs["env"]["CRASH_RECOVERY"], "1")
                create.reset_mock()
                result = bg_watchdog.launch_crash_cleanup(
                    s, ExitMode.NO_REPORT, 0xC0000374, [sys.executable], {"CRASH_RECOVERY": "1"}, folder, "", root
                )
                self.assertEqual(result, "")
                create.assert_not_called()

    def test_batch_entry_points_match_enabled_shortcuts_and_preserve_unowned_files(self):
        s = SimpleNamespace(generate_batch_shortcuts_for_args_launch=True)
        config.fill_missing_settings(s)
        s.browser_terminal_shortcut_name = ""
        s.open_settings_shortcut_name = "Äpp % Settings"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            created = batch_shortcuts.sync(s, "app.123", root)
            self.assertEqual(len(created), 7)
            self.assertTrue(all(path.read_text(encoding="utf-8").isascii() for path in created))
            launch = next(p for p in created if p.name == s.program_name + ".cmd")
            text = launch.read_text(encoding="utf-8")
            self.assertIn('"app.123" %*', text)
            self.assertIn("PYAPP_BATCH_ARGUMENTS=1", text)
            self.assertNotIn('call "%PYAPP_PYTHON%', text)
            unrelated = launch.parent / "custom.cmd"
            unrelated.write_text("echo custom", encoding="utf-8")
            s.generate_batch_shortcuts_for_args_launch = False
            self.assertEqual(batch_shortcuts.sync(s, "app.123", root), [])
            self.assertTrue(unrelated.exists())
            self.assertFalse(launch.exists())

    def test_generated_start_batch_forwards_real_cmd_arguments_without_call_reparsing(self):
        s = SimpleNamespace(generate_batch_shortcuts_for_args_launch=True)
        config.fill_missing_settings(s)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backend = root / "code/pyapp/DONT_CHANGE"
            (backend / "bootstrap").mkdir(parents=True)
            (backend / "scripts").mkdir()
            (backend / "bootstrap/ensure_runtime.bat").write_bytes(
                f'@echo off\r\nset "PYAPP_PYTHON={sys.executable}"\r\nexit /b 0\r\n'.encode()
            )
            (backend / "scripts/entrypoint.py").write_text(
                "import json,sys; print(json.dumps(sys.argv[2:]))\n", encoding="utf-8"
            )
            created = batch_shortcuts.sync(s, "app.123", root)
            launch = next(p for p in created if p.name == s.program_name + ".cmd")
            shell = str(Path(os.environ.get("WINDIR", "C:\\Windows")) / "System32/cmd.exe")
            # Fixed test arguments quoted for cmd.exe; no application code is executed.
            result = subprocess.run(  # noqa: S603
                f'"{shell}" /d /s /c ""{launch}" "" "a b" "A&B" "100%" "x(y)""',
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout), ["app.123", "", "a b", "A&B", "100%", "x(y)"])

    def test_browser_live_prefixes_affect_future_console_output_but_preserve_log_prefixes(self):
        with mock.patch.object(sys, "path", [str(DONT_CHANGE / "runtime"), *sys.path]):
            wrapper = runpy.run_path(str(DONT_CHANGE / "runtime/script_wrapper.py"), run_name="prefix_test")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preferences.json"
            console, log = io.StringIO(), io.StringIO()
            splitter = wrapper["PipeSplitter"](console, log, "PRINT ", "LOG ", "INPUT ", "LOGIN ")
            splitter.browser_preferences = path
            path.write_text(json.dumps({"printPrefix": False, "inputPrefix": False}), encoding="utf-8")
            splitter.write("hello\n")
            splitter.write_input_prompt("name? ")
            self.assertEqual(console.getvalue(), "hello\nname? ")
            self.assertEqual(log.getvalue(), "LOG hello\nLOGIN name? ")
            path.unlink()
            path.write_text(json.dumps({"printPrefix": True, "inputPrefix": True}), encoding="utf-8")
            splitter._preference_stamp = -1
            splitter.write_input_prompt("again\n")
            splitter.write("next\n")
            self.assertIn("INPUT again\nPRINT next", console.getvalue())


class CompilationTools(unittest.TestCase):
    def test_presets_and_cli_precedence_produce_distinct_expected_builds(self):
        with tempfile.TemporaryDirectory() as folder:
            config_file = Path(folder) / "settings.json"
            with mock.patch.object(compilation, "CONFIG", config_file), mock.patch.object(
                compilation, "LEGACY_CONFIG", Path(folder) / "legacy.json"
            ):
                for preset, mode, variant in (
                    ("development", "standalone", "terminal"),
                    ("standalone", "standalone", "terminal"),
                    ("onefile", "onefile", "terminal"),
                    ("gui", "standalone", "no_terminal"),
                ):
                    selected = compilation.load_options(preset, None, None)
                    self.assertEqual((selected.mode, selected.variant), (mode, variant))
                    self.assertEqual("--python-flag=unbuffered" in selected.extra_args, preset == "development")
                    command = compilation.build_command(
                        "python", Path("main.py"), mode, variant == "terminal", selected.extra_args, preset
                    )
                    self.assertIn(f"--output-dir={compilation.OUTPUT / preset / variant / mode}", command)
                config_file.write_text(
                    json.dumps({"preset": "gui", "mode": "onefile", "variant": "terminal"}), encoding="utf-8"
                )
                selected = compilation.load_options(None, None, None)
                self.assertEqual((selected.preset, selected.mode, selected.variant), ("gui", "onefile", "terminal"))
                selected = compilation.load_options("development", "standalone", "no_terminal")
                self.assertEqual(
                    (selected.preset, selected.mode, selected.variant), ("development", "standalone", "no_terminal")
                )

    def test_structured_options_and_legacy_extra_arguments_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            config_file, legacy = Path(folder) / "settings.json", Path(folder) / "legacy.json"
            config_file.write_text(
                json.dumps(
                    {
                        "jobs": 2,
                        "plugins": ["pyside6"],
                        "include_packages": ["my_plugins"],
                        "include_package_data": ["example"],
                        "include_data_files": ["config.json=config.json"],
                        "include_data_dirs": ["assets=assets"],
                        "extra_args": ["--lto=no"],
                    }
                ),
                encoding="utf-8",
            )
            legacy.write_text(json.dumps({"extra_args": ["--include-module", "old_plugin"]}), encoding="utf-8")
            with mock.patch.object(compilation, "CONFIG", config_file), mock.patch.object(
                compilation, "LEGACY_CONFIG", legacy
            ):
                selected = compilation.load_options(None, None, None)
            for option in (
                "--jobs=2",
                "--enable-plugin=pyside6",
                "--include-package=my_plugins",
                "--include-package-data=example",
                "--include-data-files=config.json=config.json",
                "--include-data-dir=assets=assets",
                "--include-module",
                "old_plugin",
                "--lto=no",
            ):
                self.assertIn(option, selected.extra_args)

    def test_invalid_settings_and_reserved_options_fail_before_environment_preparation(self):
        with tempfile.TemporaryDirectory() as folder:
            config_file = Path(folder) / "settings.json"
            invalid = (
                {"jobs": True},
                {"jobs": 0},
                {"plugins": "pyside6"},
                {"unbuffered": "yes"},
                {"preset": "unknown"},
                {"mode": ""},
                {"variant": False},
                {"typo": 1},
                {"include_data_dirs": ["assets"]},
                {"extra_args": ["--output-dir=elsewhere"]},
                {"extra_args": ["--mode=onefile"]},
                {"extra_args": ["--run"]},
            )
            with mock.patch.object(compilation, "CONFIG", config_file), mock.patch.object(
                compilation, "LEGACY_CONFIG", Path(folder) / "none"
            ), mock.patch.object(compilation, "prepare") as prepare:
                for value in invalid:
                    config_file.write_text(json.dumps(value), encoding="utf-8")
                    with self.subTest(value=value), self.assertRaises(compilation.SetupError):
                        compilation.cmd_compile_app([])
                prepare.assert_not_called()

    def test_dry_run_does_not_prepare_or_install_an_environment(self):
        with mock.patch.object(compilation, "prepare") as prepare, mock.patch.object(
            compilation, "print_info"
        ), mock.patch.object(compilation, "print_heading"):
            compilation.cmd_compile_app(["no_terminal", "--mode", "onefile", "--dry-run"])
            prepare.assert_not_called()

    def test_app_sources_include_pythonw_and_skip_launcher_and_virtual_environments(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "main.pyw").write_text("pass", encoding="utf-8")
            for name in ("pyapp", "environment", "package"):
                (root / name).mkdir()
                (root / name / "module.py").write_text("pass", encoding="utf-8")
            (root / "environment/pyvenv.cfg").write_text("home = example", encoding="utf-8")
            self.assertEqual(compilation.app_sources(root), sorted([root / "main.pyw", root / "package/module.py"]))

    def test_syntax_validation_does_not_execute_source_or_write_bytecode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "app.py"
            source.write_text("raise RuntimeError('must not run')\n", encoding="utf-8")
            compilation.validate_sources(sys.executable, [source])
            self.assertFalse((root / "__pycache__").exists())
            source.write_text("if :\n", encoding="utf-8")
            with self.assertRaises(compilation.SetupError):
                compilation.validate_sources(sys.executable, [source])

    def test_build_variants_and_clean_refuse_unowned_output(self):
        for terminal in (False, True):
            command = compilation.build_command("python.exe", Path("main.py"), "standalone", terminal, ["--jobs=2"])
            self.assertIn("--windows-console-mode=" + ("force" if terminal else "disable"), command)
            self.assertEqual(command[-1], "main.py")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "compilation"
            output.mkdir()
            with mock.patch.object(compilation, "OUTPUT", output), mock.patch.object(
                compilation.paths, "GENERATED_DIR", str(root)
            ):
                with self.assertRaises(compilation.SetupError):
                    compilation.cmd_clean_compilation([])
                (output / compilation.MARKER).write_text("owned", encoding="utf-8")
                compilation.cmd_clean_compilation([])
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
