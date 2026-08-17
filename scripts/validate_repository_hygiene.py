#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

MANIFEST_PATH = Path("governance/EPHEMERAL_WORKFLOW_RETIREMENT_V1.json")
RECEIPT_PATH = Path("governance/REPOSITORY_METADATA_RECEIPT.json")
ONE_SHOT = re.compile(r"^one-shot-.*\.ya?ml$", re.IGNORECASE)
BYTECODE = re.compile(
    r"(?:^|/)__pycache__(?:/|$)|\.py[co]$|\.pyd$",
    re.IGNORECASE,
)
SHA1 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED = {
    ".github/workflows/one-shot-consolidate-praxelta.yml":
        "9cf71b6f10a47128fd28d35b1ff8f5f39dd94fc5",
    ".github/workflows/one-shot-normalize-praxelta-metadata.yml":
        "3b8bdca9e7d2ae1ad793e3cf41f972f27b31eb32",
    ".github/workflows/one-shot-praxelta-final-order-v2.yml":
        "b82b2b032afcb22cf4d01150ab0a7388f88a51b9",
}


class ValidationError(ValueError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Cannot read valid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be object: {path}")
    return value


def tracked_paths(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(root),
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ValidationError(
            completed.stderr.decode("utf-8", errors="replace")[:500]
        )
    return [
        item.decode("utf-8", errors="surrogateescape")
        for item in completed.stdout.split(b"\0")
        if item
    ]


def find_one_shots(root: Path) -> list[str]:
    workflow_root = root / ".github/workflows"
    if not workflow_root.exists():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in workflow_root.rglob("*")
        if path.is_file() and ONE_SHOT.fullmatch(path.name)
    )


def find_bytecode(paths: Iterable[str]) -> list[str]:
    return sorted(path for path in paths if BYTECODE.search(path))


def validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if data.get("registry_id") != "PRAXELTA_EPHEMERAL_WORKFLOW_RETIREMENT_V1":
        errors.append("unexpected manifest registry_id")
    if data.get("canonical_branch") != "main":
        errors.append("canonical_branch must remain main")
    policy = data.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
    else:
        if policy.get("git_history_preserved") is not True:
            errors.append("git_history_preserved must be true")
        for key in (
            "one_shot_workflows_allowed_in_main",
            "branch_deletion_performed",
            "product_content_changed",
            "destructive_git_used",
        ):
            if policy.get(key) is not False:
                errors.append(f"policy.{key} must be false")

    entries = data.get("retired_workflows")
    if not isinstance(entries, list):
        return errors + ["retired_workflows must be array"]
    actual: dict[str, str] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"retired_workflows[{index}] must be object")
            continue
        path = entry.get("path")
        sha = entry.get("blob_sha")
        if not isinstance(path, str) or not path:
            errors.append(f"retired_workflows[{index}].path missing")
            continue
        if path in actual:
            errors.append(f"duplicate retirement path: {path}")
        if not isinstance(sha, str) or not SHA1.fullmatch(sha):
            errors.append(f"invalid blob SHA: {path}")
        else:
            actual[path] = sha
        if entry.get("status") != "RETIRED_FROM_MAIN":
            errors.append(f"invalid retirement status: {path}")
    if actual != EXPECTED:
        errors.append("retirement path/blob mapping differs from exact base evidence")
    return errors


def validate_receipt(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("repository") != "m72692591-collab/praxelta-services":
        errors.append("metadata receipt repository mismatch")
    if data.get("status") not in {
        "BLOCKED_BY_REPOSITORY_ADMINISTRATION_PERMISSION",
        "VERIFIED",
    }:
        errors.append("unexpected metadata receipt status")
    if data.get("expected_description") != (
        "ПРАКСЕЛЬТА — управляемое продвижение локальных услуг и учёт обращений"
    ):
        errors.append("expected description drift")
    if data.get("expected_homepage") != (
        "https://m72692591-collab.github.io/praxelta-services/"
    ):
        errors.append("expected homepage drift")
    if data.get("secrets_recorded") is not False:
        errors.append("metadata receipt must not record secrets")
    return errors


def validate(root: Path) -> list[str]:
    errors = validate_manifest(load(root / MANIFEST_PATH))
    errors.extend(validate_receipt(load(root / RECEIPT_PATH)))
    one_shots = find_one_shots(root)
    if one_shots:
        errors.append("one-shot workflows remain: " + ", ".join(one_shots))
    bytecode = find_bytecode(tracked_paths(root))
    if bytecode:
        errors.append("tracked Python bytecode remains: " + ", ".join(bytecode))
    for path in EXPECTED:
        if (root / path).exists():
            errors.append(f"retired workflow still exists: {path}")
    for required in (
        "BRAND_CANON.md",
        "PROJECT_IDENTITY.md",
        "brand_registry.json",
        "scripts/audit_brand_terms.py",
        ".github/workflows/praxelta-brand-audit.yml",
        ".github/workflows/quality.yml",
    ):
        if not (root / required).is_file():
            errors.append(f"required permanent asset missing: {required}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report", default="repository-hygiene-report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        errors = validate(root)
    except ValidationError as exc:
        errors = [str(exc)]
    payload = {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "one_shot_allowed": False,
        "bytecode_allowed": False,
        "branch_deletion_performed": False,
        "product_content_changed": False,
    }
    report = root / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if errors:
        for error in errors:
            print(f"PRAXELTA_HYGIENE_ERROR: {error}", file=sys.stderr)
        return 1
    print("PRAXELTA_HYGIENE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
