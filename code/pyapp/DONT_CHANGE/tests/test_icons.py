"""actions/gen_icons.py: bundled overlays; generated icons update silently, others only after a question."""

from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path
from typing import Iterable, Optional, Union
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
        ):
            overlays.append(overlay)
            Path(output).write_bytes(content)
            return output

        table = [
            (str(Path(folder) / name), "icon.png", None, "default_icon.png", "failure.png")
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
        self.assertEqual(set(overlays), {str(DONT_CHANGE / "data" / "icons" / "failure.png")})

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


class SmallSizeFinishingTests(unittest.TestCase):
    """Small sizes: averaged in linear light, sharpened, written as PNG without an image library."""

    def test_averaging_happens_in_linear_light(self):
        from pyapp.DONT_CHANGE.scripts import image_tools

        # One output pixel from 2 x 2 source pixels: two white, two black (premultiplied BGRA, opaque).
        white, black = bytes([255, 255, 255, 255]), bytes([0, 0, 0, 255])
        ((red, green, blue, alpha),) = image_tools._shrink_in_linear_light(white + black + black + white, 1, 2)
        # Half the light is sRGB 0.735 (188/255), not 0.5: plain averaging would make thin lines too dark.
        self.assertAlmostEqual(red, 0.7354, places=3)
        self.assertEqual((red, alpha), (green, 1.0))
        self.assertEqual(blue, red)

    def test_transparent_pixels_do_not_darken_the_average(self):
        from pyapp.DONT_CHANGE.scripts import image_tools

        white, clear = bytes([255, 255, 255, 255]), bytes([0, 0, 0, 0])
        ((red, _, _, alpha),) = image_tools._shrink_in_linear_light(white + clear + clear + clear, 1, 2)
        self.assertEqual((round(red, 6), alpha), (1.0, 0.25))

    def test_sharpening_keeps_values_in_range_and_skips_large_sizes(self):
        from pyapp.DONT_CHANGE.scripts import image_tools

        pixels = [(1.0, 1.0, 1.0, 1.0) if index % 2 else (0.0, 0.0, 0.0, 1.0) for index in range(16)]
        sharpened = image_tools._sharpen(pixels, 4, 0.6)
        self.assertTrue(all(0.0 <= channel <= 1.0 for pixel in sharpened for channel in pixel))
        self.assertIs(image_tools._sharpen(pixels, 4, 0.0), pixels)

    def test_the_png_is_valid(self):
        import zlib

        from pyapp.DONT_CHANGE.scripts import image_tools

        png = image_tools._png_rgba(2, [(1.0, 0.0, 0.0, 1.0)] * 4)
        self.assertTrue(png.startswith(bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])))
        self.assertEqual(struct.unpack(">II", png[16:24]), (2, 2))
        length = struct.unpack(">I", png[33:37])[0]
        self.assertEqual(zlib.decompress(png[41 : 41 + length]), bytes([0, 255, 0, 0, 255, 255, 0, 0, 255] * 2))


class IcoSizeTests(unittest.TestCase):
    def test_every_ico_has_all_sizes_including_24_px(self):
        """24 px is what Windows shows at 125 % display scaling; without it, 32 px is shrunk."""
        from pyapp.DONT_CHANGE.scripts.image_tools import generate_ico_from_png

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "icon.ico"
            generate_ico_from_png(str(output), str(DONT_CHANGE / "data" / "icons" / "default_icon.png"))
            data = output.read_bytes()
        self.assertEqual(struct.unpack_from("<HHH", data), (0, 1, 7))
        for index, size in enumerate((256, 128, 64, 48, 32, 24, 16)):
            entry = struct.unpack_from("<BBBBHHII", data, 6 + index * 16)
            self.assertEqual(entry[:2], (size % 256, size % 256))
            self.assertEqual(struct.unpack_from(">II", data, entry[-1] + 16), (size, size))


if __name__ == "__main__":
    unittest.main()
