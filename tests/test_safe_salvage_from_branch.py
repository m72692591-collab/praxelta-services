from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/safe_salvage_from_branch.py"
spec = importlib.util.spec_from_file_location("praxelta_safe_salvage", SCRIPT)
assert spec and spec.loader
salvage = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = salvage
spec.loader.exec_module(salvage)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    ).stdout.strip()


def write(repo: Path, path: str, data: str | bytes) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        target.write_bytes(data)
    else:
        target.write_text(data, encoding="utf-8")


def commit(repo: Path, message: str) -> None:
    git(repo, "add", ".")
    git(repo, "commit", "-m", message)


def build(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    write(repo, "index.html", "<h1>ПРАКСЕЛЬТА</h1>\n")
    write(repo, "existing.md", "base\n")
    commit(repo, "base")
    git(repo, "branch", "source-base")

    git(repo, "switch", "-c", "source-head")
    write(repo, "new/page.html", "<h1>ПРАКСЕЛЬТА</h1>\n")
    write(repo, "existing.md", "changed\n")
    write(repo, "bad.html", "<h1>Поток</h1>\n")
    write(
        repo,
        "legacy.md",
        "# LEGACY_COMPATIBILITY_ONLY: старый адрес Potok\n",
    )
    write(repo, "secret.env", "TOKEN=x\n")
    write(repo, "docs/file.pdf", b"%PDF-safe")
    commit(repo, "source")
    git(repo, "switch", "source-base")
    return repo


def by_path(records):
    return {record.path: record for record in records}


def test_apply_copies_only_safe_target_only(tmp_path: Path) -> None:
    repo = build(tmp_path)
    summary, records = salvage.salvage(
        repo,
        "source-base",
        "source-head",
        "HEAD",
        25_000_000,
        True,
    )
    rows = by_path(records)
    assert (repo / "new/page.html").exists()
    assert rows["new/page.html"].status == "TARGET_ONLY_COPIED"
    assert rows["existing.md"].status == "DIVERGED"
    assert (repo / "existing.md").read_text(encoding="utf-8") == "base\n"
    assert rows["bad.html"].status == "BLOCKED_ACTIVE_NAME"
    assert not (repo / "bad.html").exists()
    assert rows["secret.env"].status == "BLOCKED"
    assert not (repo / "secret.env").exists()
    assert rows["legacy.md"].status == "TARGET_ONLY_COPIED"
    assert (repo / "legacy.md").exists()
    assert rows["docs/file.pdf"].status == "TARGET_ONLY_COPIED"
    assert (repo / "docs/file.pdf").exists()
    assert summary["current_files_overwritten"] is False
    assert summary["source_deletions_applied"] is False


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    repo = build(tmp_path)
    _summary, records = salvage.salvage(
        repo,
        "source-base",
        "source-head",
        "HEAD",
        25_000_000,
        False,
    )
    assert by_path(records)["new/page.html"].status == "TARGET_ONLY_READY"
    assert not (repo / "new/page.html").exists()


def test_forbidden_name_detection_respects_marked_history() -> None:
    assert salvage.text_has_forbidden_active_name("<h1>Поток</h1>") is True
    assert (
        salvage.text_has_forbidden_active_name(
            "LEGACY_COMPATIBILITY_ONLY: старый адрес Potok"
        )
        is False
    )
    assert (
        salvage.text_has_forbidden_active_name(
            '"rejected_active_names": ["Поток", "Potok"]'
        )
        is False
    )


def test_path_traversal_is_rejected() -> None:
    assert salvage.safe_path("safe/file.html")
    assert not salvage.safe_path("../escape")
    assert not salvage.safe_path("/absolute")
