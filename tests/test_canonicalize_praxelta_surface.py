from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/canonicalize_praxelta_surface.py"
spec = importlib.util.spec_from_file_location("canonicalize", SCRIPT)
assert spec and spec.loader
canonicalize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canonicalize)


def test_active_title_is_replaced() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / "index.html"
        path.write_text("<title>Поток — услуги</title>\n<h1>Potok</h1>\n", encoding="utf-8")
        report = canonicalize.process(root, apply=True)
        text = path.read_text(encoding="utf-8")
        assert "ПРАКСЕЛЬТА" in text
        assert "PRAXELTA" in text
        assert report["remaining_active_violation_count"] == 0
        assert report["changed_file_count"] == 1


def test_legacy_context_is_not_rewritten() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        original = "# LEGACY_COMPATIBILITY_ONLY: старый адрес Potok ведёт на ПРАКСЕЛЬТУ.\n"
        path = root / "README.md"
        path.write_text(original, encoding="utf-8")
        report = canonicalize.process(root, apply=True)
        assert path.read_text(encoding="utf-8") == original
        assert report["historical_lines_rewritten"] is False
        assert report["changed_file_count"] == 0


def test_non_brand_word_part_is_not_replaced() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        original = "Потоковый анализ данных не является названием бренда.\n"
        path = root / "notes.txt"
        path.write_text(original, encoding="utf-8")
        report = canonicalize.process(root, apply=True)
        assert path.read_text(encoding="utf-8") == original
        assert report["finding_count"] == 0


def test_review_context_is_reported_but_not_rewritten() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        original = "Мы обсуждали Поток на старой встрече.\n"
        path = root / "notes.txt"
        path.write_text(original, encoding="utf-8")
        report = canonicalize.process(root, apply=True)
        assert path.read_text(encoding="utf-8") == original
        assert report["review_context_count"] == 1
        assert report["mass_unclassified_replacement_used"] is False


def test_dry_run_does_not_write() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        original = "# Поток\n"
        path = root / "README.md"
        path.write_text(original, encoding="utf-8")
        report = canonicalize.process(root, apply=False)
        assert path.read_text(encoding="utf-8") == original
        assert report["mode"] == "DRY_RUN"
