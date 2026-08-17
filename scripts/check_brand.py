#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "governance" / "brand.json"
TEXT_EXTENSIONS = {
    ".html", ".htm", ".md", ".txt", ".json", ".js", ".mjs", ".css",
    ".xml", ".yml", ".yaml", ".csv", ".py", ".toml", ".ini",
}
EXCLUDED_FILES = {
    "governance/BRAND_POLICY.md",
    "governance/brand.json",
    "scripts/check_brand.py",
}
EXCLUDED_DIRS = {
    ".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__",
}


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative in EXCLUDED_FILES:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            files.append(path)
    return sorted(files)


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    canonical = str(config["canonical_brand"])
    forbidden = [str(item) for item in config["forbidden_public_brand_forms"]]
    pattern = re.compile(
        r"(?<![\w-])(?:" + "|".join(re.escape(item) for item in forbidden) + r")(?![\w-])"
    )

    violations: list[str] = []
    canonical_occurrences = 0
    scanned = 0
    for path in iter_text_files():
        scanned += 1
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8-sig", errors="strict")
        canonical_occurrences += text.count(canonical)
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = pattern.search(line)
            if match:
                violations.append(
                    f"{relative}:{line_number}: forbidden brand form {match.group(0)!r}"
                )

    if canonical_occurrences == 0:
        violations.append("canonical brand ПРАКСЕЛЬТА is absent from public source files")

    print(
        json.dumps(
            {
                "scanned_files": scanned,
                "canonical_occurrences": canonical_occurrences,
                "violations": len(violations),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
