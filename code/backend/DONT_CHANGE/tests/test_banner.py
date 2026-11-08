"""The app name banner: the shipped font renders and has a license entry."""

import unittest

from project_location import CODE

# isort: split

from backend.DONT_CHANGE.scripts import banner

FONTS = CODE / "backend" / "DONT_CHANGE" / "data" / "fonts"
LICENSE = CODE / "backend" / "DONT_CHANGE" / "LICENSE.md"


class BannerTests(unittest.TestCase):
    def test_the_font_renders_the_template_name(self):
        rows = banner.render("PyApp-Template 2")
        self.assertGreaterEqual(len(rows), 3)
        self.assertTrue(all(row == row.rstrip() for row in rows))
        self.assertFalse(any("\x7f" in row for row in rows), "hard blanks must become spaces")
        self.assertLess(max(map(len, rows)), 200)

    def test_missing_characters_are_left_out(self):
        self.assertEqual(banner.render("A\u4e00B"), banner.render("AB"))

    def test_the_font_file_is_listed_with_its_license(self):
        self.assertEqual([path.name for path in FONTS.iterdir()], ["future.tlf"])
        self.assertIn("data/fonts/future.tlf", LICENSE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
