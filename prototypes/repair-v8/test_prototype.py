from html.parser import HTMLParser
from pathlib import Path
import re

HTML = Path(__file__).with_name("index.html").read_text(encoding="utf-8")


class StrictParser(HTMLParser):
    def error(self, message):  # pragma: no cover
        raise AssertionError(message)


def test_html_parses():
    StrictParser().feed(HTML)


def test_all_product_views_are_present():
    for view in ("home", "request", "parts", "pay", "master"):
        assert f'data-view="{view}"' in HTML


def test_demo_has_no_network_routes():
    assert not re.search(r"https?://", HTML, re.IGNORECASE)
    for token in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon"):
        assert token not in HTML


def test_no_card_or_secret_collection():
    lowered = HTML.lower()
    for forbidden in ("name=\"pan\"", "name=\"cvv\"", "name=\"cvc\"", "secretkey", "terminalkey"):
        assert forbidden not in lowered


def test_transparency_and_payment_disclosures_exist():
    for text in (
        "Публичная цена",
        "Партнёрская цена",
        "не добавляется к цене",
        "Номер карты и CVV не вводятся",
        "Демо завершено — деньги не списывались",
    ):
        assert text in HTML


def test_prototype_is_clearly_non_production():
    assert "НЕТ РЕАЛЬНЫХ ПЛАТЕЖЕЙ И ОТПРАВКИ ДАННЫХ" in HTML
    assert "демо-интерфейс" in HTML
