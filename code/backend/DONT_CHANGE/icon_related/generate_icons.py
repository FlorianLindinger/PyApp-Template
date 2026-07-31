"""Generate this project's ICO files from the configured PNG assets."""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

root_dir = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + "\\..\\..\\..")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.developer_settings import (
    crash_log_sub_icon_alignment,
    crash_log_sub_icon_scale,
    crash_sub_icon_alignment,
    crash_sub_icon_scale,
    failure_sub_icon_alignment,
    failure_sub_icon_scale,
    keyboardInterrupt_sub_icon_alignment,
    keyboardInterrupt_sub_icon_scale,
    log_sub_icon_alignment,
    log_sub_icon_scale,
    open_main_py_sub_icon_alignment,
    open_main_py_sub_icon_scale,
    settings_sub_icon_alignment,
    settings_sub_icon_scale,
    stop_sub_icon_alignment,
    stop_sub_icon_scale,
    success_sub_icon_alignment,
    success_sub_icon_scale,
)
from backend.DONT_CHANGE.scripts.generic_helpers import generate_ico_from_png, get_png_image_id
from backend.DONT_CHANGE.settings.backend_settings import (
    ICON_DELETE_RETRY_DELAY_SECONDS,
    ICON_DELETE_TIMEOUT_SECONDS,
    ICON_FALLBACK_PNG_DIR,
    ICON_GENERATION_SETTINGS,
    ICON_PNG_DIR,
)

SUB_ICON_SETTINGS: dict[str, tuple[float | None, str | None]] = {
    "settings": (settings_sub_icon_scale, settings_sub_icon_alignment),
    "stop": (stop_sub_icon_scale, stop_sub_icon_alignment),
    "log": (log_sub_icon_scale, log_sub_icon_alignment),
    "success": (success_sub_icon_scale, success_sub_icon_alignment),
    "failure": (failure_sub_icon_scale, failure_sub_icon_alignment),
    "crash": (crash_sub_icon_scale, crash_sub_icon_alignment),
    "crash_log": (crash_log_sub_icon_scale, crash_log_sub_icon_alignment),
    "open_main_py": (open_main_py_sub_icon_scale, open_main_py_sub_icon_alignment),
    "keyboardInterrupt": (keyboardInterrupt_sub_icon_scale, keyboardInterrupt_sub_icon_alignment),
}


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
        icon_name = os.path.splitext(os.path.basename(output_path))[0]
        settings = SUB_ICON_SETTINGS.get(icon_name)
        if overlay_name is not None and settings is None:
            raise KeyError(f'Missing sub-icon settings for "{icon_name}" in developer_settings.py.')
        scale, alignment = settings if settings is not None else (None, None)
        overlay_path = None
        if overlay_name is not None and scale is not None and alignment is not None:
            if not isinstance(scale, (int, float)) or isinstance(scale, bool):
                raise TypeError(f'Sub-icon scale for "{icon_name}" must be a number or None.')
            if not isinstance(alignment, str):
                raise TypeError(f'Sub-icon alignment for "{icon_name}" must be a string or None.')
            overlay_path = _pick_png(overlay_name, overlay_id, overlay_fallback)
        _delete_existing_icon(output_path)
        jobs.append(
            (
                output_path,
                base_path,
                overlay_path,
                0.35 if scale is None else float(scale),
                "bottom right" if alignment is None else alignment,
            )
        )

    def generate(job: tuple[str, str, str | None, float, str]) -> str:
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
            print(f"Generated: {os.path.basename(output_path)}")


if __name__ == "__main__":
    main()
