# ==============================
# settings

fail_message: str = "[Error] Failed to run generate_PNGs_to_be_replaced: {e}"
close_terminal_on_finish: bool = False

import os

root_dir: str = os.path.dirname(__file__) + "\\..\\..\\.."

# ==============================

try:
    # ==============================
    # import Python packages

    import os
    import sys
    from concurrent.futures import ThreadPoolExecutor

    # ==============================
    # imports from files

    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.DONT_CHANGE.scripts.common_code import input_warn, print_traceback
    from backend.DONT_CHANGE.scripts.generic_helpers import close_terminal, generate_png_with_text, get_png_image_id
    from backend.DONT_CHANGE.settings.backend_settings import (
        PNG_GENERATION_BACKGROUND_COLOR,
        PNG_GENERATION_BOLD,
        PNG_GENERATION_FONT_FAMILY,
        PNG_GENERATION_FONT_SIZE,
        PNG_GENERATION_ITEMS,
        PNG_GENERATION_MIN_FONT_SIZE,
        PNG_GENERATION_OUTPUT_DIR,
        PNG_GENERATION_PADDING,
        PNG_GENERATION_SIZE,
        PNG_GENERATION_TEXT_COLOR,
    )

    # ==============================
    # define main function

    def main() -> None:
        os.makedirs(PNG_GENERATION_OUTPUT_DIR, exist_ok=True)
        items = tuple(PNG_GENERATION_ITEMS.items())
        print(f"Generating {len(items)} PNG placeholders...", flush=True)

        def create_png(item: tuple[str, list[str]]) -> str:
            filename, lines = item
            return generate_png_with_text(
                os.path.join(PNG_GENERATION_OUTPUT_DIR, filename),
                lines,
                size=PNG_GENERATION_SIZE,
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
            input("Press enter to exit.")

    # ==============================
    # execute main function

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))
            input_warn("[Error] Press enter to exit")
        if close_terminal_on_finish:
            close_terminal()

except Exception as e:
    import traceback

    print()
    print()
    print("=" * 30)
    print(fail_message.format(e=e))
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press enter to exit")
    if close_terminal_on_finish:
        os._exit(1)
