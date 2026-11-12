"""Only hexadecimal color codes may reach the Windows color command."""

import unittest
from typing import List
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


class OutcomeColorTests(unittest.TestCase):
    """A window that stays open after a traceback turns black, so the colored report stays readable."""

    def colors_after(self, outcome: str) -> List[str]:
        from types import SimpleNamespace

        from pyapp.DONT_CHANGE.runtime import process_exit

        s = SimpleNamespace(
            program_name="App",
            **{
                "close_after_" + outcome: False,
                "open_log_file_after_" + outcome: False,
                "play_sound_after_" + outcome: False,
            },
        )
        with mock.patch.multiple(
            process_exit,
            settings=mock.Mock(return_value=s),
            set_terminal_title=mock.DEFAULT,
            set_terminal_icon=mock.DEFAULT,
            set_terminal_colors=mock.DEFAULT,
            print_report=mock.DEFAULT,
            write_crash_log=mock.Mock(return_value=None),
            wait_for_enter=mock.DEFAULT,
        ) as patched:
            process_exit.complete(outcome, None)
        return [call.args[0] for call in patched["set_terminal_colors"].call_args_list]

    def test_failure_and_ctrl_c_turn_the_window_black(self):
        self.assertEqual(self.colors_after("failure"), ["0F"])
        self.assertEqual(self.colors_after("keyboard_interrupt"), ["0F"])

    def test_success_keeps_the_colors(self):
        self.assertEqual(self.colors_after("success"), [])
