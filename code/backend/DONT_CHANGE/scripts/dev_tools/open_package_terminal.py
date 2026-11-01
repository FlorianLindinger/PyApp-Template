# ruff: noqa: E402 RUF100
"""Interactive, shell-free package commands for the managed application environment."""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

import ast
import ctypes
import shutil
import subprocess
import sys
from pathlib import Path

from backend.developer_settings import use_uv_to_install_packages
from backend.DONT_CHANGE.scripts.frontend_environment import (
    ensure_python_distro,
    environment_locked,
    make_file_to_indicate_frontend_pckgs_installed,
    refuse_mutation_while_running,
    save_current_packages_as_default,
)
from backend.DONT_CHANGE.scripts.runtime_state import clean_python_environment
from backend.DONT_CHANGE.settings.backend_settings import (
    BACKEND_PYTHON_EXE,
    FRONTEND_PACKAGES_DIR,
    FRONTEND_PYTHON_EXE,
    UV_VERSION,
)

HELP = """Package commands (no Python/module prefix needed):
  requests                         Install one package
  requests rich>=13                Install several packages
  requests, rich                   Comma-separated packages
  ["requests", "rich>=13"]          A Python-style list of requirements
  install -r "my requirements.txt"  Install a requirements file
  upgrade requests rich            Upgrade selected packages
  uninstall requests               Remove a package (installer asks if needed)
  list / list --outdated / show requests / check / freeze
  pip install requests             Explicit pip command
  uv pip install requests          Explicit uv package command
  uv --version                     Inspect the available uv tool
  save                             Save installed versions as declared defaults
  status / help / exit

Bare packages and unprefixed package actions prefer uv when enabled, with pip
fallback. Explicit pip/uv commands select that tool. Double-quote paths or
requirements containing spaces. Version constraints are passed literally;
shell redirection, pipes and command chaining are not evaluated here.
"""


