from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from agents import travel_free_agents as agents

ROOT = Path(__file__).resolve().parents[1]
CONFIG = agents.load_json(ROOT / agents.CONFIG_PATH)


def test_required_travel_files_are_present() -> None:
    result = agents.check_required_files(ROOT, CONFIG)
    assert result.status == "PASS"
    assert result.critical is True
    assert result.metrics["missing"] == 0


def test_public_travel_javascript_has_no_network_or_storage() -> None:
    result = agents.check_public_security(ROOT)
    assert result.status == "PASS", result.details
    assert result.metrics["violations"] == 0


def test_public_repository_has_no_real_secret_patterns() -> None:
    result = agents.check_repository_secrets(ROOT)
    assert result.status == "PASS", result.details
    assert result.metrics["findings"] == 0


def test_content_pack_remains_draft_only() -> None:
    result, drafts = agents.validate_content_pack(ROOT)
    assert result.status == "PASS", result.details
    assert len(drafts) >= 14
    assert all(item["status"] == "DRAFT_NO_SEND" for item in drafts)


def test_daily_draft_is_deterministic_and_not_sent() -> None:
    _, drafts = agents.validate_content_pack(ROOT)
    first = agents.choose_daily_draft(drafts, run_date=date(2026, 8, 19))
    repeated = agents.choose_daily_draft(drafts, run_date=date(2026, 8, 19))
    assert first == repeated
    assert first["status"] == "DRAFT_NO_SEND"
    assert first["automatic_posting"] is False
    assert first["owner_review_required"] is True


def test_missing_external_access_is_warning_not_fake_failure(monkeypatch) -> None:
    for name in CONFIG["production_gates"]:
        monkeypatch.delenv(name, raising=False)
    for name in CONFIG["hard_off_switches"]:
        monkeypatch.delenv(name, raising=False)
    gates, switches = agents.production_gate_state(CONFIG)
    result = agents.check_commercial_readiness(gates, switches)
    assert result.status == "WARN"
    assert result.critical is False
    assert all(value is False for value in gates.values())
    assert all(value is True for value in switches.values())


def test_unsafe_switch_is_critical_failure(monkeypatch) -> None:
    monkeypatch.setenv("REAL_MONEY", "true")
    gates, switches = agents.production_gate_state(CONFIG)
    result = agents.check_commercial_readiness(gates, switches)
    assert result.status == "FAIL"
    assert result.critical is True
    assert any("REAL_MONEY" in detail for detail in result.details)


def test_gate_report_never_contains_secret_values(monkeypatch) -> None:
    secret = "not-a-real-token-value-keep-private"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", secret)
    gates, _ = agents.production_gate_state(CONFIG)
    rendered = json.dumps(gates, ensure_ascii=False)
    assert gates["TELEGRAM_BOT_TOKEN"] is True
    assert secret not in rendered


def test_offline_run_writes_all_artifacts(tmp_path, monkeypatch) -> None:
    for name in CONFIG["production_gates"]:
        monkeypatch.delenv(name, raising=False)
    for name in CONFIG["hard_off_switches"]:
        monkeypatch.delenv(name, raising=False)
    output = tmp_path / "agents-output"
    report = agents.run(
        ROOT,
        output,
        offline=True,
        run_date=date(2026, 8, 19),
    )
    assert report.status == "DEGRADED"
    assert (output / "status.json").is_file()
    assert (output / "status.md").is_file()
    assert (output / "daily-content-draft.md").is_file()
    payload = json.loads((output / "status.json").read_text(encoding="utf-8"))
    assert payload["daily_draft"]["status"] == "DRAFT_NO_SEND"
    assert payload["hard_off_switches"]["REAL_MONEY"] is True
    assert "PRAXELTA_TRAVEL_FREE_AGENTS_STATUS" in (
        output / "status.md"
    ).read_text(encoding="utf-8")


def test_overall_status_prioritizes_critical_failures() -> None:
    pass_result = agents.AgentResult("one", "PASS", True, "ok")
    warn_result = agents.AgentResult("two", "WARN", False, "waiting")
    fail_result = agents.AgentResult("three", "FAIL", True, "blocked")
    assert agents.overall_status([pass_result]) == "PASS"
    assert agents.overall_status([pass_result, warn_result]) == "DEGRADED"
    assert agents.overall_status([pass_result, fail_result]) == "FAIL"
