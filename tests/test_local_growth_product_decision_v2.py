from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_local_growth_product_decision_v2.py"
DECISION = ROOT / "operations/products/LOCAL_GROWTH_PRODUCT_DECISION_V1.json"
PRICING = ROOT / "pricing.json"
RESOLUTION = ROOT / (
    "operations/salvage/local-service-growth-v3/DIVERGED_RESOLUTION.json"
)
DEPLOYMENT = ROOT / "operations/deployment/GITHUB_PAGES_DEPLOYMENT_V1.json"

spec = importlib.util.spec_from_file_location(
    "local_growth_product_decision_v2",
    SCRIPT,
)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def errors(**overrides) -> list[str]:
    return validator.validate(
        overrides.get("decision", load(DECISION)),
        overrides.get("pricing", load(PRICING)),
        overrides.get("resolution", load(RESOLUTION)),
        overrides.get("deployment", load(DEPLOYMENT)),
    )


def test_current_owner_decision_and_deployment_pass() -> None:
    assert errors() == []


def test_product_direction_cannot_fall_back_to_undefined() -> None:
    decision = load(DECISION)
    changed = copy.deepcopy(decision)
    changed["status"] = "UNDECIDED"
    assert any("ACTIVE_PRODUCT" in error for error in errors(decision=changed))


def test_entry_price_must_match_pricing_registry() -> None:
    decision = load(DECISION)
    changed = copy.deepcopy(decision)
    changed["product"]["entry_offer"]["price_rub"] = 8000
    current = errors(decision=changed)
    assert any(
        "price drift" in error or "amount mismatch" in error
        for error in current
    )


def test_live_payments_cannot_be_enabled_by_product_decision() -> None:
    decision = load(DECISION)
    changed = copy.deepcopy(decision)
    changed["launch_model"]["live_payments_enabled"] = True
    assert any(
        "live_payments_enabled" in error
        for error in errors(decision=changed)
    )


def test_live_lead_collection_cannot_be_enabled() -> None:
    decision = load(DECISION)
    changed = copy.deepcopy(decision)
    changed["launch_model"]["automated_live_lead_collection_allowed"] = True
    assert any(
        "automated_live_lead_collection_allowed" in error
        for error in errors(decision=changed)
    )


def test_mass_unsolicited_outreach_remains_forbidden() -> None:
    decision = load(DECISION)
    changed = copy.deepcopy(decision)
    changed["launch_model"]["mass_unsolicited_outreach_allowed"] = True
    assert any(
        "mass_unsolicited_outreach_allowed" in error
        for error in errors(decision=changed)
    )


def test_cross_project_customer_data_sharing_remains_forbidden() -> None:
    decision = load(DECISION)
    changed = copy.deepcopy(decision)
    changed["data_and_separation"][
        "share_customer_data_with_anima_tactus"
    ] = True
    assert any(
        "share_customer_data_with_anima_tactus" in error
        for error in errors(decision=changed)
    )


def test_deployment_claim_requires_exact_receipt() -> None:
    deployment = load(DEPLOYMENT)
    changed = copy.deepcopy(deployment)
    changed["verification"]["exact_files"]["index.html"][
        "live_matches_repository"
    ] = False
    assert any(
        "live file does not match repository: index.html" in error
        for error in errors(deployment=changed)
    )


def test_deployment_source_commit_must_match_decision() -> None:
    deployment = load(DEPLOYMENT)
    changed = copy.deepcopy(deployment)
    changed["source_commit"] = "0" * 40
    assert any(
        "deployment source commit mismatch" in error
        for error in errors(deployment=changed)
    )


def test_deployment_claim_switch_cannot_be_disabled_after_receipt() -> None:
    decision = load(DECISION)
    changed = copy.deepcopy(decision)
    changed["current_switches"]["deployment_claim_allowed"] = False
    assert any(
        "verified deployment claim must remain true" in error
        for error in errors(decision=changed)
    )


def test_first_client_and_revenue_claims_remain_false() -> None:
    decision = load(DECISION)
    changed = copy.deepcopy(decision)
    changed["current_switches"]["first_client_claim_allowed"] = True
    changed["current_switches"]["revenue_claim_allowed"] = True
    current = errors(decision=changed)
    assert any("first_client_claim_allowed" in error for error in current)
    assert any("revenue_claim_allowed" in error for error in current)


def test_owner_decision_requires_zero_semantic_residue() -> None:
    resolution = load(RESOLUTION)
    changed = copy.deepcopy(resolution)
    changed["summary"]["unresolved_diverged"] = 1
    assert any(
        "zero unresolved" in error
        for error in errors(resolution=changed)
    )


def test_semantic_resolution_cannot_claim_payment_or_live_leads() -> None:
    resolution = load(RESOLUTION)
    changed = copy.deepcopy(resolution)
    changed["summary"]["payments_enabled"] = True
    changed["summary"]["live_lead_collection_enabled"] = True
    current = errors(resolution=changed)
    assert any("cannot enable payments" in error for error in current)
    assert any("cannot enable live leads" in error for error in current)


def test_deployment_receipt_cannot_enable_backend_or_payments() -> None:
    deployment = load(DEPLOYMENT)
    changed = copy.deepcopy(deployment)
    changed["claims"]["production_backend_enabled"] = True
    changed["claims"]["live_payments_enabled"] = True
    current = errors(deployment=changed)
    assert any("production_backend_enabled" in error for error in current)
    assert any("live_payments_enabled" in error for error in current)
