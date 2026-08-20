#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

TEXT_SUFFIXES = {
    ".md",
    ".html",
    ".htm",
    ".json",
    ".js",
    ".css",
    ".txt",
    ".yml",
    ".yaml",
    ".py",
}
SKIP_PREFIXES = {".git", "audit", "reports"}
POLICY_EVIDENCE_PATHS = {
    "BRAND_CANON.md",
    "PROJECT_IDENTITY.md",
    "brand_registry.json",
    "governance/EPHEMERAL_WORKFLOW_RETIREMENT_V1.json",
    "governance/REPOSITORY_METADATA_RECEIPT.json",
}
ALLOWED_MARKERS = {
    "LEGACY_COMPATIBILITY_ONLY",
    "REJECTED_COMMON_NAME",
    "историческ",
    "устарел",
    "старое название",
    "запрещ",
    "не использ",
    "перенаправ",
}
ACTIVE_HINTS = {
    "<title",
    "<h1",
    "<meta",
    "название",
    "бренд",
    "brand",
    "description",
    "публичная витрина",
    "услуги",
    "заказать",
    "оставить заявку",
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    text: str
    classification: str


def is_skipped(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return bool(relative.parts and relative.parts[0] in SKIP_PREFIXES)


def has_allowed_marker(line: str) -> bool:
    folded = line.casefold()
    return any(marker.casefold() in folded for marker in ALLOWED_MARKERS)


def is_policy_evidence_path(relative: str) -> bool:
    return relative in POLICY_EVIDENCE_PATHS


def is_negative_enforcement(line: str, relative: str = "") -> bool:
    """Recognize code/tests that reject a legacy name instead of presenting it.

    Public HTML/JSON is never exempted by this function.  A matching token in a
    ``tests/`` fixture is allowed because it is input for a negative test, while
    executable validators are allowed only when the same line contains an
    explicit negative assertion such as ``not in`` plus a legacy/forbidden
    diagnostic.  This keeps strict scanning of public surfaces unchanged.
    """

    folded = line.casefold().strip()
    grep_rejection = (
        (folded.startswith("! grep") or folded.startswith("if ! grep"))
        and ("-eq" in folded or "-e" in folded)
    )
    compiled_rejection = (
        ("forbidden" in folded or "rejected" in folded)
        and ("re.compile" in folded or "regexp" in folded)
    )
    negative_assertion = (
        "not in" in folded
        and ("require(" in folded or "assert " in folded)
        and any(
            marker in folded
            for marker in (
                "legacy",
                "forbidden",
                "old public",
                "устар",
                "запрещ",
            )
        )
    )
    negative_test_fixture = relative.startswith("tests/")
    return (
        grep_rejection
        or compiled_rejection
        or negative_assertion
        or negative_test_fixture
    )


def looks_active(line: str) -> bool:
    folded = line.casefold().strip()
    return folded.startswith("#") or any(hint in folded for hint in ACTIVE_HINTS)


def audit(root: Path) -> list[Finding]:
    pattern = re.compile(
        r"(?<![\w-])(?:поток|potok)(?![\w-])",
        re.IGNORECASE,
    )
    findings: list[Finding] = []
    for path in root.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.casefold() not in TEXT_SUFFIXES
            or is_skipped(path, root)
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(root).as_posix()
        for number, line in enumerate(text.splitlines(), start=1):
            if not pattern.search(line):
                continue
            if (
                is_policy_evidence_path(relative)
                or has_allowed_marker(line)
                or is_negative_enforcement(line, relative)
            ):
                classification = "ALLOWED_LEGACY_OR_POLICY"
            elif looks_active(line):
                classification = "ACTIVE_VIOLATION"
            else:
                classification = "REVIEW_REQUIRED"
            findings.append(
                Finding(relative, number, line.strip()[:400], classification)
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report", default="brand-audit-report.json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    findings = audit(root)
    active = [
        item for item in findings if item.classification == "ACTIVE_VIOLATION"
    ]
    review = [
        item for item in findings if item.classification == "REVIEW_REQUIRED"
    ]
    payload = {
        "schema_version": 1,
        "canonical_brand": "ПРАКСЕЛЬТА / PRAXELTA",
        "status": "FAIL" if active else ("REVIEW" if review else "PASS"),
        "active_violation_count": len(active),
        "review_required_count": len(review),
        "finding_count": len(findings),
        "findings": [asdict(item) for item in findings],
    }
    report = root / args.report
    report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "status",
                    "active_violation_count",
                    "review_required_count",
                    "finding_count",
                )
            },
            ensure_ascii=False,
        )
    )
    if args.strict and active:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
