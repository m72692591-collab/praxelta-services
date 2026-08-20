from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_active_product_v2.py"
spec = importlib.util.spec_from_file_location("active_product_v2", SCRIPT)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def copy_repo() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name) / "repo"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(
            ".git",
            ".praxelta-local",
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
        ),
    )
    return temporary, root


def test_current_active_product_contract_passes() -> None:
    temporary, root = copy_repo()
    try:
        assert validator.validate(root) == []
    finally:
        temporary.cleanup()


def test_old_public_price_is_rejected() -> None:
    temporary, root = copy_repo()
    try:
        path = root / "index.html"
        path.write_text(
            path.read_text(encoding="utf-8") + "\n<p>3 900 ₽</p>\n",
            encoding="utf-8",
        )
        assert any("3 900 ₽" in item for item in validator.validate(root))
    finally:
        temporary.cleanup()


def test_live_payment_claim_is_rejected() -> None:
    temporary, root = copy_repo()
    try:
        path = root / "pricing.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["active_product"]["live_payments_enabled"] = True
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        assert any("live payments" in item for item in validator.validate(root))
    finally:
        temporary.cleanup()


def test_false_first_paid_case_is_rejected() -> None:
    temporary, root = copy_repo()
    try:
        path = (
            root
            / "operations"
            / "products"
            / "LOCAL_GROWTH_PRODUCT_DECISION_V2.json"
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        data["commercial_gates"]["first_paid_case_verified"] = True
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        assert any(
            "first_paid_case_verified" in item
            for item in validator.validate(root)
        )
    finally:
        temporary.cleanup()


def test_metadata_description_must_be_exact() -> None:
    temporary, root = copy_repo()
    try:
        path = (
            root
            / "operations"
            / "branding"
            / "GITHUB_METADATA_TARGET.json"
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        data["description"] = "Публичная витрина услуг ПОТОК"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        assert any("exact description" in item for item in validator.validate(root))
    finally:
        temporary.cleanup()


def test_network_submission_primitive_is_rejected() -> None:
    temporary, root = copy_repo()
    try:
        path = root / "express-order.js"
        path.write_text(
            path.read_text(encoding="utf-8") + "\nfetch('/lead');\n",
            encoding="utf-8",
        )
        assert any("fetch(" in item for item in validator.validate(root))
    finally:
        temporary.cleanup()


def test_tracked_private_ledger_is_rejected() -> None:
    temporary, root = copy_repo()
    try:
        path = root / ".praxelta-local" / "order-ledger" / "orders.sqlite3"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"not a real database")
        assert any("private ledger files" in item for item in validator.validate(root))
    finally:
        temporary.cleanup()
