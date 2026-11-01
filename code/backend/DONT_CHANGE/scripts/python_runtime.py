"""Full Python discovery, installation, and runtime configuration."""

import os
from pathlib import Path
from typing import override

from backend.DONT_CHANGE.scripts.filesystem_tools import (
    delete_folder_safe,
    read_lines,
    write_lines,
)


def get_python_version(python_exe: str) -> str:
    """Query the selected interpreter's version without Python environment or user-site overrides."""
    import subprocess

    from backend.DONT_CHANGE.scripts.runtime_state import clean_python_environment

    return subprocess.check_output(
        [python_exe, "-E", "-s", "-c", "import sys; print(sys.version.split()[0])"],
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
        env=clean_python_environment(),
    ).strip()


def is_python_version_compatible(actual_version: str, required_version: str) -> bool:
    """Compare a full interpreter version with the requested major, minor or patch prefix."""
    actual_parts = actual_version.split(".")
    required_parts = required_version.strip().split(".")

    if (len(actual_parts) != 3) or (any(not part.isdigit() for part in actual_parts)):
        raise ValueError(
            f"Could not determine Python version from output: {actual_version}. Expected format like '3.13.2'."
        )

    if not required_parts or any(not part.isdigit() for part in required_parts):
        raise ValueError(
            f"Invalid target_version format: {required_version}. Must be a string like '3', '3.13', or '3.13.2'."
        )

    return actual_parts[: len(required_parts)] == required_parts


def configure_python_package_path(
    python_dir_abs_path: str, rel_path_to_packages: str
) -> None:
    """Register the shared package folder, including its .pth startup hooks."""
    site_packages_dir = Path(python_dir_abs_path) / "Lib" / "site-packages"
    site_packages_dir.mkdir(parents=True, exist_ok=True)
    relative_path = rel_path_to_packages.replace("\\", "/")
    content = (
        "# Process shared packages and their .pth files at interpreter startup.\n"
        "import os, site, sys; "
        f"site.addsitedir(os.path.join(sys.prefix, {relative_path!r}))\n"
    )
    path_file = site_packages_dir / "_PATH_TO_PACKAGES_.pth"
    if not path_file.exists() or path_file.read_text(encoding="utf-8") != content:
        path_file.write_text(content, encoding="utf-8")


