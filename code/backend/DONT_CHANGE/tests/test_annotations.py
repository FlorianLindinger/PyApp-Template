"""Annotations remain inspectable at runtime, including on the oldest supported Python."""

import ast
import importlib
import inspect
import sys
import typing
import unittest
from unittest import mock

from project_location import DONT_CHANGE


class AnnotationTests(unittest.TestCase):
    def test_runtime_type_hints(self):
        modules = (
            "backend.developer_settings",
            "backend.DONT_CHANGE.scripts.banner",
            "backend.DONT_CHANGE.scripts.config",
            "backend.DONT_CHANGE.scripts.com_tools",
            "backend.DONT_CHANGE.scripts.shortcuts",
            "backend.DONT_CHANGE.scripts.env.pyproject",
            "backend.DONT_CHANGE.scripts.env.uv",
            "backend.DONT_CHANGE.scripts.tools.make_import_map",
            "backend.DONT_CHANGE.scripts.tools.get_startup_time",
            "backend.DONT_CHANGE.runtime._pyapp",
            "backend.DONT_CHANGE.runtime.script_wrapper",
        )
        # Standalone tools and the wrapper also import helpers from their own folders.
        paths = [str(DONT_CHANGE / "scripts" / "tools"), str(DONT_CHANGE / "runtime"), *sys.path]
        with mock.patch.object(sys, "path", paths):
            for name in modules:
                module = importlib.import_module(name)
                with self.subTest(module=name):
                    typing.get_type_hints(module)
                for member_name, member in vars(module).items():
                    if getattr(member, "__module__", None) != name:
                        continue
                    # Newer Python can materialize an empty __annotations__ on lookup.
                    # Leave classes with no declared annotations untouched.
                    if inspect.isfunction(member) or (inspect.isclass(member) and "__annotations__" in vars(member)):
                        with self.subTest(module=name, member=member_name):
                            typing.get_type_hints(member)
                    if inspect.isclass(member):
                        for method_name, method in vars(member).items():
                            if isinstance(method, (staticmethod, classmethod)):
                                method = method.__func__
                            elif isinstance(method, property):
                                method = method.fget
                            if inspect.isfunction(method):
                                with self.subTest(module=name, member=member_name, method=method_name):
                                    typing.get_type_hints(method)

    def test_annotations_avoid_syntax_that_cannot_be_evaluated_on_3_8(self):
        for path in DONT_CHANGE.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                annotation = None
                if isinstance(node, (ast.arg, ast.AnnAssign)):
                    annotation = node.annotation
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    annotation = node.returns
                if annotation is None:
                    continue
                for part in ast.walk(annotation):
                    with self.subTest(path=str(path.relative_to(DONT_CHANGE)), line=annotation.lineno):
                        if isinstance(part, ast.BinOp):
                            self.assertNotIsInstance(part.op, ast.BitOr, "Use typing.Union or Optional on Python 3.8")
                        if isinstance(part, ast.Subscript) and isinstance(part.value, ast.Name):
                            self.assertNotIn(part.value.id, {"list", "dict", "set", "tuple", "frozenset", "type"})


if __name__ == "__main__":
    unittest.main()
