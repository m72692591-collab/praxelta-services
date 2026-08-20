from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_brand_terms.py"

spec = importlib.util.spec_from_file_location("brand_audit_policy", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_negative_grep_is_policy_not_active_brand() -> None:
    line = "! grep -Eqi '(>Поток<|>Potok<)' live-index.html"
    assert module.is_negative_enforcement(line) is True
    assert module.looks_active(line) is False


def test_compiled_rejection_is_policy() -> None:
    line = "rejected=re.compile(r'(?iu)(поток|potok)')"
    assert module.is_negative_enforcement(line) is True


def test_negative_validator_assertion_is_policy() -> None:
    line = (
        'require("Публичная витрина услуг ПОТОК" not in text, '
        '"legacy active metadata copy remains public", errors)'
    )
    assert module.is_negative_enforcement(
        line,
        "scripts/validate_active_product_v2.py",
    ) is True


def test_negative_test_fixture_is_policy() -> None:
    line = 'data["description"] = "Публичная витрина услуг ПОТОК"'
    assert module.is_negative_enforcement(
        line,
        "tests/test_validate_active_product_v2.py",
    ) is True


def test_public_title_is_not_negative_enforcement() -> None:
    line = "<title>Публичная витрина услуг ПОТОК</title>"  # запрещённый тестовый пример
    assert module.is_negative_enforcement(line, "index.html") is False
    assert module.looks_active(line) is True
