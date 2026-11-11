"""Only hexadecimal color codes may reach the Windows color command."""

import unittest
from unittest import mock

import project_location  # noqa: F401 - make this checkout's code importable
from pyapp.DONT_CHANGE.backend_settings import CMD_EXE
from pyapp.DONT_CHANGE.scripts.console_tools import set_terminal_colors


class ConsoleColorTests(unittest.TestCase):
    def test_valid_colors_remain_separate_arguments(self):
        for colors in ("7", "0A", "f0"):
            with self.subTest(colors=colors), mock.patch("subprocess.run") as run:
                set_terminal_colors(colors)
                run.assert_called_once_with([CMD_EXE, "/c", "color", colors], check=False)

    def test_disabled_colors_do_not_launch_a_process(self):
        with mock.patch("subprocess.run") as run:
            set_terminal_colors(None)
            set_terminal_colors("")
            run.assert_not_called()

    def test_invalid_colors_are_rejected_without_execution(self):
        for colors in ("0A & whoami", "0A\nwhoami", "%PATH%", "123", "GG", " 0A "):
            with self.subTest(colors=colors), mock.patch("subprocess.run") as run:
                with self.assertRaises(ValueError):
                    set_terminal_colors(colors)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
