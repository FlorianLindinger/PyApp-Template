"""Power, startup, bounded recovery, argument entry points and app compilation tools."""

from __future__ import annotations

import contextlib
import ctypes
import io
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional
from unittest import mock

from project_location import DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE.pyapp_tools.src import _ui
from pyapp.DONT_CHANGE.scripts import config, console_tools
from pyapp.DONT_CHANGE.scripts.desktop import batch_shortcuts, splash, terminal_window, windows_focus
from pyapp.DONT_CHANGE.scripts.dev_tools import compilation, linux_compilation, linux_worker
from pyapp.DONT_CHANGE.scripts.runtime import bg_watchdog
from pyapp.DONT_CHANGE.scripts.runtime._pyapp import ExitMode
from pyapp.DONT_CHANGE.scripts.standalone import power, processes


class LinuxCompilation(unittest.TestCase):
    def test_menu_preset_choice_by_number_enter_or_cancel(self):
        presets: Dict[str, Dict[str, object]] = {"development": {}, "standalone": {}, "onefile": {}, "gui": {}}
        for answer, expected in (("4", "gui"), ("", "standalone"), ("q", None), ("onefile", "onefile")):
            with self.subTest(answer=answer), mock.patch.object(
                compilation, "_presets", return_value=presets
            ), mock.patch.object(compilation, "_configured_preset", return_value="standalone"), mock.patch.object(
                compilation, "ask", return_value=answer
            ), mock.patch("builtins.print"):
                self.assertEqual(compilation._ask_preset(), expected)

    def test_cancelled_menu_choice_builds_nothing(self):
        with mock.patch.object(compilation, "_ask_preset", return_value=None), mock.patch.object(
            compilation, "load_options"
        ) as load, mock.patch("builtins.print"):
            compilation.cmd_compile_app(["--choose"])
        load.assert_not_called()

    def test_dry_run_does_not_invoke_wsl_or_prepare_windows_environment(self):
        with mock.patch.object(linux_compilation, "wsl") as wsl, mock.patch.object(compilation, "prepare") as prepare:
            linux_compilation.cmd_compile_linux(["--dry-run"])
        wsl.assert_not_called()
        prepare.assert_not_called()

    def test_windows_flags_and_gui_preset_rejected_before_wsl(self):
        for build in (
            compilation.BuildOptions("gui", "standalone", "no_terminal", []),
            compilation.BuildOptions("standalone", "standalone", "terminal", ["--msvc=latest"]),
        ):
            with mock.patch.object(compilation, "load_options", return_value=build), mock.patch.object(
                linux_compilation, "wsl"
            ) as wsl, self.assertRaises(linux_compilation.SetupError):
                linux_compilation.cmd_compile_linux([])
            wsl.assert_not_called()

    def test_worker_archives_artifact_preserves_report_and_removes_environment(self):
        import tarfile

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "result"
            output.mkdir()
            job = root / "job.json"
            job.write_text(
                json.dumps(
                    {
                        "python": "3.14",
                        "packages": ["example"],
                        "requirements": "",
                        "code": str(root),
                        "output": str(output),
                        "mode": "standalone",
                        "script": str(root / "hello.py"),
                        "extra": [],
                    }
                )
            )
            commands = []

            def fake_run(arguments: List[str], cwd: Optional[Path] = None) -> None:
                commands.append(arguments)
                if "nuitka" in arguments and "-m" in arguments:
                    build_output = Path(next(a.split("=", 1)[1] for a in arguments if a.startswith("--output-dir=")))
                    artifact = build_output / "hello.dist"
                    artifact.mkdir()
                    (artifact / "hello.bin").write_bytes(b"fixture")
                    (build_output / "compilation-report.xml").write_text("report")

            with mock.patch.object(linux_worker.sys, "platform", "linux"), mock.patch.object(
                linux_worker.Path, "home", return_value=root
            ), mock.patch.object(linux_worker.shutil, "which", return_value=sys.executable), mock.patch.object(
                linux_worker, "run", side_effect=fake_run
            ), mock.patch.object(linux_worker.platform, "platform", return_value="Linux-fixture"), mock.patch.object(
                linux_worker.subprocess, "run", return_value=SimpleNamespace(stdout="example==1\n")
            ):
                linux_worker.build(job)
            with tarfile.open(next(output.glob("*.tar.gz"))) as archive:
                self.assertIn("hello.dist/hello.bin", archive.getnames())
            self.assertEqual((output / "compilation-report.xml").read_text(), "report")
            self.assertEqual(list((root / ".cache/pyapp-compilation").glob("build-*")), [])
            self.assertTrue(any("--constraint" in command for command in commands))
            self.assertFalse(any(any(a.startswith("--windows-") for a in command) for command in commands))
            self.assertEqual((output / "linux-requirements.txt").read_text(), "example==1\n")

            def failing_run(arguments: List[str], cwd: Optional[Path] = None) -> None:
                fake_run(arguments, cwd)
                if "nuitka" in arguments and "-m" in arguments:
                    raise subprocess.CalledProcessError(1, arguments)

            with mock.patch.object(linux_worker.sys, "platform", "linux"), mock.patch.object(
                linux_worker.Path, "home", return_value=root
            ), mock.patch.object(linux_worker.shutil, "which", return_value=sys.executable), mock.patch.object(
                linux_worker, "run", side_effect=failing_run
            ), mock.patch.object(
                linux_worker.subprocess, "run", return_value=SimpleNamespace(stdout="example==1\n")
            ), self.assertRaises(subprocess.CalledProcessError):
                linux_worker.build(job)
            self.assertEqual(list((root / ".cache/pyapp-compilation").glob("build-*")), [])
            self.assertEqual((output / "compilation-report.xml").read_text(), "report")


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
            "pyapp.DONT_CHANGE.scripts.desktop.taskbar_status.terminal_window", return_value=123
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
        ), mock.patch("pyapp.DONT_CHANGE.scripts.desktop.taskbar_status.remember_window") as remember:
            dll.return_value.GetConsoleWindow.return_value = 123
            terminal_window.configure(s, "conhost")
            remember.assert_called_once_with(123)
            dll.return_value.ShowWindow.assert_called_once_with(123, 3)

    def test_crash_statuses_accept_signed_and_unsigned_but_not_ordinary_exits(self):
        for code in (0xC0000374, 0xC0000135, 0xC0000094, 0xC000008E, 0xC0000090, 0xC0000091, 0xC0000095):
            self.assertTrue(processes.exit_code_looks_like_interpreter_crash(code))
            self.assertTrue(processes.exit_code_looks_like_interpreter_crash(code - 2**32))
        for code in (True, None, 0, 1, -1, 0xC000013A):
            self.assertFalse(processes.exit_code_looks_like_interpreter_crash(code))

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
            (backend / "scripts" / "bootstrap").mkdir(parents=True)
            (backend / "B").mkdir()
            shutil.copyfile(DONT_CHANGE / "B" / "A.bat", backend / "B" / "A.bat")  # the real one
            (backend / "scripts/bootstrap/ensure_runtime.bat").write_bytes(
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
        with mock.patch.object(sys, "path", [str(DONT_CHANGE / "scripts" / "runtime"), *sys.path]):
            wrapper = runpy.run_path(str(DONT_CHANGE / "scripts/runtime/script_wrapper.py"), run_name="prefix_test")
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
    def test_temporary_compiler_removes_only_its_target_on_success_failure_and_interrupt(self):
        for failure in (None, compilation.SetupError("build failed"), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                preserved = root / "keep.txt"
                preserved.write_text("existing output", encoding="utf-8")
                targets: List[Path] = []
                installed = {"example": "1.2", "zstandard": "0.22.0"}

                def install(arguments: List[str], created: List[Path] = targets) -> None:
                    target = Path(arguments[arguments.index("--target") + 1])
                    target.mkdir()
                    (target / "nuitka.py").write_text("temporary compiler", encoding="utf-8")
                    created.append(target)
                    constraints = Path(arguments[arguments.index("--constraint") + 1]).read_text(encoding="utf-8")
                    self.assertIn("example==1.2", constraints)
                    self.assertIn("zstandard==0.22.0", constraints)

                with mock.patch.object(compilation, "OUTPUT", root), mock.patch.object(
                    compilation, "installed_packages", return_value=installed
                ), mock.patch.object(compilation, "run_uv", side_effect=install), mock.patch.dict(
                    os.environ, {"PYTHONPATH": "existing-imports"}
                ):
                    try:
                        with compilation.temporary_compiler(sys.executable) as env:
                            self.assertEqual(env["PYTHONPATH"].split(os.pathsep)[0], str(targets[0]))
                            self.assertTrue(targets[0].is_dir())
                            self.assertEqual(os.environ["PYTHONPATH"], "existing-imports")
                            if failure is not None:
                                raise failure
                    except (compilation.SetupError, KeyboardInterrupt) as error:
                        self.assertIs(error, failure)
                self.assertEqual(installed, {"example": "1.2", "zstandard": "0.22.0"})
                self.assertFalse(targets[0].exists())
                self.assertEqual(list(root.iterdir()), [preserved])

    def test_failed_temporary_install_is_cleaned_and_existing_tools_are_reused(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            compilation, "OUTPUT", Path(folder)
        ), mock.patch.object(compilation, "installed_packages", return_value={}), mock.patch.object(
            compilation, "run_uv", side_effect=compilation.SetupError("installation failed")
        ) as install:
            with self.assertRaisesRegex(compilation.SetupError, "installation failed"), compilation.temporary_compiler(
                sys.executable
            ):
                self.fail("A failed installation must not start compilation")
            self.assertEqual(list(Path(folder).iterdir()), [])
            install.assert_called_once()
        existing = {"nuitka": "2.8", "ordered-set": "4.1", "zstandard": "0.24"}
        with mock.patch.object(compilation, "installed_packages", return_value=existing), mock.patch.object(
            compilation, "run_uv"
        ) as install:
            with compilation.temporary_compiler(sys.executable) as env:
                self.assertEqual(env, dict(os.environ))
            install.assert_not_called()

    def test_compile_command_uses_temporary_packages_and_cleans_them_after_compiler_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "compilation"
            s = SimpleNamespace(main_script_path=str(root / "main.py"))
            build = compilation.BuildOptions("standalone", "standalone", "terminal", [])
            with mock.patch.object(compilation, "OUTPUT", output), mock.patch.object(
                compilation, "settings", return_value=s
            ), mock.patch.object(
                compilation, "prepare", return_value=SimpleNamespace(exe=sys.executable)
            ), mock.patch.object(compilation, "load_options", return_value=build), mock.patch.object(
                compilation, "validate_sources"
            ), mock.patch.object(compilation, "installed_packages", return_value={}), mock.patch.object(
                compilation, "run_uv"
            ), mock.patch.object(
                compilation.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)
            ) as compiler:
                with self.assertRaisesRegex(compilation.SetupError, "Nuitka compilation failed"):
                    compilation.cmd_compile_app([])
                imports = compiler.call_args.kwargs["env"]["PYTHONPATH"].split(os.pathsep)[0]
                self.assertIn(".nuitka-build-", imports)
                self.assertFalse(Path(imports).parent.exists())
                self.assertTrue((output / compilation.MARKER).is_file())

    def test_presets_and_cli_precedence_produce_distinct_expected_builds(self):
        with tempfile.TemporaryDirectory() as folder:
            config_file = Path(folder) / "settings.json"
            with mock.patch.object(compilation, "CONFIG", config_file):
                for preset, mode, variant in (
                    ("development", "standalone", "terminal"),
                    ("standalone", "standalone", "terminal"),
                    ("onefile", "onefile", "terminal"),
                    ("gui", "standalone", "no_terminal"),
                ):
                    selected = compilation.load_options(preset, None, None)
                    self.assertEqual((selected.mode, selected.variant), (mode, variant))
                    self.assertEqual("--python-flag=unbuffered" in selected.extra_args, preset == "development")
                    target = compilation.output_folder(selected)
                    self.assertEqual(target, compilation.OUTPUT / "windows" / preset)
                    command = compilation.build_command(
                        "python", Path("main.py"), mode, variant == "terminal", selected.extra_args, target
                    )
                    self.assertIn(f"--output-dir={target}", command)
                config_file.write_text(
                    json.dumps({"preset": "gui", "mode": "onefile", "variant": "terminal"}), encoding="utf-8"
                )
                selected = compilation.load_options(None, None, None)
                self.assertEqual((selected.preset, selected.mode, selected.variant), ("gui", "onefile", "terminal"))
                selected = compilation.load_options("development", "standalone", "no_terminal")
                self.assertEqual(
                    (selected.preset, selected.mode, selected.variant), ("development", "standalone", "no_terminal")
                )

    def test_structured_options_and_extra_arguments_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            config_file = Path(folder) / "settings.json"
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
            with mock.patch.object(compilation, "CONFIG", config_file):
                selected = compilation.load_options(None, None, None)
            for option in (
                "--jobs=2",
                "--enable-plugin=pyside6",
                "--include-package=my_plugins",
                "--include-package-data=example",
                "--include-data-files=config.json=config.json",
                "--include-data-dir=assets=assets",
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
                compilation, "prepare"
            ) as prepare:
                for value in invalid:
                    config_file.write_text(json.dumps(value), encoding="utf-8")
                    with self.subTest(value=value), self.assertRaises(compilation.SetupError):
                        compilation.cmd_compile_app([])
                prepare.assert_not_called()

    def test_dry_run_does_not_prepare_or_install_an_environment(self):
        with mock.patch.object(compilation, "prepare") as prepare, mock.patch.object(
            compilation, "print_info"
        ), mock.patch.object(compilation, "print_heading"), mock.patch.object(
            compilation, "temporary_compiler"
        ) as compiler:
            compilation.cmd_compile_app(["no_terminal", "--mode", "onefile", "--dry-run"])
            prepare.assert_not_called()
            compiler.assert_not_called()

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

    def test_each_preset_replaces_its_own_build_and_keep_makes_a_dated_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "compiled"
            with mock.patch.object(compilation, "OUTPUT", output):
                build = compilation.BuildOptions("gui", "standalone", "no_terminal", [])
                target = compilation.output_folder(build)
                self.assertEqual(target, output / "windows" / "gui")
                compilation.reserve_output(target)
                (target / "old.exe").write_text("previous build", encoding="utf-8")
                compilation.reserve_output(target)
                self.assertEqual(list(target.iterdir()), [], "no file of the previous build may remain")
                changed = compilation.BuildOptions("gui", "onefile", "terminal", [])
                self.assertEqual(compilation.output_folder(changed).name, "gui-onefile-terminal")
                self.assertEqual(compilation.output_folder(build, platform="linux"), output / "linux" / "gui")
                kept = compilation.output_folder(build, keep=True)
                self.assertRegex(kept.name, r"^gui-\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")

    def test_build_variants_and_clean_refuse_unowned_output(self):
        for terminal in (False, True):
            command = compilation.build_command("python.exe", Path("main.py"), "standalone", terminal, ["--jobs=2"])
            self.assertIn("--windows-console-mode=" + ("force" if terminal else "disable"), command)
            self.assertEqual(command[-1], "main.py")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "compiled"
            output.mkdir()
            with mock.patch.object(compilation, "OUTPUT", output), mock.patch.object(
                compilation.paths, "BACKEND_DIR", str(root)
            ):
                with self.assertRaises(compilation.SetupError):
                    compilation.cmd_clean_compilation([])
                (output / compilation.MARKER).write_text("owned", encoding="utf-8")
                compilation.cmd_clean_compilation([])
                self.assertFalse(output.exists())


class StartupSplash(unittest.TestCase):
    def test_environment_failure_closes_the_splash_in_the_real_startup_flow(self):
        from pyapp.DONT_CHANGE.scripts.actions import start_program

        settings = config.settings()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(start_program, "settings", return_value=settings))
            stack.enter_context(mock.patch.object(start_program, "resolve_mode", return_value="no_terminal"))
            stack.enter_context(mock.patch.object(start_program, "set_terminal_appearance_once"))
            stack.enter_context(mock.patch.object(start_program, "decide", return_value="allow"))
            registry = stack.enter_context(mock.patch.object(start_program, "ProcessRegistry"))
            stack.enter_context(mock.patch.object(start_program, "delete_finished_run_folders"))
            stack.enter_context(mock.patch("pyapp.DONT_CHANGE.scripts.hidden_caches.hide_cache_folders"))
            spawn = stack.enter_context(mock.patch.object(splash.subprocess, "Popen"))
            thread = stack.enter_context(mock.patch.object(splash.threading, "Thread"))

            def fail_environment(**kwargs: object) -> None:
                spawn.assert_called_once()
                spawn.return_value.stdin.close.assert_not_called()
                raise RuntimeError("environment failed")

            stack.enter_context(mock.patch.object(start_program, "ensure_environment", side_effect=fail_environment))
            registry.return_value.records.return_value = ((), ())
            with self.assertRaisesRegex(RuntimeError, "environment failed"):
                start_program.main()
            spawn.return_value.stdin.close.assert_called_once()
            thread.call_args.kwargs["target"]()
            spawn.return_value.wait.assert_called_once_with(timeout=5)

    def settings(self, **changes: object) -> SimpleNamespace:
        values: Dict[str, object] = {
            "show_splash_screen_for_no_terminal_start": True,
            "start_minimized": False,
            "start_maximized": False,
            "program_name": "Test App",
        }
        values.update(changes)
        return SimpleNamespace(**values)

    def test_disabled_and_minimized_launches_do_not_spawn(self):
        for changes in ({"show_splash_screen_for_no_terminal_start": False}, {"start_minimized": True}):
            with mock.patch.object(splash.subprocess, "Popen") as spawn:
                with splash.startup_splash(self.settings(**changes), "no_terminal"):
                    pass
                spawn.assert_not_called()

    def test_terminal_and_browser_modes_do_not_spawn(self):
        for mode in ("conhost", "wt", "browser", "terminal", ""):
            with self.subTest(mode=mode), mock.patch.object(splash.subprocess, "Popen") as spawn:
                with splash.startup_splash(self.settings(), mode):
                    pass
                spawn.assert_not_called()

    def test_no_terminal_minimum_is_passed_to_helper_and_reaped_in_parallel(self):
        with mock.patch.object(splash.subprocess, "Popen") as spawn, mock.patch.object(
            splash.threading, "Thread"
        ) as thread:
            with splash.startup_splash(self.settings(), "no_terminal"):
                self.assertEqual(spawn.call_args.args[0][-1], "0.5")
            spawn.return_value.stdin.close.assert_called_once()
            spawn.return_value.wait.assert_not_called()
            thread.return_value.start.assert_called_once()
            self.assertTrue(thread.call_args.kwargs["daemon"])
            thread.call_args.kwargs["target"]()
            spawn.return_value.wait.assert_called_once_with(timeout=5)

    def test_success_and_failure_close_pipe_and_reap_helper(self):
        for fail in (False, True):
            with mock.patch.object(splash.subprocess, "Popen") as spawn, mock.patch.object(
                splash.threading, "Thread"
            ) as thread:
                child = spawn.return_value
                try:
                    with splash.startup_splash(
                        self.settings(start_minimized=True, start_maximized=True), "no_terminal"
                    ):
                        child.stdin.close.assert_not_called()
                        if fail:
                            raise RuntimeError("environment failed")
                except RuntimeError:
                    self.assertTrue(fail)
                child.stdin.close.assert_called_once()
                thread.call_args.kwargs["target"]()
                child.wait.assert_called_once_with(timeout=5)
                self.assertIn("Test App", spawn.call_args.args[0])

    def test_spawn_failure_does_not_prevent_startup(self):
        with mock.patch.object(splash.subprocess, "Popen", side_effect=OSError("unavailable")), mock.patch(
            "pyapp.DONT_CHANGE.scripts.diagnostics.note_ignored"
        ) as note:
            with splash.startup_splash(self.settings(), "no_terminal"):
                pass
            note.assert_called_once()

    def test_stalled_helper_is_killed_and_reaped(self):
        with mock.patch.object(splash.subprocess, "Popen") as spawn, mock.patch.object(
            splash.threading, "Thread"
        ) as thread:
            child = spawn.return_value
            child.wait.side_effect = [subprocess.TimeoutExpired("splash", 1), 0]
            with splash.startup_splash(self.settings(), "no_terminal"):
                pass
            thread.call_args.kwargs["target"]()
            child.kill.assert_called_once()
            self.assertEqual(child.wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
