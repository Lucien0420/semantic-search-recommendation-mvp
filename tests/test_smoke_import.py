"""Sanity check: app package and FastAPI instance import without starting the server."""

from __future__ import annotations

import unittest


class TestImports(unittest.TestCase):
    def test_import_main_app(self) -> None:
        from main import app

        self.assertTrue(app.title)

    def test_import_app_package(self) -> None:
        import app

        self.assertEqual(app.__name__, "app")


if __name__ == "__main__":
    unittest.main()
