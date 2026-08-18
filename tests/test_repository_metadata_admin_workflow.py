from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/repository-metadata-admin-update.yml"


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_exists_and_is_manual_only() -> None:
    value = text()
    assert WORKFLOW.is_file()
    assert "workflow_dispatch:" in value
    assert "pull_request:" not in value
    assert "push:" not in value
    assert "schedule:" not in value


def test_protected_environment_and_exact_secret_are_required() -> None:
    value = text()
    assert "environment: repository-administration" in value
    assert "secrets.PRAXELTA_REPO_ADMIN_TOKEN" in value
    assert "test -n \"$ADMIN_TOKEN\"" in value


def test_exact_repository_metadata_is_pinned() -> None:
    value = text()
    assert "m72692591-collab/praxelta-services" in value
    assert "Публичная витрина и рабочие материалы ПРАКСЕЛЬТЫ" in value
    assert "https://m72692591-collab.github.io/praxelta-services/" in value
    assert "EXPECTED_DEFAULT_BRANCH: main" in value


def test_patch_is_followed_by_fresh_api_read_and_exact_assertions() -> None:
    value = text()
    assert "--request PATCH" in value
    assert value.count('"https://api.github.com/repos/$REPOSITORY_SLUG"') >= 3
    assert "assert after['description'] == expected_description" in value
    assert "assert after['homepage'] == os.environ['EXPECTED_HOMEPAGE']" in value
    assert "assert after['default_branch'] == os.environ['EXPECTED_DEFAULT_BRANCH']" in value


def test_receipt_is_sanitized() -> None:
    value = text()
    assert "secrets_recorded': False" in value
    assert "token_recorded': False" in value
    assert "private_url_recorded': False" in value
    receipt_block = value.split("receipt = {", 1)[1].split("Path('repository-metadata-evidence", 1)[0]
    assert "ADMIN_TOKEN" not in receipt_block


def test_raw_api_responses_are_not_uploaded() -> None:
    value = text()
    upload = value.split("Upload immutable sanitized evidence", 1)[1]
    assert "repository-metadata-evidence" in upload
    assert "$RUNNER_TEMP/before.json" not in upload
    assert "$RUNNER_TEMP/after.json" not in upload
    assert "$RUNNER_TEMP/patch-response.json" not in upload
