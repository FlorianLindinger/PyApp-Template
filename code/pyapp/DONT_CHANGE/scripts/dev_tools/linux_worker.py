"""Standalone Linux worker: deliberately independent of the Windows launcher imports."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional


def run(arguments: List[str], cwd: Optional[Path] = None) -> None:
    subprocess.run(arguments, cwd=cwd, check=True)  # noqa: S603 - compiler/tool argv, no shell


def build(job_path: Path) -> None:
    """Use Linux-native scratch storage; remove the build environment on every handled exit."""
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if sys.platform != "linux":
        raise RuntimeError("This worker must run inside Linux, through compile_linux.cmd.")
    missing = [tool for tool in ("gcc", "patchelf", "curl") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError("Missing " + ", ".join(missing) + "; run setup_linux.cmd first.")
    # User-owned cache, never touch the distro's system Python or Windows virtual environment.
    cache = Path.home() / ".cache" / "pyapp-compilation"
    cache.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv") or str(cache / "uv" / "uv")
    if not Path(uv).is_file():
        installer = cache / "install-uv.sh"
        run(
            [
                "curl",
                "--fail",
                "--location",
                "--proto",
                "=https",
                "--tlsv1.2",
                "https://astral.sh/uv/install.sh",
                "--output",
                str(installer),
            ]
        )
        environment = os.environ.copy()
        environment["UV_UNMANAGED_INSTALL"] = str(cache / "uv")
        subprocess.run(["/bin/sh", str(installer)], env=environment, check=True)  # noqa: S603 - official installer
    with tempfile.TemporaryDirectory(prefix="build-", dir=cache) as temporary:
        scratch = Path(temporary)
        env = scratch / "venv"
        run([uv, "venv", "--python", job["python"], "--python-preference", "only-managed", str(env)])
        python = str(env / "bin" / "python")
        dependencies = list(job["packages"])
        if job["requirements"]:
            dependencies += ["-r", job["requirements"]]
        code = Path(job["code"])
        if dependencies:
            run([uv, "pip", "install", "--python", python, *dependencies], cwd=code)
        # All packages are disposable here, so no uninstall or changes to persistent app environments.
        constraints = scratch / "app-constraints.txt"
        frozen = subprocess.run(  # noqa: S603 - fixed uv metadata query
            [uv, "pip", "freeze", "--python", python], capture_output=True, text=True, check=True
        )
        constraints.write_text(frozen.stdout, encoding="utf-8")
        run(
            [
                uv,
                "pip",
                "install",
                "--python",
                python,
                "--constraint",
                str(constraints),
                "nuitka",
                "ordered-set",
                "zstandard",
            ]
        )
        output = scratch / "output"
        output.mkdir()
        command = [
            python,
            "-m",
            "nuitka",
            "--mode=" + job["mode"],
            "--output-dir=" + str(output),
            "--report=" + str(output / "compilation-report.xml"),
            *job["extra"],
            job["script"],
        ]
        print("Linux compiler:", command, flush=True)
        destination = Path(job["output"])
        shutil.copy2(constraints, destination / "linux-requirements.txt")
        try:
            run(command, cwd=code)
            artifacts = list(output.glob("*.dist")) if job["mode"] == "standalone" else list(output.glob("*.bin"))
            if not artifacts:
                raise RuntimeError("Nuitka produced no expected application artifact.")
            name = Path(job["script"]).stem + "-linux-" + platform.machine() + ".tar.gz"
            with tarfile.open(destination / name, "w:gz") as archive:
                for artifact in artifacts:
                    archive.add(artifact, arcname=artifact.name)
            (destination / "build-info.json").write_text(
                json.dumps(
                    {
                        "platform": platform.platform(),
                        "architecture": platform.machine(),
                        "python": job["python"],
                        "mode": job["mode"],
                        "command": command,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        finally:
            report = output / "compilation-report.xml"
            if report.is_file():
                shutil.copy2(report, destination / report.name)


if __name__ == "__main__":
    build(Path(sys.argv[1]))
