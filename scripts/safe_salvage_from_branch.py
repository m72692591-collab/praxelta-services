#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Sequence

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".csv",
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".html",
    ".css",
    ".xml",
    ".sh",
    ".ps1",
    ".cmd",
}
SAFE_BINARY_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".svg"}
BLOCKED_FRAGMENTS = {
    ".env",
    "secret",
    "token",
    "credential",
    "session",
    "cookie",
    "private_key",
    "id_rsa",
    "keystore",
    ".db",
    ".sqlite",
    "password",
}
REJECTED_CYRILLIC_NAME = "".join(
    chr(code) for code in (0x043F, 0x043E, 0x0442, 0x043E, 0x043A)
)
REJECTED_LATIN_NAME = "".join(chr(code) for code in (112, 111, 116, 111, 107))
FORBIDDEN_ACTIVE_NAME = re.compile(
    rf"(?iu)(?<![а-яa-z0-9])({re.escape(REJECTED_CYRILLIC_NAME)}|"
    rf"{re.escape(REJECTED_LATIN_NAME)})(?![а-яa-z0-9])"
)
ALLOWED_LEGACY_MARKERS = (
    "legacy_compatibility_only",
    "rejected_active_name",
    "rejected_active_names",
    "запрещ",
    "устаревш",
    "старый адрес",
    "историческ",
    "перенаправ",
)


@dataclass(frozen=True)
class Record:
    path: str
    source_blob: str | None
    current_blob: str | None
    size_bytes: int | None
    sha256: str | None
    status: str
    reason: str


def run(
    args: Sequence[str],
    root: Path,
    *,
    allow_failure: bool = False,
    binary: bool = False,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        list(args),
        cwd=root,
        capture_output=True,
        check=False,
        text=not binary,
        encoding=None if binary else "utf-8",
        errors=None if binary else "replace",
    )
    if result.returncode and not allow_failure:
        raw = result.stderr or result.stdout or (b"" if binary else "")
        diagnostic = (
            raw.decode("utf-8", errors="replace")
            if isinstance(raw, bytes)
            else raw
        )
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(args)}\n"
            f"{diagnostic[:2000]}"
        )
    return result


def git(
    root: Path,
    *args: str,
    allow_failure: bool = False,
    binary: bool = False,
) -> subprocess.CompletedProcess:
    return run(
        ("git", *args),
        root,
        allow_failure=allow_failure,
        binary=binary,
    )


def resolve(root: Path, ref: str) -> str:
    return git(root, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()


def blob(root: Path, ref: str, path: str) -> str | None:
    result = git(root, "rev-parse", f"{ref}:{path}", allow_failure=True)
    value = result.stdout.strip() if isinstance(result.stdout, str) else ""
    return value if result.returncode == 0 and value else None


def read_blob(root: Path, ref: str, path: str) -> bytes:
    result = git(root, "show", f"{ref}:{path}", binary=True)
    return result.stdout


def safe_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\x00" not in value
    )


def changed_paths(root: Path, base: str, head: str) -> list[str]:
    raw = git(
        root,
        "diff",
        "--name-only",
        "--no-renames",
        base,
        head,
        "--",
    ).stdout
    return sorted({line.strip() for line in raw.splitlines() if line.strip()})


def blocked_reason(path: str) -> str:
    folded = path.casefold()
    if any(fragment in folded for fragment in BLOCKED_FRAGMENTS):
        return "sensitive path blocked"
    suffix = Path(path).suffix.casefold()
    if suffix not in TEXT_SUFFIXES | SAFE_BINARY_SUFFIXES:
        return f"unsupported suffix: {suffix or '<none>'}"
    return ""


def text_has_forbidden_active_name(text: str) -> bool:
    for line in text.splitlines():
        if not FORBIDDEN_ACTIVE_NAME.search(line):
            continue
        folded = line.casefold()
        if any(marker in folded for marker in ALLOWED_LEGACY_MARKERS):
            continue
        return True
    return False


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-salvage")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def salvage(
    root: Path,
    source_base: str,
    source_head: str,
    current_ref: str,
    max_bytes: int,
    apply: bool,
) -> tuple[dict, list[Record]]:
    base_sha = resolve(root, source_base)
    head_sha = resolve(root, source_head)
    current_sha = resolve(root, current_ref)
    records: list[Record] = []

    for path in changed_paths(root, base_sha, head_sha):
        if not safe_path(path):
            records.append(
                Record(path, None, None, None, None, "BLOCKED", "unsafe path")
            )
            continue

        source_blob = blob(root, head_sha, path)
        current_blob = blob(root, current_sha, path)

        if source_blob is None:
            records.append(
                Record(
                    path,
                    None,
                    current_blob,
                    None,
                    None,
                    "SOURCE_DELETION",
                    "deletion is never applied",
                )
            )
            continue
        if current_blob == source_blob:
            records.append(
                Record(
                    path,
                    source_blob,
                    current_blob,
                    None,
                    None,
                    "ALREADY_PRESENT",
                    "identical Git blob",
                )
            )
            continue
        if current_blob is not None:
            records.append(
                Record(
                    path,
                    source_blob,
                    current_blob,
                    None,
                    None,
                    "DIVERGED",
                    "current file is never overwritten",
                )
            )
            continue

        reason = blocked_reason(path)
        if reason:
            records.append(
                Record(path, source_blob, None, None, None, "BLOCKED", reason)
            )
            continue

        data = read_blob(root, head_sha, path)
        digest = hashlib.sha256(data).hexdigest()
        if len(data) > max_bytes:
            records.append(
                Record(
                    path,
                    source_blob,
                    None,
                    len(data),
                    digest,
                    "BLOCKED",
                    "size limit exceeded",
                )
            )
            continue

        if Path(path).suffix.casefold() in TEXT_SUFFIXES:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                records.append(
                    Record(
                        path,
                        source_blob,
                        None,
                        len(data),
                        digest,
                        "BLOCKED",
                        "invalid UTF-8 text",
                    )
                )
                continue
            if text_has_forbidden_active_name(text):
                records.append(
                    Record(
                        path,
                        source_blob,
                        None,
                        len(data),
                        digest,
                        "BLOCKED_ACTIVE_NAME",
                        "active rejected name found",
                    )
                )
                continue

        status = "TARGET_ONLY_READY"
        if apply:
            write_atomic(root / path, data)
            status = "TARGET_ONLY_COPIED"
        records.append(
            Record(
                path,
                source_blob,
                None,
                len(data),
                digest,
                status,
                "target-only file passed gates",
            )
        )

    counts: dict[str, int] = {}
    for record in records:
        counts[record.status] = counts.get(record.status, 0) + 1

    summary = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_base_sha": base_sha,
        "source_head_sha": head_sha,
        "current_sha": current_sha,
        "mode": "APPLY" if apply else "DRY_RUN",
        "counts": counts,
        "destructive_actions_performed": False,
        "current_files_overwritten": False,
        "source_deletions_applied": False,
        "forbidden_active_name_copied": False,
    }
    return summary, records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--source-base", required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--current-ref", default="HEAD")
    parser.add_argument("--max-bytes", type=int, default=25_000_000)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    summary, records = salvage(
        root,
        args.source_base,
        args.source_head,
        args.current_ref,
        args.max_bytes,
        args.apply,
    )
    payload = dict(summary)
    payload["records"] = [asdict(record) for record in records]
    output = root / args.manifest
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "counts": summary["counts"],
                "manifest": str(output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
