from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://m72692591-collab.github.io/praxelta-services/"
REGISTRY = json.loads((ROOT / "service-categories.json").read_text(encoding="utf-8"))

CITY_COPY = {
    "Саратов": {
        "slug": "saratov",
        "note": "В заявке отдельно уточняем район и удобное время. Мастер принимает задачу только в пределах своего фактического покрытия.",
    },
    "Энгельс": {
        "slug": "engels",
        "note": "Энгельс учитывается как отдельная зона работы: доступность мастера в Саратове не означает автоматическую готовность к выезду через Волгу.",
    },
}

NAV = """<header class="site-header market-header">
  <a class="brand" href="index.html" aria-label="ПРАКСЕЛЬТА — на главную">ПРАКСЕЛЬТА</a>
  <nav aria-label="ПРАКСЕЛЬТА Маркет"><a href="service-categories.html">Категории</a><a href="request-service.html">Клиентам</a><a href="for-contractors.html">Мастерам</a><a href="for-suppliers.html">Поставщикам</a></nav>
</header>"""

FOOTER = """<footer class="market-footer"><p><strong>ПРАКСЕЛЬТА Маркет</strong><br>Подготовка пилота. Реальные заявки и рекламные расходы выключены.</p><nav><a href="service-network-safety.html">Безопасность</a><a href="service-network-privacy.html">Данные</a><a href="service-network-terms.html">Условия</a></nav></footer>"""


def page(filename: str, title: str, description: str, body: str) -> None:
    document = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; script-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'self'; form-action 'none'; upgrade-insecure-requests; block-all-mixed-content">
<meta name="referrer" content="no-referrer"><meta name="description" content="{html.escape(description)}"><title>{html.escape(title)} — ПРАКСЕЛЬТА</title>
<link rel="canonical" href="{BASE_URL}{filename}"><link rel="icon" type="image/png" href="praxelta-icon.png"><link rel="stylesheet" href="styles.css"></head>
<body>{NAV}<main class="local-page market-page">{body}</main>{FOOTER}</body></html>
"""
    (ROOT / filename).write_text(document, encoding="utf-8")


def render_catalog(categories: list[dict[str, object]]) -> list[str]:
    cards = []
    for category in categories:
        problems = ", ".join(str(item) for item in category["typical_problems"][:2])
        cities = category["launch_cities"]
        city_links = " ".join(
            f'<a href="services-{CITY_COPY[str(city)]["slug"]}-{category["code"]}.html">{city}</a>'
            for city in cities
        )
        cards.append(
            f"<article><p class=\"eyebrow\">Волна {category['wave']} · {category['risk']}</p>"
            f"<h3>{html.escape(str(category['name']))}</h3><p>{html.escape(problems)}.</p>"
            f"<p class=\"category-links\">{city_links or 'Готовим требования и пул мастеров'}</p></article>"
        )
    body = """<section class="local-hero market-hero"><p class="eyebrow">ПРАКСЕЛЬТА Маркет</p><h1>Шесть категорий для первого пилота</h1><p class="lead">Для каждой услуги отдельно проверяем риски, вопросы клиенту, документы мастера, районы выезда и резерв на случай отказа.</p><p class="pilot-badge">Волна 1 · Саратов и Энгельс · рекламные расходы выключены</p></section>"""
    body += f'<section><p class="eyebrow">Категории</p><h2>Что готовим к пилоту</h2><div class="category-grid">{"".join(cards)}</div></section>'
    body += """<section class="safe-promise"><p class="eyebrow">SUPPLY_READY_GATE</p><h2>Страница готова — реклама ещё не запущена</h2><p>Сначала нужны минимум три активных мастера или один надёжный сервисный партнёр, реальное покрытие районов, документы по категории и резервный исполнитель. Пока этого нет, система продолжает набор мастеров и не тратит бюджет.</p></section>"""
    page("service-categories.html", "Категории локальных услуг", "Категории ПРАКСЕЛЬТА Маркет и статус подготовки пилота.", body)
    return ["service-categories.html"]


def render_city_category(category: dict[str, object], city: str) -> str:
    city_data = CITY_COPY[city]
    filename = f"services-{city_data['slug']}-{category['code']}.html"
    problems = category["typical_problems"]
    questions = category["required_questions"]
    safety = category["safety_rules"]
    body = f"""<section class="local-hero market-hero"><p class="eyebrow">{city} · {html.escape(str(category['name']))}</p><h1>Опишите задачу — мы проверим, кому её можно предложить</h1><p class="lead">Например: {html.escape(str(problems[0]))}. Контакт не показывается мастеру до принятия заявки и согласия клиента.</p><div class="hero-actions"><a class="button primary" href="request-service.html?ref=service_{city_data['slug']}_{category['code']}">Открыть тестовую форму</a><a class="button" href="for-contractors.html">Условия для мастеров</a></div><p class="pilot-badge">Подготовка пилота · реальные заявки и платежи выключены</p></section>
<section><p class="eyebrow">Что уточним</p><h2>Чтобы мастер понял задачу до звонка</h2><ul class="check-list">{''.join(f'<li>{html.escape(str(item))}</li>' for item in questions)}</ul><p>{html.escape(str(city_data['note']))}</p></section>
<section class="two-col"><article><p class="eyebrow">Типовые задачи</p><h2>Что можно описать</h2><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in problems)}</ul></article><article><p class="eyebrow">Безопасность</p><h2>Когда обычный подбор останавливается</h2><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in safety)}</ul></article></section>
<section><p class="eyebrow">Как идёт подбор</p><h2>Сначала один подходящий мастер</h2><ol class="timeline"><li>Проверяем контакт, город, категорию, дубль и согласие.</li><li>Показываем мастеру обезличенную карточку, цену и условия.</li><li>После принятия открываем контакт в пределах согласия клиента.</li><li>Если мастер отказался или не ответил, предлагаем следующему.</li></ol></section>
<section class="safe-promise"><p class="eyebrow">Честная граница</p><h2>ПРАКСЕЛЬТА не обещает выезд, пока нет готового мастера</h2><p>Сейчас страница показывает, как будет устроена услуга. Заявки отсюда пока не передаются; реклама и списания выключены.</p></section>"""
    page(filename, f"{category['name']} в городе {city}", f"Подготовка подбора мастера: {category['name']} — {city}.", body)
    return filename


def update_sitemap(filenames: list[str]) -> None:
    sitemap_path = ROOT / "sitemap.xml"
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}urlset")
    all_pages = sorted({path.name for path in ROOT.glob("*.html")} | set(filenames))
    for filename in all_pages:
        entry = ET.SubElement(root, f"{{{namespace}}}url")
        suffix = "" if filename == "index.html" else filename
        ET.SubElement(entry, f"{{{namespace}}}loc").text = BASE_URL + suffix
        ET.SubElement(entry, f"{{{namespace}}}lastmod").text = "2026-08-13"
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)


def render() -> None:
    categories = REGISTRY["categories"]
    generated = render_catalog(categories)
    for category in categories:
        if category["wave"] != 1:
            continue
        for city in category["launch_cities"]:
            generated.append(render_city_category(category, city))
    update_sitemap(generated)
    print(f"MULTICATEGORY RENDER: PASS ({len(generated)} pages)")


if __name__ == "__main__":
    render()
