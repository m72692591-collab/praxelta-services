#!/usr/bin/env python3
"""Zero-budget, deterministic agents for the PRAXELTA travel prelaunch.

The agents never register accounts, accept terms, publish content, spend money,
collect customer data, or expose affiliate links. They monitor public surfaces,
validate safety gates, prepare one daily content draft, and produce a single
machine-readable status artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CONFIG_PATH = Path("operations/travel-selection/free-agents-config.json")
CONTENT_PACK_PATH = Path("travel-pilot-content-pack.json")

FORBIDDEN_JS_PRIMITIVES = (
    "fetch(",
    "XMLHttpRequest",
    "sendBeacon",
    "WebSocket",
    "localStorage",
    "sessionStorage",
    "document.cookie",
)

SECRET_PATTERNS = {
    "telegram_bot_token": re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    "github_pat": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "private_key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
}

TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "audit",
    "reports",
}


@dataclass(frozen=True)
class AgentResult:
    agent_id: str
    status: str
    critical: bool
    summary: str
    details: tuple[str, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunReport:
    schema_version: int
    project: str
    mode: str
    status: str
    generated_at_utc: str
    source_commit: str
    free_runtime: str
    agents: tuple[dict[str, Any], ...]
    results: tuple[dict[str, Any], ...]
    production_gates: dict[str, bool]
    hard_off_switches: dict[str, bool]
    daily_draft: dict[str, Any]
    next_safe_actions: tuple[str, ...]
    warnings: tuple[str, ...]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        yield path


def check_required_files(root: Path, config: dict[str, Any]) -> AgentResult:
    required = [root / item for item in config.get("required_public_files", [])]
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing:
        return AgentResult(
            "orchestrator",
            "FAIL",
            True,
            "Не хватает обязательных файлов публичного travel-контура.",
            tuple(missing),
            {"required": len(required), "missing": len(missing)},
        )
    return AgentResult(
        "orchestrator",
        "PASS",
        True,
        "Обязательные файлы travel-контура присутствуют.",
        metrics={"required": len(required), "missing": 0},
    )


def check_public_security(root: Path) -> AgentResult:
    failures: list[str] = []
    checked = 0

    for name in ("travel-selection.html", "travel-pilot.html"):
        path = root / name
        if not path.exists():
            failures.append(f"missing {name}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for marker in (
            "connect-src 'none'",
            "form-action 'none'",
            '<meta name="viewport"',
            '<link rel="canonical"',
        ):
            if marker not in text:
                failures.append(f"{name}: missing {marker}")

    for name in ("travel-selection.js", "travel-pilot.js"):
        path = root / name
        if not path.exists():
            failures.append(f"missing {name}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for primitive in FORBIDDEN_JS_PRIMITIVES:
            if primitive in text:
                failures.append(f"{name}: forbidden primitive {primitive}")
        if "http://" in text or "https://" in text:
            failures.append(f"{name}: external URL embedded in browser code")
        if "innerHTML" in text or "insertAdjacentHTML" in text:
            failures.append(f"{name}: unsafe DOM HTML insertion")

    for name in (
        "travel-selection-privacy.html",
        "travel-selection-terms.html",
        "travel-selection-disclosure.html",
    ):
        path = root / name
        if not path.exists():
            failures.append(f"missing {name}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8").casefold()
        if "праксельта" not in text:
            failures.append(f"{name}: canonical brand absent")

    status = "FAIL" if failures else "PASS"
    return AgentResult(
        "security_gate",
        status,
        True,
        (
            "Публичный travel-контур не содержит сетевой отправки и скрытого хранения."
            if not failures
            else "Нарушены обязательные ограничения публичного travel-контура."
        ),
        tuple(failures),
        {"files_checked": checked, "violations": len(failures)},
    )


def check_repository_secrets(root: Path) -> AgentResult:
    findings: list[str] = []
    checked = 0
    for path in iter_text_files(root):
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(root).as_posix()
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{relative}: {label}")
    return AgentResult(
        "security_gate",
        "FAIL" if findings else "PASS",
        True,
        (
            "Секреты и приватные ключи в публичных текстовых файлах не найдены."
            if not findings
            else "В публичном репозитории обнаружены секретоподобные значения."
        ),
        tuple(findings),
        {"files_checked": checked, "findings": len(findings)},
    )


def validate_content_pack(root: Path) -> tuple[AgentResult, list[dict[str, Any]]]:
    path = root / CONTENT_PACK_PATH
    failures: list[str] = []
    drafts: list[dict[str, Any]] = []
    if not path.exists():
        failures.append(f"missing {CONTENT_PACK_PATH}")
    else:
        try:
            payload = load_json(path)
            if payload.get("status") != "DRAFT_NO_SEND":
                failures.append("content pack status must be DRAFT_NO_SEND")
            if payload.get("ad_spend_rub") != 0:
                failures.append("content pack ad_spend_rub must be 0")
            rules = payload.get("rules") or {}
            for key in (
                "real_prices_allowed",
                "affiliate_links_allowed",
                "automatic_posting_allowed",
            ):
                if rules.get(key) is not False:
                    failures.append(f"content rule must remain false: {key}")
            raw_drafts = payload.get("drafts")
            if not isinstance(raw_drafts, list):
                failures.append("drafts must be a list")
            else:
                drafts = [item for item in raw_drafts if isinstance(item, dict)]
                if len(drafts) < 14:
                    failures.append("at least 14 zero-budget drafts are required")
                for index, draft in enumerate(drafts, 1):
                    if draft.get("status") != "DRAFT_NO_SEND":
                        failures.append(f"draft {index}: status drift")
                    if not str(draft.get("title", "")).strip():
                        failures.append(f"draft {index}: title missing")
                    if not str(draft.get("body", "")).strip():
                        failures.append(f"draft {index}: body missing")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(str(exc))

    return (
        AgentResult(
            "content_draft_agent",
            "FAIL" if failures else "PASS",
            True,
            (
                "Контент-пакет безопасен и остаётся черновиком без отправки."
                if not failures
                else "Контент-пакет не прошёл безопасную проверку."
            ),
            tuple(failures),
            {"draft_count": len(drafts), "violations": len(failures)},
        ),
        drafts,
    )


def check_live_urls(
    config: dict[str, Any], *, offline: bool, timeout_seconds: int = 20
) -> AgentResult:
    urls = [str(item) for item in config.get("public_urls", [])]
    if offline:
        return AgentResult(
            "public_surface_monitor",
            "WARN",
            False,
            "Сетевая проверка пропущена в offline-режиме.",
            metrics={"configured_urls": len(urls), "checked": 0},
        )

    failures: list[str] = []
    passed = 0
    latencies: list[int] = []
    for url in urls:
        started = time.monotonic()
        request = Request(
            url,
            headers={
                "User-Agent": "PRAXELTA-Free-Agents/1.0 (+GitHub Actions)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                body = response.read(512_000).decode("utf-8", errors="ignore")
                status = int(getattr(response, "status", 200))
            latency_ms = round((time.monotonic() - started) * 1000)
            latencies.append(latency_ms)
            if status != 200:
                failures.append(f"{url}: HTTP {status}")
            elif "ПРАКСЕЛЬТА" not in body:
                failures.append(f"{url}: canonical brand absent in live HTML")
            else:
                passed += 1
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            failures.append(f"{url}: {type(exc).__name__}")

    return AgentResult(
        "public_surface_monitor",
        "WARN" if failures else "PASS",
        False,
        (
            "Все настроенные публичные страницы отвечают и содержат канонический бренд."
            if not failures
            else "Часть сетевых проверок не подтверждена; локальные safety-gates продолжают действовать."
        ),
        tuple(failures),
        {
            "configured_urls": len(urls),
            "passed": passed,
            "failed": len(failures),
            "max_latency_ms": max(latencies) if latencies else None,
        },
    )


def production_gate_state(config: dict[str, Any]) -> tuple[dict[str, bool], dict[str, bool]]:
    gates = {
        str(name): bool(os.getenv(str(name), "").strip())
        for name in config.get("production_gates", [])
    }
    hard_off = {
        str(name): os.getenv(str(name), "false").strip().casefold()
        not in {"1", "true", "yes", "on", "да"}
        for name in config.get("hard_off_switches", [])
    }
    return gates, hard_off


def check_commercial_readiness(
    gates: dict[str, bool], hard_off: dict[str, bool]
) -> AgentResult:
    missing = [name for name, configured in gates.items() if not configured]
    unsafe = [name for name, is_off in hard_off.items() if not is_off]
    details = [f"WAITING_FOR_OWNER_ACCESS: {name}" for name in missing]
    details.extend(f"UNSAFE_SWITCH_ENABLED: {name}" for name in unsafe)

    if unsafe:
        status = "FAIL"
        critical = True
        summary = "Один или несколько production-переключателей включены без полного gate."
    elif missing:
        status = "WARN"
        critical = False
        summary = "Технический prelaunch готов; production ожидает личные внешние доступы владельца."
    else:
        status = "PASS"
        critical = False
        summary = "Все внешние идентификаторы присутствуют; перед включением нужен отдельный production review."

    return AgentResult(
        "commercial_readiness",
        status,
        critical,
        summary,
        tuple(details),
        {
            "configured_gates": sum(1 for value in gates.values() if value),
            "total_gates": len(gates),
            "hard_off_switches_safe": sum(1 for value in hard_off.values() if value),
            "hard_off_switches_total": len(hard_off),
        },
    )


def choose_daily_draft(
    drafts: list[dict[str, Any]], *, run_date: date
) -> dict[str, Any]:
    if not drafts:
        return {
            "status": "UNAVAILABLE",
            "date": run_date.isoformat(),
            "title": "Контент-пакет не прошёл проверку",
            "body": "Автоматическая публикация запрещена.",
            "cta": "Исправить контент-пакет",
        }
    anchor = date(2026, 8, 19)
    index = (run_date.toordinal() - anchor.toordinal()) % len(drafts)
    source = drafts[index]
    return {
        "status": "DRAFT_NO_SEND",
        "date": run_date.isoformat(),
        "source_index": index,
        "source_day": source.get("day"),
        "format": source.get("format"),
        "title": source.get("title"),
        "body": source.get("body"),
        "cta": source.get("cta"),
        "automatic_posting": False,
        "owner_review_required": True,
    }


def overall_status(results: Iterable[AgentResult]) -> str:
    result_list = list(results)
    if any(item.status == "FAIL" and item.critical for item in result_list):
        return "FAIL"
    if any(item.status in {"FAIL", "WARN"} for item in result_list):
        return "DEGRADED"
    return "PASS"


def safe_actions(gates: dict[str, bool]) -> tuple[str, ...]:
    actions = [
        "Использовать публичный browser-only demo и страницу безопасного запроса пилота.",
        "Брать один контентный материал из daily-content-draft.md и публиковать только после человеческой проверки.",
        "Не включать платную рекламу до первой подтверждённой органической комиссии.",
    ]
    if not gates.get("TELEGRAM_BOT_TOKEN", False):
        actions.append("Создать личного Telegram-бота через BotFather и сохранить токен только в локальном .env.")
    if not gates.get("TRAVELPAYOUTS_TOKEN", False):
        actions.append("Лично принять условия Travelpayouts, создать Project и сохранить токен только локально.")
    if not gates.get("LEGAL_RELEASE_ID", False):
        actions.append("Утвердить налоговую, персональную и рекламную схему до реальных партнёрских ссылок.")
    return tuple(actions)


def render_markdown(report: RunReport) -> str:
    lines = [
        "<!-- PRAXELTA_TRAVEL_FREE_AGENTS_STATUS -->",
        "# ПРАКСЕЛЬТА Travel — бесплатные агенты",
        "",
        f"**Статус:** `{report.status}`  ",
        f"**Обновлено:** `{report.generated_at_utc}`  ",
        f"**Commit:** `{report.source_commit}`  ",
        f"**Режим:** `{report.mode}`",
        "",
        "## Агенты",
        "",
        "| Агент | Статус | Результат |",
        "|---|---:|---|",
    ]
    for item in report.results:
        summary = str(item["summary"]).replace("|", "\\|")
        lines.append(f"| `{item['agent_id']}` | **{item['status']}** | {summary} |")

    missing = [name for name, configured in report.production_gates.items() if not configured]
    lines.extend(["", "## Внешние gates", ""])
    if missing:
        lines.extend(f"- `WAITING_FOR_OWNER_ACCESS`: `{name}`" for name in missing)
    else:
        lines.append("- Все идентификаторы присутствуют; production всё равно требует отдельной проверки.")

    lines.extend(
        [
            "",
            "## Черновик дня — не отправлен",
            "",
            f"**{report.daily_draft.get('title', 'Нет черновика')}**",
            "",
            str(report.daily_draft.get("body", "")),
            "",
            f"CTA: {report.daily_draft.get('cta', '')}",
            "",
            "Статус: `DRAFT_NO_SEND`. Автоматическая публикация выключена.",
            "",
            "## Следующие безопасные действия",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report.next_safe_actions)
    lines.extend(
        [
            "",
            "## Ограничения",
            "",
            "Агенты не регистрируют аккаунты, не принимают оферты, не проходят OTP/CAPTCHA, не публикуют материалы, не тратят деньги и не сохраняют клиентские данные.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(output: Path, report: RunReport) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    (output / "status.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = render_markdown(report)
    (output / "status.md").write_text(markdown + "\n", encoding="utf-8")
    draft = report.daily_draft
    (output / "daily-content-draft.md").write_text(
        "\n".join(
            [
                "# ПРАКСЕЛЬТА Travel — черновик дня",
                "",
                f"Дата: `{draft.get('date', '')}`",
                "",
                f"Статус: `{draft.get('status', '')}`",
                "",
                f"## {draft.get('title', 'Нет черновика')}",
                "",
                str(draft.get("body", "")),
                "",
                f"**CTA:** {draft.get('cta', '')}",
                "",
                "Автоматическая публикация запрещена. Нужна проверка владельцем.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run(
    root: Path,
    output: Path,
    *,
    offline: bool = False,
    run_date: date | None = None,
) -> RunReport:
    config = load_json(root / CONFIG_PATH)
    file_result = check_required_files(root, config)
    security_result = check_public_security(root)
    secret_result = check_repository_secrets(root)
    content_result, drafts = validate_content_pack(root)
    live_result = check_live_urls(config, offline=offline)
    gates, hard_off = production_gate_state(config)
    commercial_result = check_commercial_readiness(gates, hard_off)
    results = (
        file_result,
        security_result,
        secret_result,
        content_result,
        live_result,
        commercial_result,
    )
    status = overall_status(results)
    today = run_date or datetime.now(timezone.utc).date()
    warnings = tuple(
        detail
        for result in results
        if result.status in {"WARN", "FAIL"}
        for detail in result.details
    )
    report = RunReport(
        schema_version=1,
        project=str(config.get("project", "ПРАКСЕЛЬТА · подбор поездки")),
        mode=str(config.get("mode", "ZERO_BUDGET_PRELAUNCH")),
        status=status,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        source_commit=os.getenv("GITHUB_SHA", "LOCAL_OR_UNKNOWN"),
        free_runtime="GitHub Actions public repository / standard library",
        agents=tuple(config.get("agents", [])),
        results=tuple(asdict(item) for item in results),
        production_gates=gates,
        hard_off_switches=hard_off,
        daily_draft=choose_daily_draft(drafts, run_date=today),
        next_safe_actions=safe_actions(gates),
        warnings=warnings,
    )
    write_report(output, report)
    return report


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="artifacts/travel-free-agents")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--date", type=parse_date)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output = (root / args.output).resolve()
    try:
        report = run(
            root,
            output,
            offline=args.offline,
            run_date=args.date,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1

    print(
        json.dumps(
            {
                "status": report.status,
                "generated_at_utc": report.generated_at_utc,
                "output": str(output),
                "daily_draft": report.daily_draft.get("title"),
            },
            ensure_ascii=False,
        )
    )
    return 1 if report.status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
