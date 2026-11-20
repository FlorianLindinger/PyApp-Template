"""Example tests of the app. Run them with run_all_tests.cmd in this folder.

Files named test_*.py with unittest.TestCase classes are found automatically (pytest, if added
with add_packages, runs them too). Import your own modules as main.py does, e.g.
`from mypackage import calc`, but avoid importing a script that starts the app when imported.
"""

import py_compile
import unittest
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]  # the code folder


class ExampleTests(unittest.TestCase):
    def test_every_python_file_compiles(self):
        # Finds syntax errors also in files a quick start never imports. Compiling runs nothing.
        for path in CODE.rglob("*.py"):
            if "pyapp" in path.relative_to(CODE).parts:
                continue  # the launcher and the generated environment are not the app
            with self.subTest(file=str(path.relative_to(CODE))):
                py_compile.compile(str(path), doraise=True)


if __name__ == "__main__":
    unittest.main()
