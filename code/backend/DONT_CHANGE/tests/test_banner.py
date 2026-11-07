"""The app name banner: every shipped font renders, has a license entry and is accepted by validation."""

import unittest

from project_location import CODE

# isort: split

from backend.DONT_CHANGE.scripts import banner
from backend.DONT_CHANGE.scripts.config import BANNER_FONTS

FONTS = CODE / "backend" / "DONT_CHANGE" / "data" / "fonts"
LICENSE = CODE / "backend" / "DONT_CHANGE" / "LICENSE.md"


def font_file(name):
    return next(path for path in (FONTS / (name + ".flf"), FONTS / (name + ".tlf")) if path.is_file())


class BannerTests(unittest.TestCase):
    def test_every_font_renders_the_template_name(self):
        for name in BANNER_FONTS:
            with self.subTest(font=name):
                rows = banner.render("PyApp-Template 2", str(font_file(name)))
                self.assertGreaterEqual(len(rows), 3)
                self.assertTrue(all(row == row.rstrip() for row in rows))
                self.assertLess(max(map(len, rows)), 200)

    def test_missing_characters_are_left_out(self):
        path = str(font_file("future"))
        self.assertEqual(banner.render("A\u4e00B", path), banner.render("AB", path))

    def test_every_font_file_is_listed_with_its_license(self):
        text = LICENSE.read_text(encoding="utf-8")
        files = sorted(path.name for path in FONTS.iterdir())
        self.assertEqual(files, sorted(font_file(name).name for name in BANNER_FONTS))
        for name in files:
            self.assertIn("data/fonts/" + name, text)


if __name__ == "__main__":
    unittest.main()
