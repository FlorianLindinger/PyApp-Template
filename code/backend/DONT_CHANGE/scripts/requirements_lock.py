"""Convert exact backend pins into pip requirements with published artifact hashes."""

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


def lock_backend_requirements(source, destination):
    requirements = []
    manifest = []
    for line in Path(source).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", line)
        if not match:
            raise ValueError(
                "Backend requirements must use exact name==version pins: " + line
            )
        name, version = match.groups()
        url = "https://pypi.org/pypi/{}/{}/json".format(
            urllib.parse.quote(name), urllib.parse.quote(version)
        )
        with urllib.request.urlopen(url, timeout=60) as response:
            metadata = json.load(response)
        artifacts = [
            {
                "filename": item["filename"],
                "url": item["url"],
                "sha256": item["digests"]["sha256"],
            }
            for item in metadata["urls"]
            if not item.get("yanked", False)
        ]
        if not artifacts or not all(
            re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in artifacts
        ):
            raise ValueError("No usable published artifact hashes for " + line)
        requirements.append(
            line
            + " "
            + " ".join("--hash=sha256:" + item["sha256"] for item in artifacts)
        )
        manifest.append({"requirement": line, "artifacts": artifacts})
    Path(destination).write_text("\n".join(requirements) + "\n", encoding="utf-8")
    Path(str(destination) + ".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return str(destination)
