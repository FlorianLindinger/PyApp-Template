"""Generate this project's ICO files from the configured PNG assets."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.DONT_CHANGE.backend_settings import (
    CRASH_LOG_ICON_PATH,
    DEFAULT_ICON_DIR,
    FAILURE_ICON_PATH,
    GENERATED_ICONS_RECORD_PATH,
    ICON_DIR,
    ICON_PATH,
    LOG_ICON_PATH,
    OPEN_CODE_ICON_PATH,
    SETTINGS_ICON_PATH,
    STOP_ICON_PATH,
    SUB_ICONS,
    SUCCESS_ICON_PATH,
)
from backend.DONT_CHANGE.scripts.config import settings as load_settings
from backend.DONT_CHANGE.scripts.config import validate
from backend.DONT_CHANGE.scripts.console_tools import ANSI_DIM, ANSI_GOOD, ask, styled
from backend.DONT_CHANGE.scripts.image_tools import (
    generate_ico_from_png,
    get_png_image_id,
)

# fmt: off
ICON_PNG_DIR = ICON_DIR  # the project's own icon.png (replace it to change the icons)
ICON_FALLBACK_PNG_DIR = DEFAULT_ICON_DIR
ICON_DELETE_TIMEOUT_SECONDS = 2.0
ICON_DELETE_RETRY_DELAY_SECONDS = 0.05
_base = ("icon.png", "512x512:34babea5", "default_icon.png")
# The ID identifies the shipped placeholder icon.png, not a developer's replacement art.
# Update it only when changing the shipped placeholder image.
ICON_GENERATION_SETTINGS = [
    # output ICO, base PNG, base PNG ID, fallback base PNG, bundled overlay PNG
    (ICON_PATH, *_base, None),
    (SETTINGS_ICON_PATH, *_base, "default_settings.png"),
    (STOP_ICON_PATH, *_base, "default_stop.png"),
    (LOG_ICON_PATH, *_base, "default_log.png"),
    (SUCCESS_ICON_PATH, *_base, "default_success.png"),
    (FAILURE_ICON_PATH, *_base, "default_failure.png"),
    (CRASH_LOG_ICON_PATH, *_base, "default_crash_log.png"),
    (OPEN_CODE_ICON_PATH, *_base, "default_open_code.png"),
]
# fmt: on


def _delete_existing_icon(path: str) -> None:
    """Remove one old icon, retrying transient Windows file locks."""
    deadline = time.monotonic() + ICON_DELETE_TIMEOUT_SECONDS
    while Path(path).exists():
        try:
            Path(path).unlink()
        except FileNotFoundError:
            return
        except OSError as error:
            if time.monotonic() >= deadline:
                raise RuntimeError(f'Could not delete existing icon "{path}": {error}') from error
            time.sleep(ICON_DELETE_RETRY_DELAY_SECONDS)


@lru_cache(maxsize=None)
def _cached_png_image_id(path: str) -> str:
    """Return the cached PNG identifier used to recognize unchanged source assets."""
    return get_png_image_id(path)


def _pick_png(filename: str, expected_id: Optional[str], fallback_filename: Optional[str]) -> str:
    """Use a changed project PNG, otherwise use its bundled replacement image."""
    project_path = str(Path(ICON_PNG_DIR) / filename)
    if Path(project_path).is_file() and (expected_id is None or _cached_png_image_id(project_path) != expected_id):
        return project_path
    if fallback_filename is None:
        raise FileNotFoundError(f'PNG does not exist: "{project_path}"')
    fallback_path = str(Path(ICON_FALLBACK_PNG_DIR) / fallback_filename)
    if not Path(fallback_path).is_file():
        raise FileNotFoundError(f'Fallback PNG does not exist: "{fallback_path}"')
    return fallback_path


def _file_hash(path: str) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def _read_record() -> Dict[str, str]:
    """{ICO file name: hash of the file the generator last installed}."""
    try:
        with Path(GENERATED_ICONS_RECORD_PATH).open(encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError):
        return {}


def _write_record(record: Dict[str, str]) -> None:
    (Path(GENERATED_ICONS_RECORD_PATH).parent).mkdir(parents=True, exist_ok=True)
    with Path(GENERATED_ICONS_RECORD_PATH).open("w", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")


def _may_replace(output_path: str) -> bool:
    """Ask before overwriting an ICO the generator did not make."""
    question = f"{Path(output_path).name} was not made by the generator, so it may be your own. Replace it? [y/N]"
    try:
        return ask(question).strip().lower() in ("y", "yes", "j", "ja")
    except EOFError:
        return False


def _install(output_path: str, built_path: str, record: Dict[str, str]) -> None:
    """Put a freshly built ICO in place: generated ones update silently, others only when the user agrees."""
    name = Path(output_path).name
    built = _file_hash(built_path)
    if Path(output_path).is_file():
        current = _file_hash(output_path)
        if current == built:
            record[name] = built
            print(f"  {styled('=', ANSI_DIM)} {name} (unchanged)")
            return
        if current != record.get(name) and not _may_replace(output_path):
            print(f"  {styled('=', ANSI_DIM)} {name} (kept)")
            return
    _delete_existing_icon(output_path)
    shutil.copyfile(built_path, output_path)
    record[name] = built
    print(f"  {styled('+', ANSI_GOOD)} {name}")


def main() -> None:
    """Build the icons in ``ICON_GENERATION_SETTINGS`` in a temporary folder, then install them one by one."""
    validate(load_settings())
    record = _read_record()
    with tempfile.TemporaryDirectory() as folder:
        jobs: List[Tuple[str, str, str, Optional[str], float, str]] = []
        for output_path, base_name, base_id, base_fallback, overlay_name in ICON_GENERATION_SETTINGS:
            base_path = _pick_png(base_name, base_id, base_fallback)
            # e.g. stop.ico -> SUB_ICONS["stop"]
            placement = SUB_ICONS.get(Path(output_path).stem)
            overlay_path = None
            if overlay_name is not None and placement is not None:
                overlay_path = str(Path(ICON_FALLBACK_PNG_DIR) / overlay_name)
                if not Path(overlay_path).is_file():
                    raise FileNotFoundError(f'Bundled overlay PNG does not exist: "{overlay_path}"')
            scale, alignment = placement or (0.35, "bottom right")
            built_path = str(Path(folder) / Path(output_path).name)
            jobs.append((output_path, built_path, base_path, overlay_path, scale, alignment))

        def generate(job: Tuple[str, str, str, Optional[str], float, str]) -> str:
            """Build one ICO from the resolved base image, overlay and placement settings."""
            _, built_path, base_path, overlay_path, scale, alignment = job
            return generate_ico_from_png(
                built_path,
                base_path,
                overlay_path,
                sub_icon_area_scale_factor=scale,
                sub_icon_alignment=alignment,
            )

        with ThreadPoolExecutor(max_workers=max(1, min(4, len(jobs)))) as executor:
            list(executor.map(generate, jobs))
        # One at a time, in order: this may ask questions.
        try:
            for output_path, built_path, *_ in jobs:
                _install(output_path, built_path, record)
        finally:
            _write_record(record)
