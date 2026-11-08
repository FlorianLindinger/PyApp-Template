"""The shipped banner font and its character coverage."""

import unicodedata
import unittest

from project_location import CODE

# isort: split

from backend.DONT_CHANGE.scripts import banner

FONTS = CODE / "backend" / "DONT_CHANGE" / "data" / "fonts"


class BannerTests(unittest.TestCase):
    def test_the_font_renders_the_template_name(self):
        rows = banner.render("PyApp-Template 2")
        self.assertGreaterEqual(len(rows), 3)
        self.assertTrue(all(row == row.rstrip() for row in rows))
        self.assertFalse(any("\x7f" in row for row in rows), "hard blanks must become spaces")
        self.assertLessEqual(len(rows), 5)
        self.assertLess(max(map(len, rows)), 70)

    def test_missing_characters_are_left_out(self):
        self.assertEqual(banner.render("A\u4e00B"), banner.render("AB"))

    def test_the_expected_font_is_shipped(self):
        self.assertEqual(sorted(path.name for path in FONTS.iterdir()), ["pyapp-grid.tlf"])

    def test_printable_ascii_latin1_and_german_have_visible_glyphs(self):
        glyphs = banner.load_font()
        for char in "".join(map(chr, range(33, 127))) + "".join(map(chr, range(161, 256))) + "ẞ€„“”‚‘’–—…":
            with self.subTest(character=char):
                self.assertIn(char, glyphs)
                self.assertTrue(any(row.strip() for row in glyphs[char]))
                self.assertEqual(len(glyphs[char]), 6)
                self.assertEqual(len({len(row) for row in glyphs[char]}), 1)

    def test_case_and_sharp_s_are_distinct(self):
        glyphs = banner.load_font()
        for upper, lower in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜẞ", "abcdefghijklmnopqrstuvwxyzäöüß"):
            with self.subTest(character=upper):
                self.assertNotEqual(glyphs[upper], glyphs[lower])

    def test_decomposed_german_accents_render_like_precomposed_text(self):
        text = "Grüße ÄÖÜ äöü"
        self.assertEqual(banner.render(text), banner.render(unicodedata.normalize("NFD", text)))


if __name__ == "__main__":
    unittest.main()
