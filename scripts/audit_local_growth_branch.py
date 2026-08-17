#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

SAFE_TEXT_SUFFIXES = {
    ".html",
    ".css",
    ".js",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".xml",
}
PROTECTED_DIVERGED_PATHS = {
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "SECURITY.md",
    "index.html",
    "offer.html",
    "order.js",
    "payment-fail.html",
    "payment-success.html",
    "privacy.html",
    "refund.html",
    "sample.html",
    "sitemap.xml",
    "styles.css",
    "terms.html",
}
EXCLUDED_PATHS = {
    "HUMANITY_GATE_LOCAL_GROWTH_2026-08-13.json",
}
ABSOLUTE_WINDOWS_PATH = re.compile(r"(?i)(?:[A-Z]:\\|[A-Z]:/|\\\\[^\\]+\\[^\\]+)")
SECRET_MARKER = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key|cookie|session|otp)"
)


@dataclass(frozen=True)
class Record:
    path: str
    state: str
    current_blob: str | None
    historical_blob: str | None
    size_bytes: int
    action: str
    reason: str


class AuditError(RuntimeError):
    pass


def git(repo: Path, *args: str, binary: bool = False, timeout: int = 240):
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        if not detail:
            detail = completed.stdout.decode("utf-8", errors="replace").strip()
        raise AuditError(f"git {' '.join(args)} failed ({completed.returncode}): {detail}")
    return completed.stdout if binary else completed.stdout.decode("utf-8", errors="replace").strip()


def git_optional(repo: Path, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def blob_sha(repo: Path, ref: str, path: str) -> str | None:
    return git_optional(repo, "rev-parse", f"{ref}:{path}")


def blob_bytes(repo: Path, ref: str, path: str) -> bytes:
    return git(repo, "show", f"{ref}:{path}", binary=True)


def blob_size(repo: Path, ref: str, path: str) -> int:
    return int(git(repo, "cat-file", "-s", f"{ref}:{path}"))


def changed_paths(repo: Path, base_ref: str, historical_ref: str) -> list[str]:
    merge_base = git(repo, "merge-base", base_ref, historical_ref)
    raw = git(
        repo,
        "diff",
        "--no-renames",
        "--name-only",
        merge_base,
        historical_ref,
    )
    return sorted({line.strip() for line in raw.splitlines() if line.strip()})


def is_text_path(path: str) -> bool:
    return Path(path).suffix.casefold() in SAFE_TEXT_SUFFIXES


def inspect_text(data: bytes) -> tuple[bool, str]:
    if b"\x00" in data:
        return False, "binary_or_nul"
    text = data.decode("utf-8", errors="replace")
    if ABSOLUTE_WINDOWS_PATH.search(text):
        return False, "absolute_local_path"
    for line in text.splitlines():
        if SECRET_MARKER.search(line) and re.search(r"[:=]\s*['\"]?[^\s'\"]{8,}", line):
            return False, "possible_secret_value"
    return True, "safe_text"


def copy_target_only(repo: Path, historical_ref: str, path: str) -> tuple[bool, str]:
    if path in EXCLUDED_PATHS:
        return False, "explicitly_excluded_sensitive_receipt"
    if not is_text_path(path):
        if path.startswith("output/pdf/"):
            return False, "generated_pdf_requires_regeneration"
        return False, "non_text_file"
    data = blob_bytes(repo, historical_ref, path)
    safe, reason = inspect_text(data)
    if not safe:
        return False, reason
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return True, "copied_exact_target_only"


def audit(repo: Path, current_ref: str, historical_ref: str) -> dict:
    current_head = git(repo, "rev-parse", f"{current_ref}^{{commit}}")
    historical_head = git(repo, "rev-parse", f"{historical_ref}^{{commit}}")
    merge_base = git(repo, "merge-base", current_ref, historical_ref)

    records: list[Record] = []
    copied: list[str] = []
    blocked: list[str] = []

    for path in changed_paths(repo, current_ref, historical_ref):
        old_blob = blob_sha(repo, historical_ref, path)
        if old_blob is None:
            continue
        current_blob = blob_sha(repo, current_ref, path)
        size = blob_size(repo, historical_ref, path)
        if current_blob == old_blob:
            state = "ALREADY_PRESENT"
            action = "NONE"
            reason = "identical_blob"
        elif current_blob is None:
            state = "TARGET_ONLY"
            copied_ok, reason = copy_target_only(repo, historical_ref, path)
            if copied_ok:
                action = "COPIED_EXACT"
                copied.append(path)
            else:
                action = "BLOCKED_FOR_REVIEW"
                blocked.append(path)
        else:
            state = "DIVERGED"
            action = "PRESERVE_CURRENT_REVIEW_SEMANTICS"
            reason = (
                "protected_current_path"
                if path in PROTECTED_DIVERGED_PATHS
                else "semantic_comparison_required"
            )
            blocked.append(path)

        records.append(
            Record(
                path=path,
                state=state,
                current_blob=current_blob,
                historical_blob=old_blob,
                size_bytes=size,
                action=action,
                reason=reason,
            )
        )

    payload = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_ref": current_ref,
        "current_head": current_head,
        "historical_ref": historical_ref,
        "historical_head": historical_head,
        "merge_base": merge_base,
        "records": [asdict(record) for record in records],
        "summary": {
            "files": len(records),
            "already_present": sum(record.state == "ALREADY_PRESENT" for record in records),
            "target_only": sum(record.state == "TARGET_ONLY" for record in records),
            "diverged": sum(record.state == "DIVERGED" for record in records),
            "copied_exact": len(copied),
            "blocked_for_review": len(blocked),
        },
        "copied_files": copied,
        "blocked_paths": blocked,
        "destructive_actions_performed": False,
        "branch_deletion_performed": False,
        "external_publication_performed": False,
    }
    report_dir = repo / "docs/repository"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "LOCAL_GROWTH_SALVAGE.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Аудит старой ветки локального продвижения ПРАКСЕЛЬТЫ",
        "",
        f"- Текущая база: `{current_ref}` / `{current_head}`",
        f"- Историческая ветка: `{historical_ref}` / `{historical_head}`",
        f"- Файлов: **{len(records)}**",
        f"- Уже присутствует: **{payload['summary']['already_present']}**",
        f"- Target-only: **{payload['summary']['target_only']}**",
        f"- Diverged: **{payload['summary']['diverged']}**",
        f"- Точно скопировано: **{payload['summary']['copied_exact']}**",
        f"- Требует проверки: **{payload['summary']['blocked_for_review']}**",
        "",
        "| Состояние | Действие | Причина | Путь |",
        "|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            f"| `{record.state}` | `{record.action}` | `{record.reason}` | `{record.path}` |"
        )
    (report_dir / "LOCAL_GROWTH_SALVAGE.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--current-ref", default="HEAD")
    parser.add_argument("--historical-ref", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = audit(
        Path(args.repo).resolve(),
        args.current_ref,
        args.historical_ref,
    )
    print("[PRAXELTA] LOCAL GROWTH SALVAGE: PASS")
    for key, value in payload["summary"].items():
        print(f"[PRAXELTA] {key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
