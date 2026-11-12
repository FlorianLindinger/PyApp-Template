"""actions/gen_icons.py: bundled overlays; generated icons update silently, others only after a question."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Iterable, Optional, Union
from unittest import mock

from project_location import DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE.actions import gen_icons


class GenIconsTests(unittest.TestCase):
    def regenerate(self, folder: str, answers: Iterable[Union[str, BaseException]] = (), content: bytes = b"generated"):
        """Run the generator for two icons with a stand-in that writes content; return (overlays, questions)."""
        overlays = []

        def fake(
            output: str,
            base: str,
            overlay: Optional[str],
            sub_icon_area_scale_factor: float,
            sub_icon_alignment: str,
            size_png_paths: Optional[Dict[int, str]] = None,
        ):
            overlays.append(overlay)
            Path(output).write_bytes(content)
            return output

        table = [
            (str(Path(folder) / name), "icon.png", None, "default_icon.png", "default_failure.png")
            for name in ("failure.ico", "success.ico")
        ]
        with mock.patch.object(gen_icons, "ICON_GENERATION_SETTINGS", table), mock.patch.object(
            gen_icons, "GENERATED_ICONS_RECORD_PATH", str(Path(folder) / "record" / "icons.json")
        ), mock.patch.object(gen_icons, "generate_ico_from_png", fake), mock.patch.object(
            gen_icons, "_pick_png", return_value="base.png"
        ), mock.patch.object(gen_icons, "validate"), mock.patch.object(gen_icons, "load_settings"), mock.patch.object(
            gen_icons, "ask", side_effect=list(answers)
        ) as ask, mock.patch("builtins.print"):
            gen_icons.main()
        return overlays, ask.call_count

    def test_overlay_is_always_the_bundled_one(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "failure.png").write_bytes(b"not used")
            overlays, _ = self.regenerate(folder)
        self.assertEqual(set(overlays), {str(DONT_CHANGE / "data" / "icons" / "default_failure.png")})

    def test_generated_icons_update_without_a_question(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.regenerate(folder)[1], 0)
            self.assertEqual(self.regenerate(folder)[1], 0)
            self.assertEqual(self.regenerate(folder, content=b"new base image")[1], 0)
            self.assertEqual(Path(folder, "failure.ico").read_bytes(), b"new base image")
            record = json.loads(Path(folder, "record", "icons.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(record), ["failure.ico", "success.ico"])

    def test_each_placed_icon_gets_its_own_question(self):
        with tempfile.TemporaryDirectory() as folder:
            self.regenerate(folder)
            failure, success = Path(folder, "failure.ico"), Path(folder, "success.ico")
            failure.write_bytes(b"mine")
            success.write_bytes(b"also mine")
            self.assertEqual(self.regenerate(folder, ["n", "y"])[1], 2)
            self.assertEqual(failure.read_bytes(), b"mine")
            self.assertEqual(success.read_bytes(), b"generated")

    def test_placed_icon_is_still_asked_about_after_the_base_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            self.regenerate(folder)
            failure = Path(folder, "failure.ico")
            failure.write_bytes(b"mine")
            self.assertEqual(self.regenerate(folder, ["n"], content=b"new base image")[1], 1)
            self.assertEqual(failure.read_bytes(), b"mine")
            self.assertEqual(Path(folder, "success.ico").read_bytes(), b"new base image")

    def test_no_answer_keeps_the_icon(self):
        with tempfile.TemporaryDirectory() as folder:
            self.regenerate(folder)
            failure = Path(folder, "failure.ico")
            failure.write_bytes(b"mine")
            self.regenerate(folder, [EOFError()])
            self.assertEqual(failure.read_bytes(), b"mine")


if __name__ == "__main__":
    unittest.main()


class SizeIconTests(unittest.TestCase):
    """icon_32x32_optional.png / icon_16x16_optional.png: images for single sizes."""

    TEMPLATE_BASE = str(Path(gen_icons.ICON_FALLBACK_PNG_DIR) / "default_icon.png")

    def pick(self, own: Iterable[str], base: str, template_files: Iterable[str] = ()) -> Dict[int, str]:
        """{size: file name} picked with the given files of your own and unchanged template files."""
        ids = {name: "own-" + name for name in own}
        ids.update({name: template_id for _, name, template_id, _ in gen_icons.SIZE_PNGS if name in template_files})
        with tempfile.TemporaryDirectory() as folder:
            for name in ids:
                (Path(folder) / name).write_bytes(b"")

            def image_id(path: str) -> str:
                return ids[Path(path).name]

            with mock.patch.object(gen_icons, "ICON_PNG_DIR", folder), mock.patch.object(
                gen_icons, "_cached_png_image_id", image_id
            ):
                return {size: Path(path).name for size, path in gen_icons._pick_size_pngs(base).items()}

    def test_your_own_size_images_are_used(self):
        own = ["icon_32x32_optional.png", "icon_16x16_optional.png"]
        self.assertEqual(
            self.pick(own, "custom/icon.png"), {32: "icon_32x32_optional.png", 16: "icon_16x16_optional.png"}
        )

    def test_a_32x32_image_alone_also_serves_16_px(self):
        self.assertEqual(
            self.pick(["icon_32x32_optional.png"], "custom/icon.png"),
            {32: "icon_32x32_optional.png", 16: "icon_32x32_optional.png"},
        )

    def test_the_templates_small_images_never_go_with_your_own_icon(self):
        template = [name for _, name, _, _ in gen_icons.SIZE_PNGS]
        self.assertEqual(self.pick([], "custom/icon.png", template), {})
        # With the template's icon.png they are used (the bundled copies).
        self.assertEqual(
            self.pick([], self.TEMPLATE_BASE, template), {32: "default_icon_32x32.png", 16: "default_icon_16x16.png"}
        )

    def test_the_shipped_images_are_the_templates(self):
        from pyapp.DONT_CHANGE.scripts.image_tools import get_png_image_id

        for size, name, template_id, bundled in gen_icons.SIZE_PNGS:
            for path in (DONT_CHANGE.parent / "icons" / name, DONT_CHANGE / "data" / "icons" / bundled):
                self.assertEqual(get_png_image_id(str(path)), template_id, path)
                self.assertTrue(template_id.startswith(f"{size}x{size}:"))