def split_command(line: str) -> list[str]:
    """Parse a package list or Windows arguments without evaluating shell syntax."""
    line = line.strip()
    if line.startswith("["):
        values = ast.literal_eval(line)
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValueError('Use a list of package strings, e.g. ["requests", "rich"].')
        return values
    if not line:
        return []
    from ctypes import wintypes

    shell = ctypes.WinDLL("shell32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW("packages " + line, ctypes.byref(count))
    if not pointer:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return [pointer[index] for index in range(1, count.value)]
    finally:
        kernel.LocalFree(pointer)


def expand_package_commas(arguments: list[str]) -> list[str]:
    """Accept comma-separated names while preserving extras, version ranges and URLs."""
    from pip._vendor.packaging.requirements import InvalidRequirement, Requirement

    expanded = []
    for argument in arguments:
        if argument == ",":
            continue
        if "," in argument and not argument.startswith("-"):
            try:
                Requirement(argument)
            except InvalidRequirement:
                pieces = [piece for piece in argument.split(",") if piece]
                try:
                    for piece in pieces:
                        Requirement(piece)
                except InvalidRequirement:
                    pass
                else:
                    expanded.extend(pieces)
                    continue
        expanded.append(argument)
    return expanded


class PackageConsole:
    """Dispatch package commands without shell interpretation or interpreter-path assumptions."""

    def __init__(self):
        """Capture current resolved environment paths and installer preference."""
        self.python = FRONTEND_PYTHON_EXE
        self.target = FRONTEND_PACKAGES_DIR
        self.prefer_uv = use_uv_to_install_packages
        self.last_code = 0
        self.dirty = False
        self._uv_install_attempted = False

    def uv_command(self, install_if_missing: bool = True) -> list[str] | None:
        """Resolve uv, optionally provisioning the pinned tool locally once per session."""
        command = [BACKEND_PYTHON_EXE, "-E", "-s", "-m", "uv"]
        try:
            probe = subprocess.run(
                command + ["--version"],
                env=clean_python_environment(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            if probe.returncode == 0:
                return command
        except (OSError, subprocess.TimeoutExpired):
            pass
        # Resolve an executable, not our own portable uv.cmd adapter.
        executable = shutil.which("uv.exe")
        if executable:
            return [executable]
        if install_if_missing and not self._uv_install_attempted:
            self._uv_install_attempted = True
            print("[Info] Preparing local uv " + UV_VERSION + " for package commands.")
            try:
                code = self.run(
                    [
                        BACKEND_PYTHON_EXE,
                        "-E",
                        "-s",
                        "-m",
                        "pip",
                        "install",
                        "uv==" + UV_VERSION,
                        "--target",
                        str(Path(BACKEND_PYTHON_EXE).parent / "Lib/site-packages"),
                        "--upgrade",
                        "--disable-pip-version-check",
                    ]
                )
                if code == 0:
                    return self.uv_command(install_if_missing=False)
            except OSError as error:
                print("[Warning] Could not prepare uv: " + str(error))
        return None

    def run(self, command: list[str]) -> int:
        """Run literal arguments against a clean package-tool environment."""
        env = clean_python_environment()
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        print("[Run] " + subprocess.list2cmdline(command), flush=True)
        return subprocess.run(command, env=env, check=False).returncode

    def execute(self, arguments: list[str]) -> int:
        """Execute one explicit installer command or preferred-tool package shorthand."""
        if not arguments:
            return 0
        tool = "auto"
        if arguments[0].lower() in {"pip", "pip3", "uv"} or arguments[0].lower().startswith("pip3."):
            tool, arguments = arguments[0].lower(), arguments[1:]
            if tool.startswith("pip"):
                tool = "pip"
        if tool == "uv" and arguments and arguments[0] == "pip":
            arguments = arguments[1:]
        elif tool == "uv" and (not arguments or arguments[0] in {"--version", "-V", "--help", "-h"}):
            uv = self.uv_command()
            return self.run(uv + arguments) if uv else self.unavailable_uv()
        elif tool == "uv" and arguments[0] not in {
            "install",
            "uninstall",
            "list",
            "freeze",
            "show",
            "check",
            "tree",
            "compile",
            "sync",
        }:
            raise ValueError("This console manages app packages: use uv pip <command>, or uv --help.")
        if not arguments:
            arguments = ["--help"]
        global_flags = []
        while arguments and arguments[0] in {
            "-v",
            "-vv",
            "-vvv",
            "--verbose",
            "-q",
            "--quiet",
            "--no-cache-dir",
            "--no-cache",
            "--isolated",
            "--disable-pip-version-check",
        }:
            global_flags.append(arguments[0])
            arguments = arguments[1:]
        if not arguments:
            arguments = ["--help"]
        action, *options = arguments
        options = [*global_flags, *options]
        if tool != "auto" and action.startswith("-") and action not in {"--version", "-V", "--help", "-h"}:
            raise ValueError("Put installer options after the action, e.g. pip install --proxy URL package.")
        if tool == "auto" and action.startswith("-") and action not in {"-h", "--help", "--version"}:
            action, options = "install", [action, *options]
        if action in {"remove", "upgrade"}:
            action, options = ("uninstall", options) if action == "remove" else ("install", ["--upgrade", *options])
        known = {
            "install",
            "uninstall",
            "list",
            "freeze",
            "show",
            "check",
            "download",
            "wheel",
            "index",
            "cache",
            "inspect",
            "debug",
            "config",
            "hash",
            "help",
            "tree",
            "compile",
            "sync",
        }
        if tool == "auto" and action not in known and not action.startswith("-"):
            action, options = "install", [action, *options]
        if action in {"install", "uninstall"}:
            options = expand_package_commas(options)
        # Environment selection belongs to this console; installer flags remain available.
        for option in options:
            if option.split("=", 1)[0] in {
                "--target",
                "-t",
                "--prefix",
                "--python",
                "-p",
                "--user",
                "--system",
            }:
                raise ValueError(
                    "This console targets the app environment; change packages here without a target/interpreter override."
                )
        self.dirty |= action in {"install", "uninstall", "sync"}
        pip = [self.python, "-E", "-s", "-m", "pip", action, *options]
        if action == "install":
            pip += ["--target", self.target]
        elif action in {"list", "freeze"}:
            pip += ["--path", self.target]
        use_uv = (
            tool == "uv"
            or tool == "auto"
            and self.prefer_uv
            and action in {"install", "uninstall", "list", "freeze", "show", "check"}
        )
        if use_uv:
            uv = self.uv_command()
            if uv:
                uv_args = [*uv, "pip", action, *options]
                if not action.startswith("-") and action not in {"help", "compile"}:
                    uv_args += ["--python", self.python]
                    if action not in {"check", "tree"}:
                        uv_args += ["--target", self.target]
                if action in {"install", "sync"}:
                    uv_args += ["--link-mode", "copy"]
                # pip's confirmation/cache flags are not uv flags.
                uv_args = [
                    "--no-cache" if arg == "--no-cache-dir" else arg for arg in uv_args if arg not in {"-y", "--yes"}
                ]
                try:
                    code = self.run(uv_args)
                except OSError as error:
                    if tool == "uv":
                        raise
                    print("[Warning] Could not start uv: " + str(error))
                    code = 1
                if code == 0 or tool == "uv":
                    return code
                print("[Warning] uv failed; retrying with pip.")
            elif tool == "uv":
                return self.unavailable_uv()
            else:
                print("[Warning] uv is unavailable; using pip.")
        return self.run(pip)

    def unavailable_uv(self) -> int:
        """Report explicit uv unavailability without substituting another requested tool."""
        print("[Error] uv is unavailable. Use pip, or an unprefixed command for automatic fallback.")
        return 1

    def status(self) -> None:
        """Display the app environment and automatic installer policy."""
        print("Python: " + self.python)
        print("Packages: " + self.target)
        print("Default installer: " + ("uv, with pip fallback" if self.prefer_uv else "pip"))
        print("Last command exit code: " + str(self.last_code))

    def interact(self) -> None:
        """Keep the console available after command errors and validate live edits on exit."""
        self.status()
        print(HELP)
        while True:
            try:
                line = input("packages> ").strip()
                if line.lower() in {"exit", "quit"}:
                    break
                if not line:
                    continue
                if line.lower() in {"help", "?"}:
                    print(HELP)
                elif line.lower() == "status":
                    self.status()
                elif line.lower() == "save":
                    make_file_to_indicate_frontend_pckgs_installed()
                    save_current_packages_as_default(auto_search_phrase_state=False)
                    make_file_to_indicate_frontend_pckgs_installed()
                    print("[Success] Saved installed versions as defaults. Review and commit the defaults file.")
                else:
                    self.last_code = self.execute(split_command(line))
                    print(
                        "[Success]"
                        if self.last_code == 0
                        else "[Error] Installer exited with code " + str(self.last_code)
                    )
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n[Info] Interrupted. The console remains open; type exit to finish.")
            except (ValueError, SyntaxError, OSError) as error:
                self.last_code = 1
                print("[Error] " + str(error))
            except subprocess.CalledProcessError as error:
                self.last_code = error.returncode
                print("[Error] Validation failed; correct the packages before saving defaults.")
        make_file_to_indicate_frontend_pckgs_installed()


@environment_locked
def main() -> int:
    """Prepare and lock the managed environment for one command or an interactive session."""
    ensure_python_distro()
    refuse_mutation_while_running()
    Path(FRONTEND_PACKAGES_DIR).mkdir(parents=True, exist_ok=True)
    console = PackageConsole()
    if sys.argv[1:]:
        code = console.execute(sys.argv[1:])
        if console.dirty:
            make_file_to_indicate_frontend_pckgs_installed()
        return code
    console.interact()
    return 0
