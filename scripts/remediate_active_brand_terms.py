#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITOR_PATH = ROOT / "scripts" / "audit_brand_terms.py"
SPEC = importlib.util.spec_from_file_location("audit_brand_terms", AUDITOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load audit_brand_terms.py")
AUDITOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDITOR
SPEC.loader.exec_module(AUDITOR)

PATTERN = re.compile(r"(?<![\w-])(?:поток|potok)(?![\w-])", re.IGNORECASE)


def replacement(match: re.Match[str]) -> str:
    value = match.group(0)
    if re.fullmatch(r"поток", value, re.IGNORECASE):
        return "ПРАКСЕЛЬТА"
    return "PRAXELTA"


def migrate(root: Path, apply: bool) -> dict:
    findings = AUDITOR.audit(root)
    active = [item for item in findings if item.classification == "ACTIVE_VIOLATION"]
    by_path: dict[str, set[int]] = defaultdict(set)
    for item in active:
        by_path[item.path].add(item.line)

    files: list[dict] = []
    for relative, active_lines in sorted(by_path.items()):
        path = root / relative
        original = path.read_text(encoding="utf-8-sig")
        lines = original.splitlines(keepends=True)
        changed_lines: list[int] = []
        for index, line in enumerate(lines, start=1):
            if index not in active_lines:
                continue
            if AUDITOR.has_allowed_marker(line):
                continue
            updated = PATTERN.sub(replacement, line)
            if updated != line:
                lines[index - 1] = updated
                changed_lines.append(index)
        updated_text = "".join(lines)
        if updated_text != original and apply:
            path.write_text(updated_text, encoding="utf-8")
        files.append(
            {
                "path": relative,
                "active_lines": sorted(active_lines),
                "changed_lines": changed_lines,
                "changed": updated_text != original,
            }
        )

    payload = {
        "schema_version": 1,
        "mode": "apply" if apply else "dry_run",
        "canonical_brand": "ПРАКСЕЛЬТА / PRAXELTA",
        "active_violation_count_before": len(active),
        "file_count": len(files),
        "changed_file_count": sum(bool(item["changed"]) for item in files),
        "files": files,
        "historical_or_legacy_lines_modified": False,
        "mass_unclassified_replacement_used": False,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report", default="brand-remediation-report.json")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    payload = migrate(root, args.apply)
    report = root / args.report
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "mode": payload["mode"],
        "active_violation_count_before": payload["active_violation_count_before"],
        "changed_file_count": payload["changed_file_count"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
