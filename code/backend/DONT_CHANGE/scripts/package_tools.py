"""Package installation, inventories, and import inference."""

import os
import sys
from collections.abc import Sequence

from backend.DONT_CHANGE.scripts.console_tools import print_warn
from backend.DONT_CHANGE.scripts.filesystem_tools import read_lines, write_lines


def install_packages(
    python_exe: str,
    packages: str | list[str] | tuple[str, ...] | None = None,
    requirements_file: str | None = None,
    target: str | None = None,
    upgrade: bool = False,
    no_deps: bool = False,
    no_cache: bool = False,
    use_uv: bool = False,
    install_uv_locally_if_global_not_available: bool = True,
    local_uv_python_exe: str | None = None,
    extra_args: str | list[str] | tuple[str, ...] | None = None,
    disable_pip_version_check: bool = True,
    no_warn_script_location: bool = True,
    uninstall: bool = False,
):
    """Install or uninstall packages with pip, optionally trying uv first.

    ``python_exe`` is the interpreter whose package environment should be
    changed. For normal backend runtime packages this is still the backend
    Python executable, while ``target`` points pip/uv at the separate
    ``backend_packages`` runtime folder. Build/install tools should usually be
    installed without ``target`` so they land in the interpreter environment and
    can be removed again after the targeted runtime install is finished.

    ``packages`` may be one package string or a sequence of package strings.
    ``requirements_file`` may be one requirements file path. At least one of
    those inputs is required. The requirements file is passed to pip/uv with
    ``-r``, so pip/uv handle normal requirement parsing instead of this helper
    trying to parse the file.

    Set ``uninstall=True`` to run uninstall instead of install. Uninstalls are
    confirmed automatically with ``-y`` because these scripts run unattended.
    Install-only options are ignored for uninstall: ``target``, ``upgrade``,
    ``no_deps``, ``no_cache``, ``disable_pip_version_check``, and
    ``no_warn_script_location``.

    pip is the default and final fallback. If ``use_uv`` is true, a globally
    available ``uv`` executable is tried first. If no global uv is found and
    ``install_uv_locally_if_global_not_available`` is true (default), uv is
    installed into ``local_uv_python_exe`` and run as
    ``local_uv_python_exe -m uv``. If ``local_uv_python_exe`` is not given,
    ``python_exe`` is used for local uv as well. The local uv install is kept
    after the package operation; this helper does not uninstall it.

    ``local_uv_python_exe`` is useful when the Python that runs uv should be
    different from the Python being modified. For example, backend Python can
    run ``uv`` while uv installs frontend packages with ``--python`` pointing at
    frontend Python.

    If local uv cannot be installed or the uv command fails, this helper prints
    a warning and retries the same package operation with pip.

    ``extra_args`` are appended last to the selected pip/uv command. Use them
    for uncommon flags only; prefer the named options above for behavior that
    this repo relies on.
    """
    from backend.DONT_CHANGE.scripts.runtime_state import clean_python_environment

    install_env = clean_python_environment()
    import shutil
    import subprocess

    def _as_list(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
        """Normalize an optional package string or sequence into a list of package arguments."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    package_args = _as_list(packages)
    extra_args_list = _as_list(extra_args)
    if not package_args and requirements_file is None:
        raise ValueError("No packages or requirements file was given.")

    local_uv_python_exe = local_uv_python_exe or python_exe

    pip_args = [
        python_exe,
        "-E",
        "-s",
        "-m",
        "pip",
        "uninstall" if uninstall else "install",
    ]
    if requirements_file is not None:
        pip_args.extend(["-r", requirements_file])
    pip_args.extend(package_args)

    if not uninstall:
        if target is not None:
            pip_args.extend(["--target", target])
        if upgrade:
            pip_args.append("--upgrade")
        if no_deps:
            pip_args.append("--no-deps")
        if no_cache:
            pip_args.append("--no-cache-dir")
        if disable_pip_version_check:
            pip_args.append("--disable-pip-version-check")
        if no_warn_script_location:
            pip_args.append("--no-warn-script-location")
    else:
        pip_args.append("-y")
    pip_args.extend(extra_args_list)

    uv_command: list[str] | None = None
    if use_uv:
        global_uv = shutil.which("uv")
        if global_uv:
            uv_command = [
                global_uv,
                "pip",
                "uninstall" if uninstall else "install",
                "--python",
                python_exe,
            ]

    if uv_command is None and use_uv and install_uv_locally_if_global_not_available:
        local_uv_command = [
            local_uv_python_exe,
            "-m",
            "uv",
            "pip",
            "uninstall" if uninstall else "install",
            "--python",
            python_exe,
        ]
        try:
            local_uv_probe = subprocess.run(
                [local_uv_python_exe, "-m", "uv", "--version"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if local_uv_probe.returncode == 0:
                uv_command = local_uv_command
            else:
                uv_install_args = [
                    python_exe,
                    "-E",
                    "-s",
                    "-m",
                    "pip",
                    "install",
                    "uv==0.8.22",
                    "--disable-pip-version-check",
                    "--no-warn-script-location",
                ]
                if local_uv_python_exe != python_exe:
                    uv_install_args.extend(
                        [
                            "--target",
                            os.path.join(
                                os.path.dirname(local_uv_python_exe),
                                "Lib",
                                "site-packages",
                            ),
                        ]
                    )
                if no_cache:
                    uv_install_args.append("--no-cache-dir")
                subprocess.run(uv_install_args, check=True, env=install_env)
                uv_command = local_uv_command
        except Exception as error:
            print(
                f"[Warning] local uv installation failed. Falling back to pip. Error: {error}"
            )

    if uv_command is not None:
        uv_args = [*uv_command]
        if requirements_file is not None:
            uv_args.extend(["-r", requirements_file])
        uv_args.extend(package_args)

        if not uninstall:
            if target is not None:
                uv_args.extend(["--target", target])
            if upgrade:
                uv_args.append("--upgrade")
            if no_deps:
                uv_args.append("--no-deps")
            if no_cache:
                uv_args.append("--no-cache")
            uv_args.extend(["--link-mode", "copy"])
        else:
            uv_args.append("-y")
        uv_args.extend(extra_args_list)

        uv_result = subprocess.run(uv_args, check=False, env=install_env)
        if uv_result.returncode == 0:
            return uv_result

        print(
            f"[Warning] uv package {'uninstall' if uninstall else 'install'} failed. Falling back to pip."
        )

    return subprocess.run(pip_args, check=True, env=install_env)


def get_installed_packages(
    exe_path: str, with_version: bool = True, target: str | None = None
):
    """Read installed distribution names or version pins through the selected interpreter's pip."""
    import subprocess

    from backend.DONT_CHANGE.scripts.runtime_state import clean_python_environment

    result = subprocess.run(
        [
            exe_path,
            "-E",
            "-s",
            "-m",
            "pip",
            "--disable-pip-version-check",
            "freeze",
            *(["--path", target] if target else []),
        ],
        capture_output=True,
        text=True,
        check=True,
        env=clean_python_environment(),
    )
    packages_with_version = result.stdout.strip().splitlines()

    if with_version:
        return packages_with_version
    else:
        packages_without_version = []

        for line in packages_with_version:
            line = line.strip()

            if line == "" or line.startswith("#"):
                continue

            for operator in ("===", "==", "~=", ">=", "<=", "!=", ">", "<"):
                if operator in line:
                    packages_without_version.append(line.split(operator, 1)[0].strip())
                    break
            else:
                packages_without_version.append(line)

        return packages_without_version


def save_installed_packages(
    exe_path: str,
    output_path: str = "requirements.txt",
    with_version: bool = True,
    target: str | None = None,
):
    """Write an installed-package inventory to an absolute requirements path and return it."""
    output_path = os.path.abspath(output_path)

    packages = get_installed_packages(
        with_version=with_version, exe_path=exe_path, target=target
    )

    write_lines(output_path, packages)

    return output_path


def save_requirements_of_folder_noVersion(
    target_folder: str,
    output_path: str,
    excluded_folders: Sequence[str] = (
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
    ),
    print_: bool = True,
) -> bool:
    """Save the pipreqs determined python package requirement without a package version. See save_requirements_of_folder_withVersion for with version.

    Returns success bool"""

    import subprocess

    output_path = os.path.abspath(output_path)

    if os.path.exists(output_path):
        os.remove(output_path)

    try:
        cmd = [
            sys.executable,
            "-m",
            "pipreqs.pipreqs",
            target_folder,  # searched_folder,
            "--force",
            "--savepath",
            output_path,
            "--ignore",
            ",".join(excluded_folders),  # excluded_folders
            "--encoding",
            "utf-8",
            "--mode",
            "no-pin",
            "--no-follow-links",
        ]

        if print_:
            print()
            print("=" * 20)
            print("Start of finding required python packages")
            print("-" * 20)
        subprocess.run(cmd, check=True)

        if os.path.exists(output_path):
            if print_:
                print("-" * 20)
                print(
                    f'End of finding required python packages. Result: "{output_path}":\n'
                )
                packages = read_lines(output_path)
                print(*packages, sep="\n")
                print("=" * 20)
                print()

            success = True

        else:
            success = False
            if print_:
                print()
                print_warn(
                    "[Error] Failed to auto determine needed packages (see above)"
                )
    except Exception as e:
        if print_:
            print()
            print_warn(
                f"[Error] Failed to auto determine packages (do you have internet?): {e}"
            )
        success = False

    return success


def save_requirements_of_folder_withVersion(
    target_folder: str,
    output_path: str,
    python_exe: str,
    print_: bool = True,
    excluded_folders: Sequence[str] = ("__pycache__", ".git", ".hg", ".svn"),
) -> bool:
    """Save the pipreqs determined python package requirement with a package version. See save_requirements_of_folder_noVersion for wihtout version.

    Returns success bool

    Installation into a fresh temp venv needed to determine package versions. Pipreqs only can determine what packages are needed.

    lazy imports subprocess and tempfile."""

    # lazy imports
    import subprocess
    import tempfile

    output_path = os.path.normpath(os.path.abspath(output_path))

    try:
        with tempfile.TemporaryDirectory(
            prefix="tmp_venv_to_get_package_version"
        ) as tmp:
            temp_requirements = tmp + "\\tmp_package_requirements"
            success = save_requirements_of_folder_noVersion(
                print_=print_,
                target_folder=target_folder,
                output_path=temp_requirements,
                excluded_folders=excluded_folders,
            )
            if not success:
                return False

            temp_python = tmp + "\\Scripts\\python.exe"

            subprocess.run([python_exe, "-m", "venv", tmp], check=True)
            if not os.path.exists(temp_python):
                raise RuntimeError(
                    f'Temporary environment did not create "{temp_python}"'
                )

            subprocess.run(
                [
                    temp_python,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    temp_requirements,
                    "--disable-pip-version-check",
                    "--no-warn-script-location",
                ],
                check=True,
            )

            save_installed_packages(
                exe_path=temp_python, output_path=output_path, with_version=True
            )

            return True

    except Exception as e:
        if print_:
            print()
            print_warn(f"[Error] Failed to auto determine packages: {e}")
        return False
