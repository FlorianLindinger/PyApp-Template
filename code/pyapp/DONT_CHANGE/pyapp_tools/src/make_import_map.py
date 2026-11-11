"""Build the template's import-name -> PyPI-name mapping from PyPI's own package files.

Writes code/pyapp/DONT_CHANGE/data/import_to_package.txt of the PyApp Template checkout. The
import finder uses it for packages that are not installed yet, when the import name differs from
the PyPI name (e.g. "import yaml" -> PyYAML, "import cv2" -> opencv-python).

How it works (standard library only, needs internet):
1. Takes the most-downloaded PyPI projects (public ranking by Hugo van Kemenade,
   https://hugovk.dev/top-pypi-packages/; only the project names are used).
2. Asks PyPI's JSON API for each project's newest wheel.
3. Reads only the wheel's ZIP directory (an HTTP range request for its last bytes, not the whole
   download) and derives the top-level import names it installs.
4. Keeps the names that differ from the project name. A name installed by several projects
   (namespace packages such as "google" or "azure") is left out unless one of them is called
   exactly like it, because a guess would often be wrong.

The result is generated from the packages themselves, so it contains no third-party mapping data.

Usage (any Python 3.8+):
    python pyapp_tools/src/make_import_map.py [--count 8000] [--workers 16] [--output FILE]
                                                 [--max-age-days 30] [--refresh]
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import HTTPMessage
from pathlib import Path
from typing import IO, Any, Callable, Dict, Iterable, List, Mapping, Optional, Set, Tuple, TypedDict

import _ui

RANKING_URLS = (
    "https://hugovk.dev/top-pypi-packages/top-pypi-packages.min.json",
    "https://hugovk.dev/top-pypi-packages/top-pypi-packages-30-days.min.json",
)
PYPI_JSON_URL = "https://pypi.org/pypi/{}/json"
USER_AGENT = "PyApp-Template-import-mapping-builder (+https://github.com/FlorianLindinger/PyApp-Template)"
# Folders and files in wheels that are not importable application packages.
IGNORED_TOP_LEVEL = {
    "tests",
    "test",
    "testing",
    "docs",
    "doc",
    "examples",
    "example",
    "benchmarks",
    "scripts",
    "src",
    "bin",
    # Generic names that unrelated projects ship as a top-level folder; in an app they are
    # almost always the app's own modules, never a hint which package to install.
    "api",
    "app",
    "client",
    "common",
    "config",
    "core",
    "data",
    "db",
    "helpers",
    "lib",
    "main",
    "models",
    "server",
    "settings",
    "tools",
    "util",
    "utils",
}
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
MODULE_SUFFIXES = (".py", ".pyi", ".pyd", ".so", ".pyc")


# A mostly failed download must not replace the existing map with a nearly empty one.
MINIMUM_COMPLETE = 0.9


def normalized(name: str) -> str:
    """PEP 503 form, also used to compare import names with project names."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _validate_download_url(url: str) -> None:
    """Only public HTTPS endpoints used by the ranking and PyPI are download sources."""
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"hugovk.dev", "pypi.org", "files.pythonhosted.org"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Import-map downloads must use the approved public HTTPS hosts.")


