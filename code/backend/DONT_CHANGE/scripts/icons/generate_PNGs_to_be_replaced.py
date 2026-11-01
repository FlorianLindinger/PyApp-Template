# ruff: noqa: E402
# The early __main__ handoff lets the shared runner catch dependency import failures.

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

fail_message: str = "[Error] Failed to run generate_PNGs_to_be_replaced: {e}"
close_terminal_on_finish: bool = False
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from backend.DONT_CHANGE.scripts.image_tools import (
    generate_png_with_text,
    get_png_image_id,
)
from backend.DONT_CHANGE.settings.backend_settings import (
    PNG_GENERATION_BACKGROUND_COLOR,
    PNG_GENERATION_BOLD,
    PNG_GENERATION_FONT_FAMILY,
    PNG_GENERATION_FONT_SIZE,
    PNG_GENERATION_HEIGHT,
    PNG_GENERATION_ITEMS,
    PNG_GENERATION_MIN_FONT_SIZE,
    PNG_GENERATION_OUTPUT_DIR,
    PNG_GENERATION_PADDING,
    PNG_GENERATION_TEXT_COLOR,
    PNG_GENERATION_WIDTH,
)


def main() -> None:
    os.makedirs(PNG_GENERATION_OUTPUT_DIR, exist_ok=True)
    items = tuple(PNG_GENERATION_ITEMS.items())
    print(f"Generating {len(items)} PNG placeholders...", flush=True)

    def create_png(item: tuple[str, list[str]]) -> str:
        filename, lines = item
        return generate_png_with_text(
            os.path.join(PNG_GENERATION_OUTPUT_DIR, filename),
            lines,
            width=PNG_GENERATION_WIDTH,
            height=PNG_GENERATION_HEIGHT,
            font_family=PNG_GENERATION_FONT_FAMILY,
            font_size=PNG_GENERATION_FONT_SIZE,
            min_font_size=PNG_GENERATION_MIN_FONT_SIZE,
            bold=PNG_GENERATION_BOLD,
            padding=PNG_GENERATION_PADDING,
            text_color=PNG_GENERATION_TEXT_COLOR,
            background_color=PNG_GENERATION_BACKGROUND_COLOR,
        )

    with ThreadPoolExecutor(max_workers=min(4, len(items))) as executor:
        created_paths = list(executor.map(create_png, items))
    print(f"Created: {', '.join(PNG_GENERATION_ITEMS)}")
    print("Image IDs:")
    with ThreadPoolExecutor(max_workers=min(4, len(created_paths))) as executor:
        image_ids = executor.map(get_png_image_id, created_paths)
        for path, image_id in zip(created_paths, image_ids):
            print(f"  {os.path.basename(path)}: {image_id}")
    if sys.stdin.isatty() and sys.stdout.isatty():
        print()
