"""The shipped banner font, its character coverage and the console font it needs."""

import os
import unicodedata
import unittest
from unittest import mock

from project_location import CODE  # noqa: F401 - makes "pyapp" importable

# isort: split

from pyapp.DONT_CHANGE.scripts import banner


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


class ConsoleFontTests(unittest.TestCase):
    """The classic console has no font fallback: missing block characters would show as boxes."""

    QUADRANTS = "".join(chr(code) for code in range(0x2596, 0x25A0))

    @unittest.skipUnless(os.name == "nt", "Windows only")
    def test_the_default_console_font_lacks_the_quadrants(self):
        # Why the banner switches fonts: Consolas, the classic console's default, has no quadrants.
        if not banner.font_has_glyphs("Consolas", "A"):
            self.skipTest("Consolas is not installed")
        self.assertFalse(banner.font_has_glyphs("Consolas", self.QUADRANTS))
        self.assertFalse(banner.font_has_glyphs("No Such Font 123", "A"))  # no silent substitute

    @unittest.skipUnless(os.name == "nt", "Windows only")
    def test_a_replacement_font_has_every_block_character_of_the_banner(self):
        used = "".join(
            {character for row in banner.render("PyApp-Template") for character in row if ord(character) > 127}
        )
        installed = [face for face in banner.BLOCK_FONTS if banner.font_has_glyphs(face, "A")]
        if not installed:
            self.skipTest("no Cascadia font installed")
        self.assertTrue(all(banner.font_has_glyphs(face, used) for face in installed))

    def test_without_a_suitable_font_the_plain_banner_is_printed(self):
        settings = mock.Mock(program_name="App")
        with mock.patch.object(banner, "_shown", False), mock.patch.object(
            banner, "settings", return_value=settings
        ), mock.patch.object(banner, "console_can_show", return_value=False), mock.patch("builtins.print") as printed:
            banner.print_banner()
        self.assertEqual(printed.call_args[0][0], "App\n===\n")


if __name__ == "__main__":
    unittest.main()
