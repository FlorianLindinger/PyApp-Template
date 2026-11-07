"""scripts/import_finder.py: which PyPI packages does the app import?"""

import os
import tempfile
import textwrap
import unittest
from pathlib import Path

from project_location import DONT_CHANGE

# isort: split

from backend.DONT_CHANGE.scripts import import_finder


def write(root, relative, text=""):
    path = Path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


class ScanTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = directory.name

    def test_stdlib_local_and_launcher_imports_are_excluded(self):
        write(self.root, "main.py", "import os, json, helper, requests\nfrom mypkg import x\n")
        write(self.root, "helper.py")
        write(self.root, "mypkg/__init__.py")
        write(self.root, "backend/x/launcher.py", "import launcheronly\n")
        write(self.root, "myapp/backend/server.py", "import flask\n")
        found, problems = import_finder.imports_in_project(self.root)
        self.assertEqual(problems, [])
        self.assertEqual(sorted(found), ["flask", "requests"])

    def test_optional_import_guards(self):
        write(
            self.root,
            "main.py",
            """
            try:
                import numpy
                run(numpy)
            except Exception:
                pass
            try:
                import yaml
                HAS_YAML = True
            except Exception:
                HAS_YAML = False
            try:
                import ujson
            except ImportError:
                ujson = None
            """,
        )
        found, _ = import_finder.imports_in_project(self.root)
        self.assertFalse(found["numpy"][1], "a program wrapped in try/except still requires its imports")
        self.assertTrue(found["yaml"][1])
        self.assertTrue(found["ujson"][1])

    def test_syntax_errors_are_reported_not_fatal(self):
        write(self.root, "main.py", "import requests\n")
        write(self.root, "broken.py", "def (:\n")
        found, problems = import_finder.imports_in_project(self.root)
        self.assertIn("requests", found)
        self.assertEqual(len(problems), 1)

    def test_installed_metadata_maps_import_to_distribution(self):
        site = Path(self.root, "site-packages")
        write(site, "PyYAML-6.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: PyYAML\nVersion: 6.0\n")
        write(site, "PyYAML-6.0.dist-info/top_level.txt", "yaml\n_yaml\n")
        write(site, "yaml/__init__.py")
        mapping = import_finder.installed_import_map(str(site))
        self.assertEqual(mapping.get("yaml"), "PyYAML")
        self.assertEqual(import_finder.distribution_for_import("yaml.loader", str(site)), "PyYAML")


class MappingFileTests(unittest.TestCase):
    def test_bundled_mapping_parses_and_maps_common_names(self):
        mapping = import_finder.bundled_mapping(str(DONT_CHANGE / "data" / "import_to_package.txt"))
        self.assertGreater(len(mapping), 50)
        for name in mapping:
            self.assertNotIn(" ", name)
        self.assertEqual(mapping.get("yaml", "PyYAML").lower(), "pyyaml")

    def test_later_lines_win(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "map.txt")
            Path(path).write_text("# comment\nfoo:first\nfoo:second\n", encoding="utf-8")
            self.assertEqual(import_finder.bundled_mapping(path), {"foo": "second"})


if __name__ == "__main__":
    unittest.main()
