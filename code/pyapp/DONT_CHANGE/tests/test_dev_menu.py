"""The dev tools menu offers every command exactly once."""

import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import project_location  # noqa: F401 - make this checkout's code importable
from pyapp.DONT_CHANGE.scripts.dev_tools import main as dev_tools


class MenuTests(unittest.TestCase):
    def test_every_command_is_in_the_menu_once(self):
        names = [name for _, group in dev_tools.MENU_GROUPS for name in group]
        self.assertEqual(sorted(names), sorted(dev_tools.COMMANDS))

    def test_headings_belong_to_commands(self):
        self.assertLessEqual(set(dev_tools.HEADINGS), set(dev_tools.COMMANDS))


class SelfContainedTests(unittest.TestCase):
    def test_status_tells_whether_everything_is_inside_the_folder(self):
        from pyapp.DONT_CHANGE.scripts.dev_tools import self_contained

        local = types.SimpleNamespace(**self_contained.SELF_CONTAINED_SETTINGS)
        shared = types.SimpleNamespace(**{**self_contained.SELF_CONTAINED_SETTINGS, "python_source": "uv_user"})
        with tempfile.TemporaryDirectory() as folder:
            uv = Path(folder) / "uv" / "uv.exe"
            pythons = Path(folder) / "pythons"
            uv.parent.mkdir()
            uv.touch()
            config = {"home": str(pythons / "cpython-3.14" / "")}
            with mock.patch.multiple(
                self_contained.paths, LOCAL_UV_EXE=str(uv), LOCAL_PYTHONS_DIR=str(pythons)
            ), mock.patch.object(self_contained, "read_venv_config", return_value=config):
                self.assertTrue(self_contained.is_self_contained(local))
                self.assertFalse(self_contained.is_self_contained(shared))
                config["home"] = "C:/Users/x/AppData/Roaming/uv/python/cpython-3.14"  # the shared Python
                self.assertFalse(self_contained.is_self_contained(local))


if __name__ == "__main__":
    unittest.main()
