"""actions/gen_icons.py: bundled overlays; generated icons update silently, others only after a question."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from project_location import DONT_CHANGE

# isort: split

from backend.DONT_CHANGE.actions import gen_icons


class GenIconsTests(unittest.TestCase):
    def regenerate(self, folder, answers=(), content=b"generated"):
        """Run the generator for two icons with a stand-in that writes content; return (overlays, questions)."""
        overlays = []

        def fake(output, base, overlay, sub_icon_area_scale_factor, sub_icon_alignment):
            overlays.append(overlay)
            Path(output).write_bytes(content)
            return output

        table = [
            (os.path.join(folder, name), "icon.png", None, "default_icon.png", "default_failure.png")
            for name in ("failure.ico", "success.ico")
        ]
        with mock.patch.object(gen_icons, "ICON_GENERATION_SETTINGS", table), mock.patch.object(
            gen_icons, "GENERATED_ICONS_RECORD_PATH", os.path.join(folder, "record", "icons.json")
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
