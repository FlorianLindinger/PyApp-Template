"""Transactional managed directories and inspectable installation manifests."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.DONT_CHANGE.scripts.runtime_state import (
    atomic_json,
    clean_python_environment,
)


def replace_directory(staged, destination, keep_previous=False):
    """Commit a sibling staging folder, restoring the previous directory on failure."""
    staged, destination = Path(staged).resolve(), Path(destination).resolve()
    if staged.parent != destination.parent or staged == destination:
        raise ValueError("Staging must be a distinct sibling of the destination")
    if (
        staged.is_symlink()
        or destination.is_symlink()
        or staged.is_junction()
        or destination.is_junction()
    ):
        raise ValueError("Refusing to replace a linked environment directory")
    backup = destination.with_name(destination.name + ".previous")
    if backup.exists():
        raise RuntimeError(
            "A previous environment backup remains; inspect it before retrying: "
            + str(backup)
        )
    had_destination = destination.exists()
    if had_destination:
        destination.rename(backup)
    try:
        staged.rename(destination)
    except BaseException:
        if had_destination:
            backup.rename(destination)
        raise
    if had_destination and not keep_previous:
        try:
            shutil.rmtree(backup)
        except OSError:
            # A completed replacement is usable; retain locked files for inspection.
            print("[Warning] Previous environment retained at " + str(backup))


def requirements_fingerprint(path, seen=None):
    """Include nested local -r/-c files; no network lookups while checking state."""
    path = Path(path).resolve()
    seen = set() if seen is None else seen
    if path in seen:
        return "cycle"
    seen.add(path)
    import re

    # Git/Windows checkout line endings must not invalidate a committed lock.
    content = path.read_text(encoding="utf-8-sig")
    digest = hashlib.sha256(content.encode("utf-8"))
    for line in content.splitlines():
        line = line.strip()
        match = re.match(
            r"^(?:--(?:requirement|constraint)(?:\s+|=)|-[rc]\s*)(.+)$", line
        )
        if not match:
            continue
        nested = match.group(1).strip()
        if nested.startswith(('"', "'")):
            quote = nested[0]
            end = nested.find(quote, 1)
            if end < 0:
                raise ValueError("Unclosed quote in requirements include: " + line)
            nested = nested[1:end]
        else:
            nested = re.split(r"\s+#", nested, maxsplit=1)[0].strip()
        if "://" in nested:
            raise ValueError(
                "Use local requirement includes for reproducible startup: " + nested
            )
        digest.update(requirements_fingerprint(path.parent / nested, seen).encode())
    return digest.hexdigest()


def runtime_healthy(executable, tkinter=False):
    modules = "import sys, ssl, sqlite3, ctypes, encodings, pip"
    if tkinter:
        modules += ", tkinter"
    try:
        result = subprocess.run(
            [
                str(executable),
                "-E",
                "-s",
                "-c",
                modules + "; print(sys.version.split()[0])",
            ],
            env=clean_python_environment(),
            capture_output=True,
            text=True,
            timeout=20,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def package_inventory(directory):
    """Record installed metadata and payload existence, without importing user code."""
    directory = Path(directory).resolve()
    result = {}
    for info in sorted(directory.glob("*.dist-info")):
        for name in ("METADATA", "RECORD"):
            metadata = info / name
            if not metadata.is_file():
                raise ValueError("Incomplete package metadata: " + str(metadata))
            result[str(metadata.relative_to(directory))] = hashlib.sha256(
                metadata.read_bytes()
            ).hexdigest()
    return result


def package_payloads_present(directory):
    directory = Path(directory).resolve()
    for record in directory.glob("*.dist-info/RECORD"):
        with record.open(encoding="utf-8", newline="") as stream:
            for row in csv.reader(stream):
                if not row:
                    continue
                candidate = (directory / row[0]).resolve()
                # pip target entry points may live outside the package directory.
                if directory not in candidate.parents or candidate.suffix == ".pyc":
                    continue
                if not candidate.exists():
                    return False
    return True


def write_package_state(directory, marker_name, requirements, python_version):
    atomic_json(
        Path(directory) / marker_name,
        {
            "schema": 1,
            "requirements": requirements_fingerprint(requirements),
            "python": python_version,
            "packages": package_inventory(directory),
        },
    )


def packages_healthy(directory, marker_name, requirements, python_version):
    try:
        state = json.loads((Path(directory) / marker_name).read_text(encoding="utf-8"))
        return (
            state["schema"] == 1
            and state["requirements"] == requirements_fingerprint(requirements)
            and state["python"] == python_version
            and state["packages"] == package_inventory(directory)
            and package_payloads_present(directory)
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def stage_directory(destination):
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent)
    )


def verify_python_signature(path):
    """Require a Windows-trusted Python Software Foundation Authenticode signature."""
    env = os.environ.copy()
    env["PYAPP_VERIFY_ARTIFACT"] = str(Path(path).resolve())
    command = "$s=Get-AuthenticodeSignature -LiteralPath $env:PYAPP_VERIFY_ARTIFACT; if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Python Software Foundation') { throw 'Invalid Python publisher signature' }"
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        env=env,
        check=True,
        timeout=120,
    )


def artifact_record(path, url):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"url": url, "sha256": digest.hexdigest(), "filename": Path(path).name}
