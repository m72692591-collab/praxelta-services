#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DECISION = Path("operations/products/LOCAL_GROWTH_PRODUCT_DECISION_V1.json")
PRICING = Path("pricing.json")
RESOLUTION = Path(
    "operations/salvage/local-service-growth-v3/DIVERGED_RESOLUTION.json"
)
DEPLOYMENT = Path("operations/deployment/GITHUB_PAGES_DEPLOYMENT_V1.json")

EXPECTED_DEPLOYMENT_FILES = {
    "index.html",
    "styles.css",
    "sitemap.xml",
    "pricing.json",
}
EXPECTED_PUBLIC_URL = "https://m72692591-collab.github.io/praxelta-services/"


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
    deployment: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    require(decision.get("schema_version") == 1, "decision schema drift", errors)
    require(
        decision.get("status") == "ACTIVE_PRODUCT",
        "product direction must remain ACTIVE_PRODUCT",
        errors,
    )
    require(
        decision.get("decision_source")
        == "OWNER_DIRECTIVE_COMPLETE_ALL_REMAINING_GATES",
        "owner decision source drift",
        errors,
    )

    project = decision.get("project") or {}
    require(project.get("brand_ru") == "ПРАКСЕЛЬТА", "Russian brand drift", errors)
    require(project.get("brand_latin") == "PRAXELTA", "Latin brand drift", errors)
    require(
        project.get("independent_from") == "ANIMA TACTUS",
        "project separation drift",
        errors,
    )

    product = decision.get("product") or {}
    offer = product.get("entry_offer") or {}
    pricing_offer = ((pricing.get("services") or {}).get("express") or {})
    require(offer.get("tariff_id") == "express", "entry tariff drift", errors)
    require(
        offer.get("price_rub") == 7900,
        "owner-confirmed entry price drift",
        errors,
    )
    require(offer.get("duration_days") == 7, "entry duration drift", errors)
    require(
        offer.get("price_rub") == pricing_offer.get("price_once"),
        "pricing.json amount mismatch",
        errors,
    )
    require(
        offer.get("duration_days") == pricing_offer.get("duration_days"),
        "pricing.json duration mismatch",
        errors,
    )
    require(
        offer.get("scope") == pricing_offer.get("summary"),
        "pricing.json scope mismatch",
        errors,
    )
    require(
        offer.get("price_status") == "CONFIRMED_TEST_ENTRY_OFFER",
        "price status drift",
        errors,
    )
    require(
        offer.get("guaranteed_results") is False,
        "guaranteed results must remain false",
        errors,
    )
    for key in ("medical_service", "financial_guarantee", "lead_guarantee"):
        require(
            product.get(key) is False,
            f"product safety flag must remain false: {key}",
            errors,
        )

    launch = decision.get("launch_model") or {}
    require(
        launch.get("status") == "ACTIVE_PRODUCT_PRELAUNCH",
        "launch status drift",
        errors,
    )
    require(
        launch.get("budget_rub") == 0,
        "budget must remain zero until separate decision",
        errors,
    )
    require(
        launch.get("static_public_information_allowed") is True,
        "static public information gate drift",
        errors,
    )
    require(
        launch.get("consent_first_contact_allowed") is True,
        "consent-first contact gate drift",
        errors,
    )
    require(
        launch.get("manual_written_order_allowed") is True,
        "written-order gate drift",
        errors,
    )
    for key in (
        "mass_unsolicited_outreach_allowed",
        "automated_live_lead_collection_allowed",
        "production_backend_enabled",
        "live_payments_enabled",
        "paid_advertising_enabled",
    ):
        require(
            launch.get(key) is False,
            f"launch switch must remain false: {key}",
            errors,
        )
    require(
        launch.get("deployment_receipt_required") is True,
        "deployment receipt requirement missing",
        errors,
    )
    require(
        launch.get("first_real_client_receipt_required") is True,
        "first client receipt requirement missing",
        errors,
    )

    separation = decision.get("data_and_separation") or {}
    for key in (
        "share_customer_data_with_anima_tactus",
        "share_payment_credentials_with_anima_tactus",
        "assume_common_merchant_account",
        "sensitive_data_collection_enabled",
    ):
        require(
            separation.get(key) is False,
            f"cross-project boundary must remain false: {key}",
            errors,
        )
    require(
        separation.get("contact_data_requires_explicit_consent") is True,
        "explicit consent requirement missing",
        errors,
    )

    deployment_block = decision.get("deployment") or {}
    require(
        deployment_block.get("status")
        == "VERIFIED_CURRENT_MAIN_ON_GITHUB_PAGES",
        "deployment status drift",
        errors,
    )
    require(
        deployment_block.get("receipt")
        == "operations/deployment/GITHUB_PAGES_DEPLOYMENT_V1.json",
        "deployment receipt reference drift",
        errors,
    )
    require(
        deployment_block.get("public_url") == EXPECTED_PUBLIC_URL,
        "decision public URL drift",
        errors,
    )
    require(
        set(deployment_block.get("verified_files") or [])
        == EXPECTED_DEPLOYMENT_FILES,
        "decision verified file set drift",
        errors,
    )

    require(
        deployment.get("receipt_id") == "PRAXELTA_GITHUB_PAGES_DEPLOYMENT_V1",
        "unexpected deployment receipt ID",
        errors,
    )
    require(
        deployment.get("repository") == "m72692591-collab/praxelta-services",
        "deployment repository drift",
        errors,
    )
    require(deployment.get("branch") == "main", "deployment branch drift", errors)
    require(
        deployment.get("public_url") == EXPECTED_PUBLIC_URL,
        "deployment public URL drift",
        errors,
    )
    require(
        deployment.get("source_commit") == deployment_block.get("source_commit"),
        "deployment source commit mismatch",
        errors,
    )

    verification = deployment.get("verification") or {}
    require(
        verification.get("http_fetch_succeeded") is True,
        "deployment HTTP verification missing",
        errors,
    )
    require(
        verification.get("canonical_brand_visible") is True,
        "canonical brand was not verified live",
        errors,
    )
    require(
        verification.get("active_rejected_name_in_index") is False,
        "rejected active name appears in live index",
        errors,
    )
    exact_files = verification.get("exact_files") or {}
    require(
        set(exact_files) == EXPECTED_DEPLOYMENT_FILES,
        "deployment exact file set drift",
        errors,
    )
    for path in sorted(EXPECTED_DEPLOYMENT_FILES):
        row = exact_files.get(path) or {}
        require(
            row.get("live_matches_repository") is True,
            f"live file does not match repository: {path}",
            errors,
        )
        digest = row.get("sha256")
        require(
            isinstance(digest, str) and len(digest) == 64,
            f"invalid live file SHA-256: {path}",
            errors,
        )

    claims = deployment.get("claims") or {}
    require(
        claims.get("deployment_verified") is True,
        "deployment receipt is not verified",
        errors,
    )
    require(
        claims.get("current_main_release_verified") is True,
        "current main release is not verified",
        errors,
    )
    for key in (
        "automated_live_leads_enabled",
        "production_backend_enabled",
        "live_payments_enabled",
        "first_real_client_verified",
        "revenue_verified",
    ):
        require(
            claims.get(key) is False,
            f"deployment receipt must keep non-deployment claim false: {key}",
            errors,
        )

    safety = deployment.get("safety") or {}
    for key in (
        "customer_data_collected_during_verification",
        "credentials_recorded",
        "paid_actions_performed",
        "branches_deleted",
        "history_rewritten",
    ):
        require(
            safety.get(key) is False,
            f"deployment safety flag must remain false: {key}",
            errors,
        )

    switches = decision.get("current_switches") or {}
    require(
        switches.get("product_direction_active") is True,
        "product direction switch drift",
        errors,
    )
    require(
        switches.get("price_7900_confirmed") is True,
        "price confirmation switch drift",
        errors,
    )
    require(
        switches.get("deployment_claim_allowed") is True,
        "verified deployment claim must remain true",
        errors,
    )
    for key in (
        "live_leads_claim_allowed",
        "first_client_claim_allowed",
        "revenue_claim_allowed",
        "live_payments_enabled",
        "paid_actions_enabled",
    ):
        require(
            switches.get(key) is False,
            f"claim/financial switch must remain false: {key}",
            errors,
        )

    source = decision.get("historical_evidence") or {}
    require(source.get("source_pr") == 1, "historical source PR drift", errors)
    require(
        source.get("source_branch_preserved") is True,
        "historical branch preservation missing",
        errors,
    )
    for key in ("blind_merge_performed", "branches_deleted", "history_rewritten"):
        require(
            source.get(key) is False,
            f"historical safety flag must remain false: {key}",
            errors,
        )

    summary = resolution.get("summary") or {}
    require(
        summary.get("unresolved_diverged") == 0,
        "product decision requires zero unresolved diverged paths",
        errors,
    )
    require(
        summary.get("diverged_resolved") == 13,
        "expected 13 resolved diverged paths",
        errors,
    )
    require(
        summary.get("product_launch_unlocked") is False,
        "semantic resolution must not unlock launch",
        errors,
    )
    require(
        summary.get("deployment_performed") is False,
        "semantic resolution itself cannot claim deployment",
        errors,
    )
    require(
        summary.get("live_lead_collection_enabled") is False,
        "semantic resolution cannot enable live leads",
        errors,
    )
    require(
        summary.get("payments_enabled") is False,
        "semantic resolution cannot enable payments",
        errors,
    )

    require(
        len(decision.get("required_before_external_launch_claim") or []) >= 6,
        "external launch gate list incomplete",
        errors,
    )
    require(
        len(decision.get("required_before_first_paid_order") or []) >= 6,
        "first paid order gate list incomplete",
        errors,
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--decision", default=str(DECISION))
    parser.add_argument("--pricing", default=str(PRICING))
    parser.add_argument("--resolution", default=str(RESOLUTION))
    parser.add_argument("--deployment", default=str(DEPLOYMENT))
    parser.add_argument("--report")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    try:
        errors = validate(
            load(root / args.decision),
            load(root / args.pricing),
            load(root / args.resolution),
            load(root / args.deployment),
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
        "deployment_verified": not errors,
        "public_url": EXPECTED_PUBLIC_URL if not errors else None,
        "live_leads_claim_allowed": False,
        "live_payments_enabled": False,
        "first_real_client_verified": False,
        "revenue_verified": False,
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
    raise SystemExit(main())
