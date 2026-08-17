from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "remediate_active_brand_terms.py"
SPEC = importlib.util.spec_from_file_location("remediate_active_brand_terms", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BrandRemediationTests(unittest.TestCase):
    def test_active_heading_is_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text(
                "<title>Поток — услуги</title>\n<h1>Potok</h1>\n",
                encoding="utf-8",
            )
            payload = MODULE.migrate(root, apply=True)
            text = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("ПРАКСЕЛЬТА", text)
            self.assertIn("PRAXELTA", text)
            self.assertEqual(1, payload["changed_file_count"])

    def test_legacy_marked_line_is_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = "# LEGACY_COMPATIBILITY_ONLY: Potok перенаправляет на ПРАКСЕЛЬТУ.\n"
            (root / "README.md").write_text(original, encoding="utf-8")
            payload = MODULE.migrate(root, apply=True)
            self.assertEqual(original, (root / "README.md").read_text(encoding="utf-8"))
            self.assertEqual(0, payload["changed_file_count"])

    def test_slug_is_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = '<a href="https://example.test/potok-services/">legacy</a>\n'
            (root / "index.html").write_text(original, encoding="utf-8")
            MODULE.migrate(root, apply=True)
            self.assertEqual(original, (root / "index.html").read_text(encoding="utf-8"))

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = "# Поток\n"
            (root / "README.md").write_text(original, encoding="utf-8")
            payload = MODULE.migrate(root, apply=False)
            self.assertEqual(original, (root / "README.md").read_text(encoding="utf-8"))
            self.assertEqual("dry_run", payload["mode"])


if __name__ == "__main__":
    unittest.main()
