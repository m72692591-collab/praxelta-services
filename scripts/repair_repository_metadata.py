#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOKEN_ENV_NAMES = (
    "TOKEN_PRAXELTA",
    "TOKEN_REPO_ADMIN",
    "TOKEN_GH_ADMIN",
    "TOKEN_GH_PAT",
    "TOKEN_GITHUB_PAT",
    "TOKEN_PAT",
    "TOKEN_DEFAULT",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_json(url: str, token: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        method=method,
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "PRAXELTA-metadata-repair",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"message": raw[:500]}
        return exc.code, data


def choose_tokens() -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name in TOKEN_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append((name, value))
    return result


def sanitize_message(data: dict[str, Any], status: int) -> str:
    message = str(data.get("message") or "HTTP request failed").strip()
    documentation = str(data.get("documentation_url") or "").strip()
    rendered = f"HTTP {status}: {message}"
    if documentation:
        rendered += f"; documentation={documentation}"
    return rendered[:1000]


def write_output(path: str | None, key: str, value: str) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--expected-description", required=True)
    parser.add_argument("--expected-homepage", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--github-output")
    args = parser.parse_args()

    url = f"https://api.github.com/repos/{args.repository}"
    attempts: list[dict[str, Any]] = []
    selected_source: str | None = None
    patch_succeeded = False

    for source, token in choose_tokens():
        status, data = request_json(
            url,
            token,
            method="PATCH",
            payload={
                "description": args.expected_description,
                "homepage": args.expected_homepage,
            },
        )
        success = status == 200
        attempts.append({
            "credential_source": source,
            "http_status": status,
            "success": success,
            "error": None if success else sanitize_message(data, status),
        })
        if success:
            selected_source = source
            patch_succeeded = True
            break

    read_token_source = selected_source
    read_token = None
    available = dict(choose_tokens())
    if selected_source:
        read_token = available.get(selected_source)
    if not read_token:
        for source, token in choose_tokens():
            read_token_source = source
            read_token = token
            break

    if read_token:
        get_status, current = request_json(url, read_token)
    else:
        get_status, current = 0, {"message": "No credential available"}

    actual_description = current.get("description") if get_status == 200 else None
    actual_homepage = current.get("homepage") if get_status == 200 else None
    actual_default_branch = current.get("default_branch") if get_status == 200 else None
    verified = (
        get_status == 200
        and actual_description == args.expected_description
        and actual_homepage == args.expected_homepage
        and actual_default_branch == "main"
    )

    if verified:
        status_text = "VERIFIED"
        error_summary = None
    elif not choose_tokens():
        status_text = "BLOCKED_NO_CREDENTIAL"
        error_summary = "No protected repository-administration credential is configured."
    elif patch_succeeded:
        status_text = "BLOCKED_FRESH_READ_MISMATCH"
        error_summary = (
            f"PATCH returned success but fresh GET mismatch: description={actual_description!r}, "
            f"homepage={actual_homepage!r}, default_branch={actual_default_branch!r}."
        )
    else:
        status_text = "BLOCKED_BY_REPOSITORY_ADMINISTRATION_PERMISSION"
        errors = [item["error"] for item in attempts if item.get("error")]
        error_summary = errors[-1] if errors else sanitize_message(current, get_status)

    receipt = {
        "schema_version": 2,
        "checked_at_utc": utc_now(),
        "repository": args.repository,
        "status": status_text,
        "patch_attempted": bool(attempts),
        "patch_succeeded": patch_succeeded,
        "selected_credential_source": selected_source,
        "fresh_read_credential_source": read_token_source,
        "expected_description": args.expected_description,
        "actual_description": actual_description,
        "expected_homepage": args.expected_homepage,
        "actual_homepage": actual_homepage,
        "expected_default_branch": "main",
        "actual_default_branch": actual_default_branch,
        "verified": verified,
        "error_summary": error_summary,
        "attempts": attempts,
        "secret_values_recorded": False,
        "credential_fingerprints_recorded": False,
        "file_content_changes_required": False,
        "next_gate": None if verified else "Provide repository-administration-capable credential or change Settings while authenticated, then rerun fresh API verification.",
    }
    path = Path(args.receipt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_output(args.github_output, "verified", "true" if verified else "false")
    write_output(args.github_output, "status", status_text)
    print(json.dumps({
        "status": status_text,
        "verified": verified,
        "actual_description": actual_description,
        "actual_homepage": actual_homepage,
        "actual_default_branch": actual_default_branch,
        "attempt_count": len(attempts),
    }, ensure_ascii=False))
    return 0 if verified else 1


if __name__ == "__main__":
    sys.exit(main())
