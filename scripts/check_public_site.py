"""Dependency-free preflight for the public static site."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://m72692591-collab.github.io/praxelta-services/"
ALLOWED_EMAILS = {
    "animatactus087@gmail.com",
    "m72692591@gmail.com",
    "grigorov555@mail.ru",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.canonical: list[str] = []
        self.metas: list[dict[str, str]] = []
        self.text: list[str] = []
        self.positive_tabindex: list[str] = []
        self.price_spans: list[tuple[str, str]] = []
        self.unlabelled_controls: list[str] = []
        self._label_depth = 0
        self._price_key: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: value or "" for key, value in attrs}
        if tag == "label":
            self._label_depth += 1
        if tag in {"a", "link", "script", "img"}:
            target = data.get("href") or data.get("src")
            if target:
                self.links.append(target)
        if tag == "link" and data.get("rel") == "canonical":
            self.canonical.append(data.get("href", ""))
        if tag == "meta":
            self.metas.append(data)
        if data.get("tabindex", "0").lstrip("-").isdigit() and int(data.get("tabindex", "0")) > 0:
            self.positive_tabindex.append(f"{tag}[tabindex={data['tabindex']}]")
        if "data-price-key" in data:
            self._price_key = data["data-price-key"]
        if tag in {"input", "select", "textarea"} and self._label_depth == 0:
            if not data.get("aria-label") and not data.get("aria-labelledby"):
                self.unlabelled_controls.append(f"{tag}[name={data.get('name', '')}]")

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._price_key:
            self._price_key = None
        if tag == "label" and self._label_depth:
            self._label_depth -= 1

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.text.append(value)
            if self._price_key:
                self.price_spans.append((self._price_key, value))


def nested(source: dict, key: str) -> object:
    value: object = source
    for part in key.split("."):
        value = value[part]  # type: ignore[index]
    return value


def money(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " ₽"


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    adjusted = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * adjusted[0] + 0.7152 * adjusted[1] + 0.0722 * adjusted[2]


def contrast_ratio(foreground: str, background: str) -> float:
    first, second = relative_luminance(foreground), relative_luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def main() -> int:
    errors: list[str] = []
    pages = sorted(ROOT.glob("*.html"))
    pricing = json.loads((ROOT / "pricing.json").read_text(encoding="utf-8"))
    category_registry = json.loads(
        (ROOT / "service-categories.json").read_text(encoding="utf-8")
    )
    campaigns = json.loads((ROOT / "campaigns-wave1.json").read_text(encoding="utf-8"))
    parsed: dict[str, PageParser] = {}

    for page in pages:
        raw = page.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(raw)
        parsed[page.name] = parser

        if not any(meta.get("name") == "viewport" for meta in parser.metas):
            fail(errors, f"{page.name}: missing viewport")
        if not any(meta.get("http-equiv") == "Content-Security-Policy" for meta in parser.metas):
            fail(errors, f"{page.name}: missing CSP")
        expected = BASE + ("" if page.name == "index.html" else page.name)
        if parser.canonical != [expected]:
            fail(errors, f"{page.name}: canonical {parser.canonical!r}, expected {expected}")
        if parser.positive_tabindex:
            fail(errors, f"{page.name}: positive tabindex {parser.positive_tabindex}")
        if page.name == "request-service.html" and parser.unlabelled_controls:
            fail(errors, f"{page.name}: unlabelled controls {parser.unlabelled_controls}")

        visible = " ".join(parser.text)
        for bad in ("Проксельта", "Пракселта", "Praxelta"):
            if bad in visible:
                fail(errors, f"{page.name}: forbidden public brand variant {bad}")
        for claim in (
            "без потери заявок",
            "гарантированно увеличим продажи",
            "приведём клиентов",
            "официальный партнёр Авито",
            "полный контроль вашего бизнеса",
        ):
            if claim.casefold() in visible.casefold():
                fail(errors, f"{page.name}: forbidden claim {claim}")

        for key, value in parser.price_spans:
            expected_price = nested(pricing, key)
            if not isinstance(expected_price, int) or value != money(expected_price):
                fail(errors, f"{page.name}: price {key}={value!r} does not match pricing.json")

        for link in parser.links:
            parsed_url = urlparse(link)
            if parsed_url.scheme in {"http", "https", "mailto", "tel"} or link.startswith("#"):
                continue
            target = unquote(parsed_url.path)
            if not target:
                continue
            if not (ROOT / target).exists():
                fail(errors, f"{page.name}: missing linked file {target}")

    text_suffixes = {".html", ".js", ".css", ".md", ".json", ".xml", ".txt"}
    ignored_parts = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "output", "tmp", "__pycache__"}
    all_public = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.casefold() in text_suffixes
        and not any(part in ignored_parts for part in path.parts)
    )
    for email in set(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", all_public, re.I)):
        if email.casefold() not in {item.casefold() for item in ALLOWED_EMAILS}:
            fail(errors, f"unexpected email in public root: {email}")
    for pattern in (
        r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]+",
        r"(?i)BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY",
    ):
        if re.search(pattern, all_public):
            fail(errors, f"secret-like pattern found: {pattern}")

    order_js = (ROOT / "order.js").read_text(encoding="utf-8")
    for required in ("mail.google.com", "mailto:", "navigator.clipboard"):
        if required not in order_js:
            fail(errors, f"order.js: missing {required}")
    for forbidden in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket"):
        if forbidden in order_js:
            fail(errors, f"order.js: unexpected network primitive {forbidden}")

    service_network_js = (ROOT / "service-network.js").read_text(encoding="utf-8")
    for forbidden in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "localStorage"):
        if forbidden in service_network_js:
            fail(errors, f"service-network.js: unexpected persistence/network primitive {forbidden}")
    request_page = (ROOT / "request-service.html").read_text(encoding="utf-8")
    for required in (
        "данные не отправляются",
        "processing",
        "transfer",
        "не более трёх мастеров",
        "Это не согласие на рекламу",
        "112",
    ):
        if required.casefold() not in request_page.casefold():
            fail(errors, f"request-service.html: missing safety/consent text {required}")

    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    if "@media print" not in css:
        fail(errors, "styles.css: missing print styles")
    if "focus-visible" not in css:
        fail(errors, "styles.css: missing keyboard focus styles")
    if "@media(max-width:760px)" not in css and "@media (max-width:760px)" not in css:
        fail(errors, "styles.css: missing local mobile breakpoint")
    for foreground, background, label in (
        ("#18212a", "#f4f0e7", "primary text on paper"),
        ("#626d76", "#f4f0e7", "muted text on paper"),
        ("#76500f", "#f4f0e7", "accent text on paper"),
        ("#d6b56b", "#18212a", "accent text on dark"),
        ("#f25322", "#18212a", "coral text on dark"),
    ):
        ratio = contrast_ratio(foreground, background)
        if ratio < 4.5:
            fail(errors, f"contrast: {label} is {ratio:.2f}:1, expected at least 4.5:1")

    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    if BASE + "sitemap.xml" not in robots:
        fail(errors, "robots.txt: missing sitemap URL")
    try:
        sitemap = ET.parse(ROOT / "sitemap.xml")
        locs = {node.text for node in sitemap.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
    except ET.ParseError as exc:
        fail(errors, f"sitemap.xml: invalid XML: {exc}")
        locs = set()
    for name in [
        "local-growth.html",
        "local-growth-commercial.html",
        "local-growth-checklist.html",
        "lead-marketplace.html",
        "request-service.html",
        "for-contractors.html",
        "for-suppliers.html",
        "lead-quality-policy.html",
        "service-network-safety.html",
        "service-network-privacy.html",
        "service-network-terms.html",
        "service-categories.html",
    ]:
        if BASE + name not in locs:
            fail(errors, f"sitemap.xml: missing {name}")

    wave_one = [item for item in category_registry["categories"] if item["wave"] == 1]
    if len(wave_one) != 6:
        fail(errors, f"service-categories.json: expected 6 wave-one categories, got {len(wave_one)}")
    category_codes = [item["code"] for item in category_registry["categories"]]
    if len(category_codes) != len(set(category_codes)):
        fail(errors, "service-categories.json: category codes must be unique")
    if "tv_electronics_repair" not in category_codes:
        fail(errors, "service-categories.json: missing television and electronics research category")
    for category in wave_one:
        for city_slug in ("saratov", "engels"):
            name = f"services-{city_slug}-{category['code']}.html"
            if not (ROOT / name).exists():
                fail(errors, f"missing generated city/category page {name}")
            if BASE + name not in locs:
                fail(errors, f"sitemap.xml: missing {name}")

    if len(campaigns.get("campaigns", [])) != 24:
        fail(errors, "campaigns-wave1.json: expected 24 campaign drafts")
    if campaigns.get("ad_spend") != "OFF" or campaigns.get("real_launches") != 0:
        fail(errors, "campaigns-wave1.json: AD_SPEND must be OFF and real_launches 0")
    for campaign in campaigns.get("campaigns", []):
        if campaign.get("forecast_budget") is not None:
            fail(errors, "campaign draft: forecast must stay empty until checked in an account")
        if campaign.get("status") != "DRAFT_NO_SPEND":
            fail(errors, "campaign draft: unexpected status")

    if errors:
        print("PUBLIC SITE PREFLIGHT: FAIL")
        for item in errors:
            print(f"- {item}")
        return 1
    print(f"PUBLIC SITE PREFLIGHT: PASS ({len(pages)} HTML pages)")
    print("Checks: links, files, sitemap, canonical, robots, CSP, mail composer, mobile/keyboard/print markers, form labels, WCAG text contrast, pricing, categories, campaigns OFF, brand, secrets, contacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
