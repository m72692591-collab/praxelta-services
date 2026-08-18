#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DECISION = Path("operations/products/LOCAL_GROWTH_PRODUCT_DECISION_V1.json")
PRICING = Path("pricing.json")
RESOLUTION = Path("operations/salvage/local-service-growth-v3/DIVERGED_RESOLUTION.json")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(
    decision: dict[str, Any],
    pricing: dict[str, Any],
    resolution: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    require(decision.get("schema_version") == 1, "decision schema drift", errors)
    require(decision.get("status") == "ACTIVE_PRODUCT", "product direction must remain ACTIVE_PRODUCT", errors)
    require(
        decision.get("decision_source") == "OWNER_DIRECTIVE_COMPLETE_ALL_REMAINING_GATES",
        "owner decision source drift",
        errors,
    )

    project = decision.get("project") or {}
    require(project.get("brand_ru") == "ПРАКСЕЛЬТА", "Russian brand drift", errors)
    require(project.get("brand_latin") == "PRAXELTA", "Latin brand drift", errors)
    require(project.get("independent_from") == "ANIMA TACTUS", "project separation drift", errors)

    product = decision.get("product") or {}
    offer = product.get("entry_offer") or {}
    pricing_offer = ((pricing.get("services") or {}).get("express") or {})
    require(offer.get("tariff_id") == "express", "entry tariff drift", errors)
    require(offer.get("price_rub") == 7900, "owner-confirmed entry price drift", errors)
    require(offer.get("duration_days") == 7, "entry duration drift", errors)
    require(offer.get("price_rub") == pricing_offer.get("price_once"), "pricing.json amount mismatch", errors)
    require(offer.get("duration_days") == pricing_offer.get("duration_days"), "pricing.json duration mismatch", errors)
    require(offer.get("scope") == pricing_offer.get("summary"), "pricing.json scope mismatch", errors)
    require(offer.get("price_status") == "CONFIRMED_TEST_ENTRY_OFFER", "price status drift", errors)
    require(offer.get("guaranteed_results") is False, "guaranteed results must remain false", errors)
    for key in ("medical_service", "financial_guarantee", "lead_guarantee"):
        require(product.get(key) is False, f"product safety flag must remain false: {key}", errors)

    launch = decision.get("launch_model") or {}
    require(launch.get("status") == "ACTIVE_PRODUCT_PRELAUNCH", "launch status drift", errors)
    require(launch.get("budget_rub") == 0, "budget must remain zero until separate decision", errors)
    require(launch.get("static_public_information_allowed") is True, "static public information gate drift", errors)
    require(launch.get("consent_first_contact_allowed") is True, "consent-first contact gate drift", errors)
    require(launch.get("manual_written_order_allowed") is True, "written-order gate drift", errors)
    for key in (
        "mass_unsolicited_outreach_allowed",
        "automated_live_lead_collection_allowed",
        "production_backend_enabled",
        "live_payments_enabled",
        "paid_advertising_enabled",
    ):
        require(launch.get(key) is False, f"launch switch must remain false: {key}", errors)
    require(launch.get("deployment_receipt_required") is True, "deployment receipt requirement missing", errors)
    require(launch.get("first_real_client_receipt_required") is True, "first client receipt requirement missing", errors)

    separation = decision.get("data_and_separation") or {}
    for key in (
        "share_customer_data_with_anima_tactus",
        "share_payment_credentials_with_anima_tactus",
        "assume_common_merchant_account",
        "sensitive_data_collection_enabled",
    ):
        require(separation.get(key) is False, f"cross-project boundary must remain false: {key}", errors)
    require(separation.get("contact_data_requires_explicit_consent") is True, "explicit consent requirement missing", errors)

    switches = decision.get("current_switches") or {}
    require(switches.get("product_direction_active") is True, "product direction switch drift", errors)
    require(switches.get("price_7900_confirmed") is True, "price confirmation switch drift", errors)
    for key in (
        "deployment_claim_allowed",
        "live_leads_claim_allowed",
        "first_client_claim_allowed",
        "revenue_claim_allowed",
        "live_payments_enabled",
        "paid_actions_enabled",
    ):
        require(switches.get(key) is False, f"claim/financial switch must remain false: {key}", errors)

    source = decision.get("historical_evidence") or {}
    require(source.get("source_pr") == 1, "historical source PR drift", errors)
    require(source.get("source_branch_preserved") is True, "historical branch preservation missing", errors)
    for key in ("blind_merge_performed", "branches_deleted", "history_rewritten"):
        require(source.get(key) is False, f"historical safety flag must remain false: {key}", errors)

    summary = resolution.get("summary") or {}
    require(summary.get("unresolved_diverged") == 0, "product decision requires zero unresolved diverged paths", errors)
    require(summary.get("diverged_resolved") == 13, "expected 13 resolved diverged paths", errors)
    require(summary.get("product_launch_unlocked") is False, "resolution must not unlock launch", errors)
    require(summary.get("deployment_performed") is False, "resolution cannot claim deployment", errors)
    require(summary.get("live_lead_collection_enabled") is False, "resolution cannot enable live leads", errors)
    require(summary.get("payments_enabled") is False, "resolution cannot enable payments", errors)

    require(len(decision.get("required_before_external_launch_claim") or []) >= 6, "external launch gate list incomplete", errors)
    require(len(decision.get("required_before_first_paid_order") or []) >= 6, "first paid order gate list incomplete", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--decision", default=str(DECISION))
    parser.add_argument("--pricing", default=str(PRICING))
    parser.add_argument("--resolution", default=str(RESOLUTION))
    parser.add_argument("--report")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    try:
        errors = validate(
            load(root / args.decision),
            load(root / args.pricing),
            load(root / args.resolution),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors = [str(exc)]
    report = {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "product_direction": "ACTIVE_PRODUCT" if not errors else "BLOCKED",
        "entry_price_rub": 7900 if not errors else None,
        "deployment_claim_allowed": False,
        "live_leads_claim_allowed": False,
        "live_payments_enabled": False,
        "paid_actions_enabled": False,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        output = root / args.report
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
