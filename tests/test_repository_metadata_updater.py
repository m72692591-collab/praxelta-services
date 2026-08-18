from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/update_github_description.ps1"
LAUNCHER = ROOT / "RUN_UPDATE_GITHUB_DESCRIPTION.cmd"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_metadata_updater_files_exist() -> None:
    assert SCRIPT.is_file()
    assert LAUNCHER.is_file()


def test_exact_repository_and_metadata_are_pinned() -> None:
    text = read(SCRIPT)
    assert "m72692591-collab/praxelta-services" in text
    assert "Публичная витрина и рабочие материалы ПРАКСЕЛЬТЫ" in text
    assert "https://m72692591-collab.github.io/praxelta-services/" in text
    assert 'default_branch -ne "main"' in text


def test_patch_is_followed_by_fresh_get_and_exact_assertions() -> None:
    text = read(SCRIPT)
    assert text.count('"--method", "GET"') >= 2
    assert '"--method", "PATCH"' in text
    assert "Свежий API GET не подтвердил точный description" in text
    assert "Свежий API GET не подтвердил homepage" in text
    assert "PRAXELTA_REPOSITORY_METADATA=VERIFIED" in text


def test_no_secret_or_token_is_written_to_receipt() -> None:
    text = read(SCRIPT)
    assert "secrets_recorded = $false" in text
    assert "token_recorded = $false" in text
    assert "private_url_recorded = $false" in text
    forbidden = (
        "gh auth token",
        "GITHUB_TOKEN=",
        "Authorization: Bearer",
        "ConvertFrom-SecureString",
    )
    assert not [marker for marker in forbidden if marker in text]


def test_launcher_preserves_factual_exit_code() -> None:
    text = read(LAUNCHER).casefold()
    assert "update_github_description.ps1" in text
    assert "exit /b %code%" in text
    assert "executionpolicy bypass" in text