def install_full_python(
    python_dir_abs_path: str, *, keep_previous: bool = False, **options
) -> None:
    """Build and probe a sibling runtime before replacing the installed directory."""
    import shutil

    from backend.DONT_CHANGE.scripts.environment_state import (
        replace_directory,
        runtime_healthy,
        stage_directory,
    )
    from backend.DONT_CHANGE.scripts.runtime_state import require_supported_architecture

    require_supported_architecture()
    destination = Path(python_dir_abs_path).resolve()
    staging = stage_directory(destination)
    try:
        _install_full_python_into_staging(str(staging), **options)
        if not runtime_healthy(
            staging / "python.exe", options.get("install_tkinter", True)
        ):
            raise RuntimeError(
                "New Python runtime failed its health check; previous runtime retained"
            )
        replace_directory(staging, destination, keep_previous=keep_previous)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _install_full_python_into_staging(
    python_dir_abs_path: str,
    python_version: str = "",
    rel_path_to_packages: str = "",
    install_tkinter: bool = True,
    install_tests: bool = True,
    install_tools: bool = True,
    install_docs: bool = False,
    print_: bool = True,
) -> None:
    r"""
    Create a local full Windows Python installation from python.org MSI files.

    The function finds the newest matching Python version in the form of:

        https://www.python.org/ftp/python/{version}/amd64/<some-file>.msi or
        https://www.python.org/ftp/python/<version>/<some-file>.amd64.msi

    It downloads the selected amd64 MSI packages, extracts them into
    ``python_dir_abs_path``, bootstraps pip through ensurepip or get-pip.py,
    and optionally writes a ``.pth`` file that adds another relative package
    directory to Python's import path if parameter rel_path_to_packages is given.

    Args:
        python_dir_abs_path: Target directory. Existing contents are deleted after a
            valid MSI set is found. Must be absolute path and raises Error otherwise.
        python_version (optional, default ""): Python version filter. Examples: ``""``, ``"3"``,
            ``"3.12"``, ``"3.12.4"``.
        rel_path_to_packages: Optional path relative to being inside ``python_dir_abs_path`` that is
            written into ``Lib/site-packages/path_to_packages.pth``. Default "" -> No path written.
        install_tkinter (optional, default True): Include Tcl/Tk support.
        install_tests (optional, default True): Include the standard library test package.
        install_tools (optional, default True): Include Python tools.
        install_docs (optional, default False): Include documentation.
        print_ (default True): Whether to print info messages

    For lower python versions (3.4-), there is no option to for example not install tkinter. It will ignore the parameter

    Raises:
        RuntimeError: If version discovery, download, extraction, or pip setup
        fails.
    """

    # ---------------------------
    # lazy imports

    import fnmatch
    import html.parser
    import re
    import shutil
    import subprocess
    import tempfile
    import urllib.error
    import urllib.parse
    import urllib.request

    # ---------------------------
    # local variables

    python_file_download_url_patterns = [  # lower index preferred
        "https://www.python.org/ftp/python/{version}/amd64/*.msi",  # python 3.5+ 64bit
        "https://www.python.org/ftp/python/{version}/*.amd64.msi",  # python 3.4- 64bit
    ]
    blacklisted_file_patterns = [
        "appendpath.msi",  # PATH modification helper, skipped because this install uses a local target directory.
        "launcher.msi",  # Global Python launcher component, skipped for this local extracted install.
        "path.msi",  # PATH modification helper, skipped because this install uses a local target directory.
        "pip.msi",  # Pip is installed later through ensurepip or get-pip.py.
        "*_d.msi",  # Debug build MSI, not the normal runtime package.
        "*_pdb.msi",  # Debug symbols MSI, not needed for normal runtime use.
        "*arm64*",  # ARM64 package, skipped because this installer uses the amd64 package directory.
        "*[0-9]rc[0-9]*",  # Release candidate, not a final release.
        "*win32*",  # 32-bit package, skipped because this installer uses the amd64 package directory.
    ]
    if not install_tkinter:
        blacklisted_file_patterns.append("tcltk.msi")  # Tkinter component disabled.
    if not install_tests:
        blacklisted_file_patterns.append("test.msi")  # Test suite component disabled.
    if not install_tools:
        blacklisted_file_patterns.append("tools.msi")  # Tools component disabled.
    if not install_docs:
        blacklisted_file_patterns.append("doc.msi")  # Documentation component disabled.
    python_exe = python_dir_abs_path + "\\python.exe"
    ruff_config = python_dir_abs_path + "\\Lib\\test\\.ruff.toml"
    python_download_timeout_s = 120
    user_agent = "install-full-python/1.0"
    downloaded_artifacts = []

    # ---------------------------
    # define helper functions

    def _find_python_version_and_download_links() -> tuple[str, str, list[str]]:
        """Find the newest requested Python release with the required Windows MSI downloads."""

        def _get_download_links_from_url(url: str) -> list[str]:
            """Fetch a Python download directory and return the links parsed from its HTML."""
            request = urllib.request.Request(url, headers={"User-Agent": user_agent})

            with urllib.request.urlopen(
                request, timeout=python_download_timeout_s
            ) as response:
                html_text = response.read().decode("utf-8", errors="replace")

            class _LinkParser(html.parser.HTMLParser):
                """Extract href values from a simple HTML directory listing."""

                def __init__(self) -> None:
                    """Initialize the HTML parser and its collected download links."""
                    super().__init__()
                    self.links: list[str] = []

                @override
                def handle_starttag(
                    self, tag: str, attrs: list[tuple[str, str | None]]
                ) -> None:
                    """Collect nonempty href values from HTML anchor tags."""
                    if tag.lower() == "a":
                        self.links.extend(
                            value
                            for name, value in attrs
                            if name.lower() == "href" and value
                        )

            parser = _LinkParser()
            parser.feed(html_text)
            return parser.links

        # define key to sort download links: prefer newest version that matches pattern
        def _version_key(version: str) -> tuple[int, int, int]:
            """Convert a three-component version string into a numeric sorting key."""
            major, minor, patch = version.split(".")
            return int(major), int(minor), int(patch)

        def _find_matching_versions() -> list[str]:
            """Find all matching version folders from the configured download URL patterns."""
            versions = set()
            errors = []
            for url_pattern in python_file_download_url_patterns:
                version_list_url = url_pattern.split("{version}", 1)[0]
                try:
                    versions.update(
                        link.strip("/")
                        for link in _get_download_links_from_url(version_list_url)
                        if target_version_pattern.match(link)
                    )
                except (OSError, urllib.error.URLError) as error:
                    errors.append(error)

            if versions:
                return sorted(versions, key=_version_key, reverse=True)
            if errors:
                raise RuntimeError(
                    f'[Error] Could not find a matching Python MSI set for parameter python_version: "{python_version}".'
                ) from errors[0]
            raise RuntimeError(
                f'[Error] No Python download URL patterns configured for parameter python_version: "{python_version}".'
            )

        def _is_wanted_file(link: str) -> bool:
            """Return whether wanted msi."""
            if link.endswith("/"):  # reject folders
                return False

            filename = os.path.basename(urllib.parse.urlparse(link).path).lower()

            # return False if filename matches any blacklisted pattern
            if any(
                fnmatch.fnmatchcase(filename.lower(), pattern)
                for pattern in blacklisted_file_patterns
            ):
                return False

            _base, extension = os.path.splitext(filename)
            if extension == ".msi":
                return True
            else:
                return False

        def _find_msi_urls_from_pattern(
            url_pattern: str, version: str
        ) -> tuple[str, list[str]]:
            """Find matching MSI URLs from a URL pattern such as .../{version}/amd64/*.msi."""
            resolved_pattern = url_pattern.format(version=version)
            folder_url, filename_pattern = resolved_pattern.rsplit("/", 1)
            folder_url += "/"
            links = _get_download_links_from_url(folder_url)
            msi_urls = []
            for link in links:
                filename = os.path.basename(urllib.parse.urlparse(link).path).lower()
                if fnmatch.fnmatchcase(
                    filename, filename_pattern.lower()
                ) and _is_wanted_file(link):
                    msi_urls.append(urllib.parse.urljoin(folder_url, link))
            return folder_url, sorted(msi_urls)

        if python_version == "":
            target_version_pattern = re.compile(r"^\d+\.\d+\.\d+/$")
        elif re.fullmatch(r"\d+", python_version):
            target_version_pattern = re.compile(
                rf"^{re.escape(python_version)}\.\d+\.\d+/$"
            )
        elif re.fullmatch(r"\d+\.\d+", python_version):
            target_version_pattern = re.compile(rf"^{re.escape(python_version)}\.\d+/$")
        elif re.fullmatch(r"\d+\.\d+\.\d+", python_version):
            target_version_pattern = re.compile(rf"^{re.escape(python_version)}/$")
        else:
            raise RuntimeError(
                f'[Error] Could not find a matching Python version pattern for parameter python_version: "{python_version}".'
            )

        # sort download links and take first working
        for version in _find_matching_versions():
            for url_pattern in python_file_download_url_patterns:
                try:
                    url, msi_urls = _find_msi_urls_from_pattern(url_pattern, version)
                except (OSError, urllib.error.URLError):
                    continue

                # return found download links and python version
                if msi_urls:
                    return version, url, msi_urls
        raise RuntimeError(
            f'[Error] Could not find msi-downloadable Python for python_version: "{python_version}".'
        )

    def _download_file_from_url(url: str, folder: str) -> str:
        """Download one installer artifact to the selected folder and return its local path."""
        filename = os.path.basename(urllib.parse.urlparse(url).path)
        output_path = os.path.join(folder, filename)

        if print_:
            print(f"Downloading {filename}")

        request = urllib.request.Request(url, headers={"User-Agent": user_agent})

        with (
            urllib.request.urlopen(
                request, timeout=python_download_timeout_s
            ) as response,
            open(output_path, "wb") as file,
        ):
            shutil.copyfileobj(response, file)

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f'Download produced an empty file: "{output_path}"')
        from backend.DONT_CHANGE.scripts.environment_state import (
            artifact_record,
            verify_python_signature,
        )

        if output_path.lower().endswith(".msi"):
            verify_python_signature(output_path)
        downloaded_artifacts.append(artifact_record(output_path, url))
        return output_path

    def _install_msi_file(msi_path: str) -> None:
        """Install one Python MSI component into the configured runtime and retain its diagnostic log."""
        msi_name = os.path.basename(msi_path)
        import uuid

        from backend.DONT_CHANGE.settings.backend_settings import TEMPORARY_DIR

        diagnostic_dir = Path(TEMPORARY_DIR) / "installation-logs"
        diagnostic_dir.mkdir(parents=True, exist_ok=True)
        log_path = str(diagnostic_dir / (uuid.uuid4().hex + "-" + msi_name + ".log"))

        if print_:
            print(f"Installing {msi_name}")

        # install msi files in python_dir_abs_path
        command = f'msiexec /a "{msi_path}" TARGETDIR="{python_dir_abs_path}" /qn /L*V "{log_path}"'
        result = subprocess.run(
            command,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"msiexec failed for {msi_name} with exit code {result.returncode}. Log: {log_path}"
            )

        if msi_name.lower() == "test.msi":
            # needed to prevent Ruff from complaining/failing for ".ruff.toml" files in Pythons "test" package/folder because this local python installation does not follow the global python source-tree layout.-> it comments out lines starting with "extend" in "Lib\test\.ruff.toml", e.g., "extend = "../.ruff.toml"."""
            if os.path.exists(ruff_config):
                lines = read_lines(ruff_config)
                lines = [
                    "# " + line if re.match(r"^\s*extend\s*=", line) else line
                    for line in lines
                ]
                write_lines(ruff_config, lines)

        # Remove any MSI copy that install left in TARGETDIR.
        copied_msi = os.path.join(python_dir_abs_path, msi_name)
        if os.path.exists(copied_msi):
            os.remove(copied_msi)

    def _install_pip(target_version: str) -> None:
        """Bootstrap pip using the best method for the installed Python version."""
        version_match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?", target_version)
        if not version_match:
            raise RuntimeError(f'Could not parse Python version "{target_version}".')

        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        patch = int(version_match.group(3) or 0)

        # Python includes ensurepip starting with 3.4 and 2.7.9.
        supports_ensurepip = (
            major > 3
            or (major == 3 and minor >= 4)
            or (major == 2 and (minor > 7 or (minor == 7 and patch >= 9)))
        )
        if supports_ensurepip:
            from backend.DONT_CHANGE.scripts.runtime_state import (
                clean_python_environment,
            )

            env = clean_python_environment()
            env["PIP_NO_WARN_SCRIPT_LOCATION"] = (
                "1"  # supress warning that pip is not global
            )
            env["PATH"] = os.pathsep.join(
                [
                    python_dir_abs_path,
                    os.path.join(python_dir_abs_path, "Scripts"),
                    env.get("PATH", ""),
                ]
            )

            result = subprocess.run(
                [python_exe, "-E", "-s", "-m", "ensurepip", "--upgrade"],
                check=False,
                env=env,
            )
            if result.returncode != 0:
                raise RuntimeError("Python installation failed: ensurepip failed.")

            return

        # Python 3.3 and older do not have ensurepip. Use PyPA's versioned
        # legacy get-pip.py bootstrapper so pip itself still supports the interpreter.
        if print_:
            print(f"Bootstrapping pip with get-pip.py for Python {target_version}")

        get_pip_urls = [
            f"https://bootstrap.pypa.io/pip/{major}.{minor}/get-pip.py",
            f"https://bootstrap.pypa.io/{major}.{minor}/get-pip.py",
        ]
        errors = []
        env = os.environ.copy()
        env["PIP_NO_WARN_SCRIPT_LOCATION"] = "1"
        env["PATH"] = os.pathsep.join(
            [
                python_dir_abs_path,
                os.path.join(python_dir_abs_path, "Scripts"),
                env.get("PATH", ""),
            ]
        )
        with tempfile.TemporaryDirectory(prefix="tmp_get_pip_") as tmp:
            for get_pip_url in get_pip_urls:
                try:
                    get_pip_path = _download_file_from_url(get_pip_url, tmp)
                    break
                except (OSError, RuntimeError, urllib.error.URLError) as error:
                    errors.append(f"{get_pip_url}: {error}")
            else:
                raise RuntimeError(
                    f"Python installation failed: could not download get-pip.py for Python {target_version}. "
                    f"Tried: {'; '.join(errors)}"
                )

            result = subprocess.run(
                [python_exe, get_pip_path, "--no-warn-script-location"],
                check=False,
                env=env,
            )

        if result.returncode != 0:
            raise RuntimeError("Python installation failed: get-pip.py failed.")

        # Verify that pip can be imported and run by the installed Python:
        result = subprocess.run([python_exe, "-m", "pip", "--version"], check=False)
        if result.returncode != 0:
            raise RuntimeError(
                "Python installation failed: pip is not available after bootstrap."
            )

    # ----------------------------
    # execute code of function

    if not os.path.isabs(python_dir_abs_path):
        raise RuntimeError(
            f'Paramter "python_dir_abs_path" must be an absolute path. Got "{python_dir_abs_path}"'
        )

    # find compatible python version and download links
    compatible_full_py_vers, download_url, msi_urls = (
        _find_python_version_and_download_links()
    )

    if print_:
        print(f"Found Python {compatible_full_py_vers} (Target: {python_version}).")
        print(f"Download URL: {download_url}")
        print(f"Found {len(msi_urls)} MSI package(s).")

    # Only delete the target after a valid MSI set has been found.
    try:
        if not delete_folder_safe(python_dir_abs_path, max_size_GB_before_prompt=1.2):
            raise RuntimeError("Python installation cancelled")
    except Exception as error:
        raise RuntimeError(
            f'[Error] Refusing to delete "{python_dir_abs_path}". {error}'
        ) from error

    # create folder
    os.makedirs(python_dir_abs_path, exist_ok=True)

    # add gitignore file
    write_lines(
        python_dir_abs_path + "\\.gitignore",
        [
            "# Prevent committing the local Python distribution.",
            "*",
        ],
    )

    # download and install msi files
    try:
        with tempfile.TemporaryDirectory(
            prefix="tmp_python_installation_files_"
        ) as tmp:
            # downlaod into temp folder
            msi_paths = [_download_file_from_url(url, tmp) for url in msi_urls]

            # install
            def msi_filename(path: str) -> str:
                """Return the lowercase MSI basename used to select and order installer components."""
                return os.path.basename(path).lower()

            for msi_path in sorted(msi_paths, key=msi_filename):
                _install_msi_file(msi_path)
    except Exception as error:
        raise RuntimeError(f"Local Python installation failed: {error}") from error

    # check if installation looks successful
    if not os.path.exists(python_exe):
        raise RuntimeError("Python installation failed: python.exe was not created.")

    # create a pip config file to stop it from complaining about not being a globally installed python
    write_lines(
        python_dir_abs_path + "\\pip.ini",
        [
            "[global]",
            "no-warn-script-location = true",
        ],
    )

    # install pip
    _install_pip(compatible_full_py_vers)

    from backend.DONT_CHANGE.scripts.runtime_state import atomic_json

    atomic_json(
        Path(python_dir_abs_path) / "installation-manifest.json",
        {
            "python": compatible_full_py_vers,
            "architecture": "amd64",
            "artifacts": downloaded_artifacts,
        },
    )

    # tell python where to look for third party packages
    if rel_path_to_packages:
        configure_python_package_path(python_dir_abs_path, rel_path_to_packages)

    if print_:
        print()
        print(
            f'Successfully created local Python {compatible_full_py_vers} at "{python_dir_abs_path}".'
        )
        print()
