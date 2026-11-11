"""scripts/import_finder.py: which PyPI packages does the app import?"""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Union

from project_location import DONT_CHANGE

# isort: split

from pyapp.DONT_CHANGE.scripts import import_finder


def write(root: Union[str, Path], relative: str, text: str = ""):
    path = Path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


class ScanTests(unittest.TestCase):
    # typing.override requires Python 3.12; keep this override dependency-free on 3.8.
    def setUp(self):  # pyrefly: ignore[missing-override-decorator]
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = directory.name

    def test_stdlib_local_and_launcher_imports_are_excluded(self):
        write(
            self.root,
            "main.py",
            "import os, json, helper, requests\nfrom mypkg import x\n",
        )
        write(self.root, "helper.py")
        write(self.root, "mypkg/__init__.py")
        write(self.root, "pyapp/x/launcher.py", "import launcheronly\n")
        write(self.root, "myapp/pyapp/server.py", "import flask\n")
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
        self.assertFalse(
            found["numpy"][1],
            "a program wrapped in try/except still requires its imports",
        )
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
        write(
            site,
            "PyYAML-6.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: PyYAML\nVersion: 6.0\n",
        )
        write(site, "PyYAML-6.0.dist-info/top_level.txt", "yaml\n_yaml\n")
        write(site, "yaml/__init__.py")
        mapping = import_finder.installed_import_map(str(site))
        self.assertEqual(mapping.get("yaml"), "PyYAML")
        self.assertEqual(import_finder.distribution_for_import("yaml.loader", str(site)), "PyYAML")

    def test_local_namespace_packages_are_not_install_candidates(self):
        write(self.root, "main.py", "from local_ns.sub import module\nimport data_only\n")
        write(self.root, "local_ns/sub/module.py")  # no __init__.py anywhere, and no .py at its top
        write(self.root, "data_only/readme.txt")
        found, _ = import_finder.imports_in_project(self.root)
        self.assertEqual(sorted(found), ["data_only"])

    def install(self, site: Path, name: str, files: str):
        info = f"{name}-1.0.dist-info"
        write(
            site,
            f"{info}/METADATA",
            f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n",
        )
        write(site, f"{info}/RECORD", "".join(f"{file},,\n" for file in files.split()))
        for file in files.split():  # newer Pythons list only the RECORD entries that exist
            write(site, file)

    def test_a_shared_namespace_is_ambiguous_not_guessed(self):
        site = Path(self.root, "site-packages")
        self.install(site, "google-auth", "google/auth/__init__.py")
        self.install(site, "google-cloud-storage", "google/cloud/storage/__init__.py")
        self.install(site, "PyYAML", "yaml/__init__.py")
        self.assertEqual(
            import_finder.installed_providers(str(site))["google"],
            ["google-auth", "google-cloud-storage"],
        )
        self.assertNotIn("google", import_finder.installed_import_map(str(site)))
        self.assertEqual(import_finder.installed_import_map(str(site))["yaml"], "PyYAML")
        # A missing module of the namespace: the distribution that contains it, else no false answer.
        self.assertEqual(
            import_finder.distribution_for_import("google.cloud.storage", str(site)),
            "google-cloud-storage",
        )
        self.assertEqual(
            import_finder.distribution_for_import("google.protobuf", str(site)),
            "google",
        )

        write(self.root, "main.py", "import google.auth\nimport yaml\n")
        requirements, _ = import_finder.find_requirements(self.root, str(site))
        self.assertEqual(
            [(r.distribution, r.source) for r in requirements],
            [
                ("google-auth", "ambiguous"),
                ("google-cloud-storage", "ambiguous"),
                ("PyYAML", "installed"),
            ],
        )


class MappingFileTests(unittest.TestCase):
    def test_bundled_mapping_parses_and_maps_common_names(self):
        mapping = import_finder.bundled_mapping(str(DONT_CHANGE / "data" / "import_to_package.txt"))
        self.assertGreater(len(mapping), 50)
        for name in mapping:
            self.assertNotIn(" ", name)
        self.assertEqual(mapping.get("yaml", "PyYAML").lower(), "pyyaml")

    def test_later_lines_win(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "map.txt")
            Path(path).write_text("# comment\nfoo:first\nfoo:second\n", encoding="utf-8")
            self.assertEqual(import_finder.bundled_mapping(path), {"foo": "second"})


if __name__ == "__main__":
    unittest.main()
