from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "travel-pilot.html").read_text(encoding="utf-8")
JS = (ROOT / "travel-pilot.js").read_text(encoding="utf-8")
CSS = (ROOT / "travel-pilot.css").read_text(encoding="utf-8")


def test_pilot_is_indexable_but_explicitly_not_booking() -> None:
    assert '<meta name="robots" content="index,follow">' in HTML
    assert "это запрос на подбор, а не бронирование" in HTML.casefold()
    assert "не принимает оплату туриста" in HTML.casefold()
    assert "реальное бронирование пока не выполняется" in HTML.casefold()


def test_pilot_has_strict_static_csp() -> None:
    assert "connect-src 'none'" in HTML
    assert "form-action 'none'" in HTML
    assert 'onsubmit="return false"' in HTML


def test_all_controls_are_labelled() -> None:
    for control_id in (
        "pilot-departure",
        "pilot-type",
        "pilot-start",
        "pilot-end",
        "pilot-flexibility",
        "pilot-budget",
        "pilot-adults",
        "pilot-children",
        "pilot-documents",
        "pilot-priority",
        "pilot-note",
    ):
        assert f'id="{control_id}"' in HTML
        assert f'byId("{control_id}")' in JS


def test_javascript_has_no_network_or_persistence_primitives() -> None:
    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "sendBeacon",
        "WebSocket",
        "localStorage",
        "sessionStorage",
        "document.cookie",
    ):
        assert forbidden not in JS


def test_only_approved_contact_and_mail_composer_are_used() -> None:
    assert 'CONTACT_EMAIL = "animatactus087@gmail.com"' in JS
    assert "mailto:" in JS
    assert "http://" not in JS
    assert "https://" not in JS


def test_personal_and_payment_fields_are_not_requested() -> None:
    forbidden_names = (
        'name="surname"',
        'name="phone"',
        'name="passport"',
        'name="card"',
        'name="address"',
        'type="file"',
    )
    for forbidden in forbidden_names:
        assert forbidden not in HTML
    for required_warning in (
        "фамилии",
        "телефоны",
        "паспортные данные",
        "номера карт",
        "сведения о здоровье",
    ):
        assert required_warning in HTML.casefold()


def test_dom_output_uses_text_content_not_inner_html() -> None:
    assert ".textContent" in JS
    assert "innerHTML" not in JS
    assert "insertAdjacentHTML" not in JS


def test_layout_has_accessibility_and_print_markers() -> None:
    assert "focus-visible" in CSS
    assert "@media (max-width:" in CSS
    assert "@media print" in CSS
