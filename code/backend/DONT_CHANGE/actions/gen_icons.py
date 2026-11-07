"""Generate this project's ICO files from the configured PNG assets."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from backend.DONT_CHANGE.backend_settings import (
    CRASH_LOG_ICON_PATH,
    DONT_CHANGE_DIR,
    FAILURE_ICON_PATH,
    ICON_DIR,
    ICON_PATH,
    LOG_ICON_PATH,
    OPEN_MAIN_PY_ICON_PATH,
    SETTINGS_ICON_PATH,
    STOP_ICON_PATH,
    SUCCESS_ICON_PATH,
)
from backend.DONT_CHANGE.scripts.config import settings as load_settings
from backend.DONT_CHANGE.scripts.config import validate
from backend.DONT_CHANGE.scripts.console_tools import ANSI_GOOD, styled
from backend.DONT_CHANGE.scripts.image_tools import (
    generate_ico_from_png,
    get_png_image_id,
)

# fmt: off
ICON_PNG_DIR = ICON_DIR  # the project's own PNGs (replace them to change the icons)
ICON_FALLBACK_PNG_DIR = DONT_CHANGE_DIR + "\\icon_related"
ICON_DELETE_TIMEOUT_SECONDS = 2.0
ICON_DELETE_RETRY_DELAY_SECONDS = 0.05
_base = ("icon.png", "512x512:34babea5", "default_icon.png")
# IDs identify the shipped placeholder PNGs, not a developer's replacement art.
# Update an ID only when changing the corresponding shipped placeholder image.
ICON_GENERATION_SETTINGS = [
    # output ICO, base PNG, base PNG ID, fallback base PNG, overlay PNG, overlay PNG ID, fallback overlay PNG
    (ICON_PATH, *_base, None, None, None),
    (SETTINGS_ICON_PATH, *_base, "settings.png", "512x512:19c7e6d8", "default_settings.png"),
    (STOP_ICON_PATH, *_base, "stop.png", "512x512:0f35bd9e", "default_stop.png"),
    (LOG_ICON_PATH, *_base, "log.png", "512x512:66c0a178", "default_log.png"),
    (SUCCESS_ICON_PATH, *_base, "success.png", "512x512:c33e7909", "default_success.png"),
    (FAILURE_ICON_PATH, *_base, "failure.png", "512x512:93eddb87", "default_failure.png"),
    (CRASH_LOG_ICON_PATH, *_base, "crash_log.png", "512x512:99dee2ae", "default_crash_log.png"),
    (OPEN_MAIN_PY_ICON_PATH, *_base, "open_main_py.png", "512x512:3bd1b4b4", "default_open_main_py.png"),
]
# fmt: on


def _delete_existing_icon(path: str) -> None:
    """Remove one old icon, retrying transient Windows file locks."""
    deadline = time.monotonic() + ICON_DELETE_TIMEOUT_SECONDS
    while os.path.exists(path):
        try:
            os.remove(path)
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


def _pick_png(filename: str, expected_id: str | None, fallback_filename: str | None) -> str:
    """Use a changed project PNG, otherwise use its bundled replacement image."""
    project_path = os.path.join(ICON_PNG_DIR, filename)
    if os.path.isfile(project_path) and (expected_id is None or _cached_png_image_id(project_path) != expected_id):
        return project_path
    if fallback_filename is None:
        raise FileNotFoundError(f'PNG does not exist: "{project_path}"')
    fallback_path = os.path.join(ICON_FALLBACK_PNG_DIR, fallback_filename)
    if not os.path.isfile(fallback_path):
        raise FileNotFoundError(f'Fallback PNG does not exist: "{fallback_path}"')
    return fallback_path


def main() -> None:
    """Generate every enabled icon described by ``ICON_GENERATION_SETTINGS``."""
    s = load_settings()
    validate(s)
    jobs: list[tuple[str, str, str | None, float, str]] = []
    for (
        output_path,
        base_name,
        base_id,
        base_fallback,
        overlay_name,
        overlay_id,
        overlay_fallback,
    ) in ICON_GENERATION_SETTINGS:
        base_path = _pick_png(base_name, base_id, base_fallback)
        # e.g. stop.ico -> stop_sub_icon_scale / stop_sub_icon_alignment (checked by validate()).
        icon_name = os.path.splitext(os.path.basename(output_path))[0]
        scale = getattr(s, icon_name + "_sub_icon_scale", None)
        alignment = getattr(s, icon_name + "_sub_icon_alignment", None)
        overlay_path = None
        if overlay_name is not None and scale is not None and (alignment is not None):
            overlay_path = _pick_png(overlay_name, overlay_id, overlay_fallback)
        _delete_existing_icon(output_path)
        jobs.append(
            (
                output_path,
                base_path,
                overlay_path,
                0.35 if scale is None else scale,
                "bottom right" if alignment is None else alignment,
            )
        )

    def generate(job: tuple[str, str, str | None, float, str]) -> str:
        """Generate one ICO from the resolved base image, overlay and placement settings."""
        output_path, base_path, overlay_path, scale, alignment = job
        return generate_ico_from_png(
            output_path,
            base_path,
            overlay_path,
            sub_icon_area_scale_factor=scale,
            sub_icon_alignment=alignment,
        )

    with ThreadPoolExecutor(max_workers=min(4, len(jobs))) as executor:
        for output_path in executor.map(generate, jobs):
            print(f"  {styled('+', ANSI_GOOD)} {os.path.basename(output_path)}")