class _DownloadRedirectHandler(urllib.request.HTTPRedirectHandler):
    # typing.override requires Python 3.12; keep this override dependency-free on 3.8.
    def redirect_request(  # pyrefly: ignore[missing-override-decorator]
        self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage, newurl: str
    ):
        _validate_download_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 60) -> bytes:
    """GET with retries; raises urllib.error.HTTPError for 4xx answers."""
    _validate_download_url(url)
    # Both the initial URL and redirects are restricted to approved HTTPS sources.
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})  # noqa: S310
    opener = urllib.request.build_opener(_DownloadRedirectHandler())
    for attempt in range(4):
        try:
            with opener.open(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == 3:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 3:
                raise
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


# ---------------------------------------------------------------- ZIP directory of a remote wheel


def zip_member_names(read_range: Callable[[int, int], bytes], size: int) -> List[str]:
    """File names in a ZIP archive of `size` bytes; read_range(start, end) returns bytes [start, end)."""
    tail_start = max(0, size - (65536 + 22))
    tail = read_range(tail_start, size)
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise ValueError("no end-of-central-directory record")
    _sig, _disk, _cd_disk, _entries_disk, entries, cd_size, cd_offset, _comment = struct.unpack_from(
        "<4s4H2LH", tail, eocd
    )
    if cd_offset == 0xFFFFFFFF or entries == 0xFFFF:  # ZIP64
        locator = tail.rfind(b"PK\x06\x07", 0, eocd)
        if locator < 0:
            raise ValueError("ZIP64 archive without locator")
        (zip64_offset,) = struct.unpack_from("<Q", tail, locator + 8)
        record = read_range(zip64_offset, zip64_offset + 56)
        if record[:4] != b"PK\x06\x06":
            raise ValueError("bad ZIP64 end record")
        entries, cd_size, cd_offset = struct.unpack_from("<QQQ", record, 32)
    if cd_offset >= tail_start:
        directory = tail[cd_offset - tail_start : cd_offset - tail_start + cd_size]
    else:
        directory = read_range(cd_offset, cd_offset + cd_size)
    names: List[str] = []
    position = 0
    for _ in range(entries):
        if directory[position : position + 4] != b"PK\x01\x02":
            raise ValueError("bad central directory entry")
        flags = struct.unpack_from("<H", directory, position + 8)[0]
        name_length, extra_length, comment_length = struct.unpack_from("<3H", directory, position + 28)
        raw = directory[position + 46 : position + 46 + name_length]
        names.append(raw.decode("utf-8" if flags & 0x800 else "cp437", "replace"))
        position += 46 + name_length + extra_length + comment_length
    return names


def import_names(member_names: Iterable[str]) -> Set[str]:
    """Top-level importable names a wheel installs (packages, modules and extension modules)."""
    result = set()
    for name in member_names:
        parts = name.split("/")
        if parts[0].endswith(".data") and len(parts) > 2 and parts[1] in ("purelib", "platlib"):
            parts = parts[2:]  # installed into site-packages as well
        elif parts[0].endswith((".dist-info", ".data", ".egg-info")):
            continue
        if not parts or not parts[-1]:
            continue
        if len(parts) == 1:  # a module directly in site-packages
            if not parts[0].endswith(MODULE_SUFFIXES):
                continue
            top = parts[0].split(".")[0]
        else:  # a package (or namespace package) folder containing modules
            if not parts[-1].endswith(MODULE_SUFFIXES):
                continue
            top = parts[0]
        if IDENTIFIER.match(top) and not top.startswith("_") and top.lower() not in IGNORED_TOP_LEVEL:
            result.add(top)
    return result


# ---------------------------------------------------------------- PyPI


def pick_wheel(files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prefer a pure-Python wheel, then a Windows x64 wheel, then any wheel."""
    wheels = [f for f in files if f.get("packagetype") == "bdist_wheel" and not f.get("yanked")]
    for preferred in ("none-any.whl", "win_amd64.whl", ""):
        for wheel in wheels:
            if wheel["filename"].endswith(preferred):
                return wheel
    return None


def project_import_names(project: str) -> Tuple[str, Set[str]]:
    """(PyPI display name, import names of its newest wheel); empty set if it has no wheel."""
    data = json.loads(fetch(PYPI_JSON_URL.format(project)))
    wheel = pick_wheel(data.get("urls") or [])
    display_name = data.get("info", {}).get("name") or project
    if wheel is None:
        return display_name, set()

    def read_range(start: int, end: int) -> bytes:
        return fetch(wheel["url"], {"Range": f"bytes={start}-{end - 1}"})

    return display_name, import_names(zip_member_names(read_range, int(wheel["size"])))


def top_projects(count: int) -> List[str]:
    for url in RANKING_URLS:
        try:
            rows = json.loads(fetch(url))["rows"]
        except (OSError, KeyError, ValueError):
            continue
        return [row["project"] for row in rows[:count]]
    raise RuntimeError("Could not download the PyPI download ranking.")


# ---------------------------------------------------------------- main


class _CacheEntry(TypedDict, total=False):
    name: str
    imports: List[str]
    fetched: str  # ISO date the wheel was read


def _today() -> datetime.date:
    return datetime.datetime.now(datetime.timezone.utc).date()


def _is_fresh(entry: _CacheEntry, max_age_days: Optional[float]) -> bool:
    """Cached data is reused until it is max_age_days old (None: forever); it lets an interrupted run continue."""
    if max_age_days is None:
        return True
    try:
        fetched = datetime.date.fromisoformat(entry.get("fetched", ""))
    except ValueError:
        return False
    return (_today() - fetched).days < max_age_days


def fetch_dates(cache_path: Path, projects: Iterable[str]) -> Tuple[Optional[str], Optional[str]]:
    """Oldest and newest date at which the wheels of these projects were read."""
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None
    dates = sorted(cache[p]["fetched"] for p in projects if p in cache and "fetched" in cache[p])
    return (dates[0], dates[-1]) if dates else (None, None)


def build(
    projects: List[str], workers: int, cache_path: Path, max_age_days: Optional[float] = None
) -> Dict[str, List[str]]:
    """{project display name: sorted import names}, using and updating a JSON cache.

    Entries older than max_age_days are fetched again. If that fails, the old entry is kept: older
    data is better than a gap in the map.
    """
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache: Dict[str, _CacheEntry] = {}
    todo = [p for p in projects if p not in cache or not _is_fresh(cache[p], max_age_days)]
    _ui.fields([("Projects", len(projects)), ("Cached", len(projects) - len(todo)), ("To fetch", len(todo))])
    failures = 0
    cache_path.parent.mkdir(parents=True, exist_ok=True)  # also needed by the checkpoints below
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(project_import_names, project): project for project in todo}
        for done, future in enumerate(as_completed(futures), 1):
            project = futures[future]
            try:
                name, names = future.result()
                cache[project] = {"name": name, "imports": sorted(names), "fetched": _today().isoformat()}
            except Exception as error:
                failures += 1
                _ui.info(f"skipped {project}: {error}")
            _ui.progress(f"{done}/{len(todo)} fetched, {failures} skipped")
            if done % 250 == 0:
                cache_path.write_text(json.dumps(cache), encoding="utf-8")
    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    _ui.step(f"Fetched; {failures} skipped.")
    return {cache[p]["name"]: cache[p]["imports"] for p in projects if p in cache}


def mapping_lines(results: Mapping[str, Iterable[str]]) -> List[str]:
    """import:project pairs where the names differ and the import name is unambiguous."""
    providers = {}
    for project, names in results.items():
        for name in names:
            providers.setdefault(name, []).append(project)
    lines = []
    for name in sorted(providers, key=str.lower):
        projects = providers[name]
        if any(normalized(p) == normalized(name) for p in projects):
            continue  # the import name is a project name: the finder's guess is right
        if len(projects) > 1:
            continue  # namespace package or clash: no reliable answer
        lines.append(f"{name}:{projects[0]}")
    return lines


def main() -> int:
    from _paths import CODE_DIR, DONT_CHANGE_DIR

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--count",
        type=int,
        default=8000,
        help="number of most-downloaded projects (default 8000)",
    )
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument(
        "--output",
        type=Path,
        default=CODE_DIR / "pyapp/DONT_CHANGE/data/import_to_package.txt",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=DONT_CHANGE_DIR / "tmp/import_mapping_cache.json",
    )
    parser.add_argument(
        "--max-age-days",
        type=float,
        default=30.0,
        help="fetch projects again whose cached data is this old (default 30)",
    )
    parser.add_argument("--refresh", action="store_true", help="fetch every project again, ignoring the cache")
    args = parser.parse_args()

    _ui.heading("Import name map")
    _ui.step(f"Getting the {args.count} most-downloaded PyPI projects ...")
    ranking = top_projects(args.count)
    results = build(ranking, args.workers, args.cache, 0.0 if args.refresh else args.max_age_days)
    if len(results) < len(ranking) * MINIMUM_COMPLETE:
        _ui.error(
            f"Only {len(results)} of {len(ranking)} projects could be read (no internet?). "
            f"The existing map was kept; what was fetched is cached, so run this again."
        )
        return 1
    lines = mapping_lines(results)
    oldest, newest = fetch_dates(args.cache, ranking)
    read = (
        f"between {oldest} and {newest}"
        if oldest and newest and oldest != newest
        else f"on {oldest or 'unknown dates'}"
    )
    header = [
        '# Import name -> PyPI project name, one "import:project" pair per line.',
        "# Used by the offline import finder when a package is not installed yet; names that equal",
        "# their project name need no entry. Later lines win when an import name appears twice.",
        "# Add your own pairs at the end of this file.",
        "#",
        f"# Generated {datetime.datetime.now(datetime.timezone.utc).date().isoformat()} by",
        f"# DONT_CHANGE/pyapp_tools/src/make_import_map.py from the wheel file lists of the {len(ranking)}",
        "# most-downloaded PyPI projects.",
        f"# The wheel file lists were read {read}.",
    ]
    temporary = args.output.with_name(args.output.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        stream.write("\r\n".join(header + lines) + "\r\n")
    Path(temporary).replace(args.output)
    _ui.success(f'Wrote {len(lines)} pairs to "{args.output}".')
    return 0


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
