#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PRODUCT_NAME = "Управляемое продвижение и учёт обращений"
ENTRY_NAME = "Экспресс"
PRICE_RUB = 7900
DURATION_DAYS = 7
DESCRIPTION = "Публичная витрина и рабочие материалы ПРАКСЕЛЬТЫ"
HOMEPAGE = "https://m72692591-collab.github.io/praxelta-services/"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    index_path = root / "index.html"
    order_path = root / "express-order.html"
    order_js_path = root / "express-order.js"
    pricing_path = root / "pricing.json"
    decision_path = (
        root
        / "operations"
        / "products"
        / "LOCAL_GROWTH_PRODUCT_DECISION_V2.json"
    )
    metadata_path = (
        root
        / "operations"
        / "branding"
        / "GITHUB_METADATA_TARGET.json"
    )
    ledger_path = root / "scripts" / "praxelta_order_ledger.py"
    gitignore_path = root / ".gitignore"

    for path in (
        index_path,
        order_path,
        order_js_path,
        pricing_path,
        decision_path,
        metadata_path,
        ledger_path,
        gitignore_path,
    ):
        require(path.is_file(), f"required path missing: {path.relative_to(root)}", errors)
    if errors:
        return errors

    index = index_path.read_text(encoding="utf-8-sig")
    visible_index = re.sub(r"<[^>]+>", " ", index)
    require(PRODUCT_NAME in visible_index, "active product name missing from index", errors)
    require("7 900 ₽" in visible_index, "entry price missing from index", errors)
    require("7 дней" in visible_index, "entry duration missing from index", errors)
    require("3 900 ₽" not in index, "superseded 3 900 ₽ offer remains on index", errors)
    require("Пилот —" not in visible_index, "superseded pilot label remains on index", errors)
    require("гарант" in visible_index.casefold(), "guarantee boundary missing on index", errors)
    require("express-order.html" in index, "structured intake CTA missing on index", errors)
    for legal in ("offer.html", "privacy.html", "terms.html", "refund.html"):
        require(legal in index, f"legal link missing from index: {legal}", errors)

    pricing = read_json(pricing_path)
    active = pricing.get("active_product") or {}
    express = (pricing.get("services") or {}).get("express") or {}
    require(pricing.get("schema_version") == 2, "pricing schema drift", errors)
    require(pricing.get("currency") == "RUB", "pricing currency drift", errors)
    require(active.get("name") == PRODUCT_NAME, "pricing product name drift", errors)
    require(active.get("entry_tariff_id") == "express", "pricing entry tariff drift", errors)
    require(active.get("live_payments_enabled") is False, "live payments must remain off", errors)
    require(active.get("lead_guarantee") is False, "lead guarantee must remain false", errors)
    require(active.get("revenue_guarantee") is False, "revenue guarantee must remain false", errors)
    require(express.get("name") == ENTRY_NAME, "express tariff name drift", errors)
    require(express.get("price_once") == PRICE_RUB, "express price drift", errors)
    require(express.get("duration_days") == DURATION_DAYS, "express duration drift", errors)

    decision = read_json(decision_path)
    product = decision.get("product") or {}
    entry = product.get("entry_offer") or {}
    intake = decision.get("public_intake") or {}
    ledger = decision.get("local_order_ledger") or {}
    gates = decision.get("commercial_gates") or {}
    deployment = decision.get("deployment") or {}
    metadata = decision.get("metadata") or {}
    require(decision.get("schema_version") == 2, "product decision schema drift", errors)
    require(decision.get("status") == "ACTIVE_PRODUCT_PRELAUNCH", "product status drift", errors)
    require(product.get("name") == PRODUCT_NAME, "decision product name drift", errors)
    require(entry.get("price_rub") == PRICE_RUB, "decision price drift", errors)
    require(entry.get("currency") == "RUB", "decision currency drift", errors)
    require(entry.get("duration_days") == DURATION_DAYS, "decision duration drift", errors)
    for guarantee in ("guaranteed_leads", "guaranteed_revenue", "guaranteed_ranking"):
        require(entry.get(guarantee) is False, f"forbidden guarantee enabled: {guarantee}", errors)
    require(intake.get("status") == "LOCAL_EMAIL_COMPOSER_ONLY", "intake status drift", errors)
    require(intake.get("automatic_submission") is False, "automatic submission must be false", errors)
    require(intake.get("server_storage") is False, "server storage must be false", errors)
    require(intake.get("written_order_required_before_payment") is True, "written order gate missing", errors)
    require(ledger.get("tracked_in_git") is False, "ledger must remain outside Git", errors)
    require(ledger.get("revenue_requires_reconciliation") is True, "revenue reconciliation gate missing", errors)
    require(ledger.get("profit_requires_direct_costs") is True, "profit cost gate missing", errors)
    for gate in (
        "seller_identity_confirmed",
        "tax_mode_confirmed_for_this_launch",
        "written_order_received",
        "provider_payment_confirmed",
        "delivery_receipt_confirmed",
        "client_acceptance_confirmed",
        "reconciliation_confirmed",
        "first_paid_case_verified",
        "revenue_verified",
        "profit_verified",
        "live_payments_enabled",
    ):
        require(gates.get(gate) is False, f"unproven commercial gate enabled: {gate}", errors)
    require(deployment.get("status") == "REDEPLOY_REQUIRED_FOR_V2", "deployment must remain pending", errors)
    require(deployment.get("source_commit") is None, "unverified deployment commit recorded", errors)
    require(metadata.get("patch_completed") is False, "metadata patch falsely completed", errors)
    require(metadata.get("repeat_api_get_verified") is False, "metadata GET falsely verified", errors)

    metadata_target = read_json(metadata_path)
    require(metadata_target.get("schema_version") == 2, "metadata target schema drift", errors)
    require(metadata_target.get("repository") == "m72692591-collab/praxelta-services", "metadata repository drift", errors)
    require(metadata_target.get("description") == DESCRIPTION, "metadata exact description drift", errors)
    require(metadata_target.get("homepage") == HOMEPAGE, "metadata homepage drift", errors)
    require(metadata_target.get("default_branch") == "main", "metadata default branch drift", errors)
    verification = metadata_target.get("verification") or {}
    require(verification.get("patch_is_not_completion") is True, "metadata patch-only prohibition missing", errors)
    require(verification.get("repeat_api_get_required") is True, "metadata repeat GET gate missing", errors)

    order_html = order_path.read_text(encoding="utf-8-sig")
    for text in (
        PRODUCT_NAME,
        "7 900 ₽",
        "7 дней",
        "сайт ничего не отправляет",
        "не гарантирует лиды",
        "не согласие на рекламную рассылку",
        "offer.html",
        "privacy.html",
        "terms.html",
        "refund.html",
    ):
        require(text.casefold() in order_html.casefold(), f"express intake missing: {text}", errors)
    for checkbox in ("scope_ack", "privacy_ack", "terms_ack", "contact_ack"):
        require(f'name="{checkbox}"' in order_html, f"required consent missing: {checkbox}", errors)
    require("express-order.js" in order_html, "express-order.js not loaded", errors)

    order_js = order_js_path.read_text(encoding="utf-8-sig")
    for required in (
        "PRX-EX-",
        "window.crypto.getRandomValues",
        "navigator.clipboard",
        "mail.google.com",
        "mailto:",
        "form.reportValidity",
    ):
        require(required in order_js, f"express-order.js missing {required}", errors)
    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "sendBeacon",
        "WebSocket",
        "localStorage",
        "sessionStorage",
        "indexedDB",
    ):
        require(forbidden not in order_js, f"express-order.js forbidden primitive: {forbidden}", errors)

    ledger_source = ledger_path.read_text(encoding="utf-8-sig")
    for required in (
        "PRICE_RUB = 7900",
        'CURRENCY = "RUB"',
        "DURATION_DAYS = 7",
        "DUPLICATE_PAYMENT_IDENTIFIER",
        "RECONCILIATION_GATE_INCOMPLETE",
        "first_real_payment_verified",
        "revenue_verified",
        "profit_verified",
        ".praxelta-local",
    ):
        require(required in ledger_source, f"order ledger missing contract: {required}", errors)
    gitignore = gitignore_path.read_text(encoding="utf-8-sig")
    require(".praxelta-local/" in gitignore, "private ledger directory not ignored", errors)

    for path in root.glob("*.html"):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        require("3 900 ₽" not in text, f"superseded 3 900 ₽ remains public: {path.name}", errors)
        require("Публичная витрина услуг ПОТОК" not in text, f"legacy active metadata copy remains public: {path.name}", errors)

    tracked_private = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".praxelta-local" in path.parts
    ]
    require(not tracked_private, f"private ledger files present in source: {tracked_private}", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors = validate(root)
    report = {
        "schema_version": 2,
        "status": "PASS" if not errors else "FAIL",
        "active_product": PRODUCT_NAME,
        "entry_offer": {
            "name": ENTRY_NAME,
            "price_rub": PRICE_RUB,
            "currency": "RUB",
            "duration_days": DURATION_DAYS,
        },
        "metadata_target": DESCRIPTION,
        "live_payments": False,
        "first_paid_case_verified": False,
        "revenue_verified": False,
        "profit_verified": False,
        "error_count": len(errors),
        "errors": errors,
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
