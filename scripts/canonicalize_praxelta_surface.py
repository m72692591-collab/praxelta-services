#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

FORBIDDEN = re.compile(r"(?<![\w-])(?:поток|potok)(?![\w-])", re.IGNORECASE)
TEXT_SUFFIXES = {".md", ".html", ".htm", ".json", ".js", ".css", ".txt", ".yml", ".yaml", ".py"}
SKIP_DIRS = {".git", "node_modules", "build", "dist", ".venv", "venv", "__pycache__", "audit", "reports"}
LEGACY_MARKERS = (
    "LEGACY_COMPATIBILITY_ONLY",
    "REJECTED_COMMON_NAME",
    "старое название",
    "устаревш",
    "историческ",
    "запрещ",
    "не использ",
    "перенаправ",
    "совместимост",
)
ACTIVE_MARKERS = (
    "<title",
    "<h1",
    "<h2",
    "<meta",
    "og:title",
    "og:description",
    "twitter:title",
    "twitter:description",
    "brand",
    "project_name",
    "product_name",
    "service_name",
    "description",
    "название",
    "бренд",
    "публичная витрина",
    "услуги",
    "оставить заявку",
    "заказать",
    "тариф",
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    classification: str
    before: str
    after: str


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        yield path


def has_marker(line: str, markers: tuple[str, ...]) -> bool:
    folded = line.casefold()
    return any(marker.casefold() in folded for marker in markers)


def replacement(match: re.Match[str]) -> str:
    value = match.group(0)
    return "PRAXELTA" if value[:1].isascii() else "ПРАКСЕЛЬТА"


def classify_line(line: str) -> str:
    if has_marker(line, LEGACY_MARKERS):
        return "ALLOWED_LEGACY_CONTEXT"
    if has_marker(line, ACTIVE_MARKERS) or line.lstrip().startswith("#"):
        return "ACTIVE_BRAND_DECLARATION"
    return "REVIEW_CONTEXT"


def process(root: Path, apply: bool) -> dict:
    findings: list[Finding] = []
    changed_files = 0
    for path in iter_text_files(root):
        try:
            original = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        lines = original.splitlines(keepends=True)
        changed = False
        for index, line in enumerate(lines, start=1):
            if not FORBIDDEN.search(line):
                continue
            classification = classify_line(line)
            updated = line
            if classification == "ACTIVE_BRAND_DECLARATION":
                updated = FORBIDDEN.sub(replacement, line)
                changed = changed or updated != line
                if apply:
                    lines[index - 1] = updated
            findings.append(
                Finding(
                    path=path.relative_to(root).as_posix(),
                    line=index,
                    classification=classification,
                    before=line.rstrip("\r\n")[:500],
                    after=updated.rstrip("\r\n")[:500],
                )
            )
        if apply and changed:
            path.write_text("".join(lines), encoding="utf-8")
            changed_files += 1

    remaining_active: list[Finding] = []
    remaining_review: list[Finding] = []
    for finding in findings:
        if finding.classification == "ACTIVE_BRAND_DECLARATION":
            if FORBIDDEN.search(finding.after):
                remaining_active.append(finding)
        elif finding.classification == "REVIEW_CONTEXT":
            remaining_review.append(finding)

    payload = {
        "schema_version": 2,
        "mode": "APPLY" if apply else "DRY_RUN",
        "canonical_brand_ru": "ПРАКСЕЛЬТА",
        "canonical_brand_latin": "PRAXELTA",
        "forbidden_active_names": ["Поток", "Potok"],
        "finding_count": len(findings),
        "changed_file_count": changed_files,
        "remaining_active_violation_count": len(remaining_active),
        "review_context_count": len(remaining_review),
        "mass_unclassified_replacement_used": False,
        "historical_lines_rewritten": False,
        "findings": [asdict(item) for item in findings],
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report", default="praxelta-brand-surface-report.json")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--strict-review", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    payload = process(root, args.apply)
    report = root / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "mode": payload["mode"],
        "finding_count": payload["finding_count"],
        "changed_file_count": payload["changed_file_count"],
        "remaining_active_violation_count": payload["remaining_active_violation_count"],
        "review_context_count": payload["review_context_count"],
    }, ensure_ascii=False))

    if payload["remaining_active_violation_count"]:
        return 1
    if args.strict_review and payload["review_context_count"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
