"""The dev tools menu offers every command exactly once."""

import unittest

import project_location  # noqa: F401 - make this checkout's code importable
from backend.DONT_CHANGE.scripts import dev_tools


class MenuTests(unittest.TestCase):
    def test_every_command_is_in_the_menu_once(self):
        names = [name for _, group in dev_tools.MENU_GROUPS for name in group]
        self.assertEqual(sorted(names), sorted(dev_tools.COMMANDS))

    def test_headings_belong_to_commands(self):
        self.assertLessEqual(set(dev_tools.HEADINGS), set(dev_tools.COMMANDS))


if __name__ == "__main__":
    unittest.main()
