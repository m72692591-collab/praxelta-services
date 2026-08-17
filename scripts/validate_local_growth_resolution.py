#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

RESOLUTION = Path(
    "operations/salvage/local-service-growth-v3/DIVERGED_RESOLUTION.json"
)
STATUS = Path(
    "operations/salvage/local-service-growth-v3/INTEGRATION_STATUS.json"
)
EXPECTED_PATHS = {
    "AGENTS.md",
    "README.md",
    "SECURITY.md",
    "docs/IMPLEMENTATION_PLAN.md",
    "docs/OUTREACH_COPYBOOK.md",
    "index.html",
    "output/pdf/praxelta-7-points-checklist.pdf",
    "output/pdf/praxelta-local-growth-commercial.pdf",
    "output/pdf/praxelta-local-growth-teaser.pdf",
    "scripts/check_public_site.py",
    "scripts/generate_pdfs.py",
    "sitemap.xml",
    "styles.css",
}
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
    ).stdout.strip()


def validate(
    root: Path,
    resolution: dict[str, Any],
    status: dict[str, Any],
    source_ref: str | None = None,
) -> list[str]:
    errors: list[str] = []

    if resolution.get("schema_version") != 1:
        errors.append("resolution schema_version drift")
    if resolution.get("decision") != "PRESERVE_CURRENT_CANONICAL_FOR_ALL_DIVERGED_PATHS":
        errors.append("unexpected resolution decision")

    source = resolution.get("source") or {}
    current = resolution.get("current_canonical") or {}
    if source.get("base_sha") != "7775b2dce8116bc77163dd7c0762974fb763244d":
        errors.append("source base SHA drift")
    if source.get("head_sha") != "fa4cda15af8b244d2aee4f17939f8be698ca4f85":
        errors.append("source head SHA drift")
    if current.get("commit_sha") != "c15554ac11a62f3765b2ede99681e4d537645a0d":
        errors.append("current canonical SHA drift")
    if current.get("active_brand_ru") != "ПРАКСЕЛЬТА":
        errors.append("Russian active brand drift")
    if current.get("active_brand_latin") != "PRAXELTA":
        errors.append("Latin active brand drift")

    rows = resolution.get("resolutions")
    if not isinstance(rows, list):
        return errors + ["resolutions must be a list"]
    paths = [row.get("path") for row in rows if isinstance(row, dict)]
    if len(paths) != len(set(paths)):
        errors.append("duplicate resolved path")
    if set(paths) != EXPECTED_PATHS:
        missing = sorted(EXPECTED_PATHS - set(paths))
        extra = sorted(set(paths) - EXPECTED_PATHS)
        errors.append(f"resolved path set drift: missing={missing}, extra={extra}")

    observed_status_paths = set(
        status.get("diverged_paths_requiring_semantic_resolution") or []
    )
    if observed_status_paths != EXPECTED_PATHS:
        errors.append("integration status diverged set does not match resolution")
    if status.get("source_base_sha") != source.get("base_sha"):
        errors.append("integration status source base mismatch")
    if status.get("source_head_sha") != source.get("head_sha"):
        errors.append("integration status source head mismatch")
    if status.get("current_files_overwritten_automatically") is not False:
        errors.append("automatic overwrite boundary drift")
    if status.get("source_deletions_not_applied") not in ([], None):
        errors.append("unexpected source deletions in integration status")

    for row in rows:
        if not isinstance(row, dict):
            errors.append("resolution row must be object")
            continue
        path = row.get("path")
        source_blob = row.get("source_blob")
        current_blob = row.get("current_blob")
        if row.get("disposition") != "CURRENT_CANONICAL_PRESERVED":
            errors.append(f"unexpected disposition: {path}")
        if not isinstance(row.get("rationale"), str) or len(row["rationale"].strip()) < 40:
            errors.append(f"rationale too short: {path}")
        if not isinstance(source_blob, str) or SHA_PATTERN.fullmatch(source_blob) is None:
            errors.append(f"invalid source blob SHA: {path}")
        if not isinstance(current_blob, str) or SHA_PATTERN.fullmatch(current_blob) is None:
            errors.append(f"invalid current blob SHA: {path}")
        if not isinstance(path, str) or not (root / path).is_file():
            errors.append(f"current canonical path missing: {path}")
            continue
        try:
            actual_current = git(root, "hash-object", "--", path)
        except (OSError, subprocess.CalledProcessError) as exc:
            errors.append(f"cannot hash current path {path}: {exc}")
        else:
            if actual_current != current_blob:
                errors.append(
                    f"current blob drift: {path}: expected {current_blob}, got {actual_current}"
                )
        if source_ref:
            try:
                actual_source = git(root, "rev-parse", f"{source_ref}:{path}")
            except (OSError, subprocess.CalledProcessError) as exc:
                errors.append(f"cannot resolve source path {path}: {exc}")
            else:
                if actual_source != source_blob:
                    errors.append(
                        f"source blob drift: {path}: expected {source_blob}, got {actual_source}"
                    )

    summary = resolution.get("summary") or {}
    expected_summary = {
        "source_changed_paths": 51,
        "already_present_or_integrated": 38,
        "diverged_resolved": 13,
        "unresolved_diverged": 0,
        "source_deletions_applied": 0,
        "current_files_overwritten_automatically": 0,
        "historical_branch_deleted": False,
        "history_rewritten": False,
        "product_launch_unlocked": False,
        "deployment_performed": False,
        "live_lead_collection_enabled": False,
        "payments_enabled": False,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            errors.append(f"summary drift: {key}")

    gate = resolution.get("next_gate") or {}
    if gate.get("status") != "OWNER_PRODUCT_DECISION_REQUIRED":
        errors.append("owner product decision gate drift")
    if set(gate.get("decision_options") or []) != {
        "ACTIVE_PRODUCT",
        "INTERNAL_SERVICE_ONLY",
        "HISTORICAL_ARCHIVE",
    }:
        errors.append("owner decision options drift")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--resolution", default=str(RESOLUTION))
    parser.add_argument("--status", default=str(STATUS))
    parser.add_argument("--source-ref")
    parser.add_argument("--report")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    try:
        errors = validate(
            root,
            load(root / args.resolution),
            load(root / args.status),
            args.source_ref,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors = [str(exc)]
    report = {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "diverged_paths_resolved": 13 if not errors else 0,
        "unresolved_diverged_paths": 0 if not errors else 13,
        "product_launch_unlocked": False,
        "owner_product_decision_required": True,
        "deployment_performed": False,
        "payments_enabled": False,
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
