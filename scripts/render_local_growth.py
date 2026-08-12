"""Render the static local-growth pages from the pricing source of truth."""

from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://m72692591-collab.github.io/praxelta-services/"
EMAIL = "animatactus087@gmail.com"


def money(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " ₽"


def price_span(pricing: dict, key: str) -> str:
    value: object = pricing
    for part in key.split("."):
        value = value[part]  # type: ignore[index]
    assert isinstance(value, int)
    return f'<span data-price-key="{key}">{money(value)}</span>'


def head(title: str, description: str, filename: str, *, script: bool = True) -> str:
    policy = "script-src 'self';" if script else "script-src 'none';"
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; {policy} connect-src 'none'; object-src 'none'; base-uri 'self'; form-action 'none'; upgrade-insecure-requests; block-all-mixed-content">
  <meta name="referrer" content="no-referrer">
  <meta name="description" content="{html.escape(description)}">
  <title>{html.escape(title)} — ПРАКСЕЛЬТА</title>
  <link rel="canonical" href="{BASE_URL}{filename}">
  <link rel="icon" type="image/png" href="praxelta-icon.png">
  <link rel="stylesheet" href="styles.css">
</head>"""


def header() -> str:
    return """<header class="site-header local-header">
  <a class="brand" href="index.html" aria-label="ПРАКСЕЛЬТА — на главную">ПРАКСЕЛЬТА</a>
  <nav aria-label="Разделы направления">
    <a href="local-growth.html">Услуга</a>
    <a href="local-growth-sample.html">Пример</a>
    <a href="local-growth-commercial.html">Предложение</a>
    <a href="local-growth-checklist.html">Чек-лист</a>
  </nav>
</header>"""


def footer() -> str:
    return """<footer>
  <nav>
    <a href="offer.html">Публичная оферта</a>
    <a href="privacy.html">Персональные данные</a>
    <a href="refund.html">Отмена и возврат</a>
    <a href="terms.html">Порядок заказа</a>
  </nav>
  <p>© 2026 ПРАКСЕЛЬТА. Григоров Михаил Владимирович, ИНН 640100982708.</p>
</footer>"""


def order_link(label: str, code: str, source: str = "local_growth") -> str:
    subject = "Запрос ПРАКСЕЛЬТА — продвижение локального бизнеса"
    body = (
        f"Код услуги: {code}\n"
        f"Источник: {source}\n"
        "Оформить письменный заказ: да\n\n"
        "Город:\n"
        "Услуга или направление:\n"
        "Ссылка на профиль Авито или сайт:\n"
        "Какой путь обращения важнее проверить первым:\n"
        "Плательщик: физлицо / ИП / организация"
    )
    query = urlencode({"subject": subject, "body": body})
    return f'<a class="button primary" href="mailto:{EMAIL}?{query}">{html.escape(label)} →</a>'


def dialog() -> str:
    return """<dialog id="order-dialog" aria-labelledby="order-dialog-title">
  <div class="dialog-card">
    <button class="dialog-close" type="button" aria-label="Закрыть">×</button>
    <p class="eyebrow">Письмо можно проверить до отправки</p>
    <h2 id="order-dialog-title">Готовый запрос</h2>
    <label for="order-subject">Тема</label>
    <input id="order-subject" type="text">
    <label for="order-body">Текст</label>
    <textarea id="order-body" rows="12"></textarea>
    <div class="dialog-actions">
      <button id="copy-order" class="button" type="button">Скопировать</button>
      <a id="open-gmail" class="button primary" href="#" target="_blank" rel="noopener noreferrer">Открыть Gmail</a>
      <a id="open-mail-app" class="button" href="#">Почтовое приложение</a>
    </div>
    <p id="dialog-status" class="micro" role="status"></p>
  </div>
</dialog>
<script src="order.js?v=local-growth-1" defer></script>"""


def tariff_cards(pricing: dict) -> str:
    p = lambda key: price_span(pricing, key)
    return f"""<div class="tariff-grid">
  <article><p class="eyebrow">Один раз · 7 дней</p><h3>Экспресс</h3><p class="price">{p('services.express.price_once')}</p><p>До трёх объявлений, ответы, десять действий и план на 30 дней.</p></article>
  <article><p class="eyebrow">Ведение Авито</p><h3>Старт</h3><p class="price">{p('services.start.first_month')} первый месяц</p><p>Далее {p('services.start.monthly')} в месяц. До 5–7 рабочих объявлений, еженедельные правки, отзывы и отчёт.</p></article>
  <article><p class="eyebrow">Несколько каналов</p><h3>Рост</h3><p class="price">{p('services.growth.first_month')} первый месяц</p><p>Далее {p('services.growth.monthly')} в месяц. Сайт, Яндекс Бизнес, 2ГИС, простой учёт обращений и материалы.</p></article>
  <article><p class="eyebrow">Внедрение</p><h3>Система</h3><p class="price">{p('services.system.implementation')} внедрение</p><p>Далее {p('services.system.monthly')} в месяц. CRM, рабочий номер, телефония, статусы и резервный ручной режим. Подписки отдельно.</p></article>
  <article><p class="eyebrow">Управление процессом</p><h3>Бизнес-партнёр</h3><p class="price">{p('services.business_partner.implementation')} внедрение</p><p>Далее {p('services.business_partner.monthly')} в месяц. Загрузка, повторные обращения, регламенты, база знаний и управленческий отчёт. Подписки и реклама отдельно.</p></article>
</div>"""


def local_growth(pricing: dict) -> str:
    express = price_span(pricing, "services.express.price_once")
    return f"""{head('Продвижение локального сервисного бизнеса', 'Разбор Авито, понятные объявления и честный учёт обращений для локальных сервисных компаний.', 'local-growth.html')}
<body>{header()}
<main class="local-page">
  <section class="local-hero" aria-labelledby="local-title"><p class="eyebrow">Новое направление ПРАКСЕЛЬТЫ</p><h1 id="local-title">Разберём действующее продвижение и сделаем путь до выезда понятнее</h1><p class="lead">Сначала смотрим, как человек находит услугу, что видит в объявлении и какой ответ получает. Затем предлагаем конкретные правки. Текущие объявления продолжают работать.</p><div class="hero-actions">{order_link('Обсудить экспресс-разбор', 'local_growth_express')}<a class="button" href="local-growth-sample.html">Посмотреть пример</a></div><p class="micro">{express} — работа ПРАКСЕЛЬТЫ за семь дней. Рекламный бюджет и оплата Авито не входят.</p></section>

  <section><p class="eyebrow">Кому подходит</p><h2>Мастерам и компаниям, у которых работа начинается со звонка или сообщения</h2><p>Мастерам по котлам и отоплению, сантехникам, электрикам, сервисам бытовой техники, окон, кровли и ремонта, клинингу, автосервисам и другим локальным компаниям. Медицинские, финансовые и юридические услуги требуют отдельной проверки правил и в этот запуск не входят.</p></section>

  <section><p class="eyebrow">Почему трудно разобраться</p><h2>Объявления работают, а просмотры, звонки и сообщения видны в разных местах</h2><p>Из разрозненных данных трудно понять, какое объявление привело подходящее обращение, что спросил человек и чем закончился разговор. Мы сводим доступные факты и показываем путь от объявления до результата — без догадок о потерях.</p></section>

  <section class="safe-promise"><p class="eyebrow">Главное обещание</p><h2>Сначала сохраняем то, что уже работает</h2><p>Мы не отключаем объявления, не забираем рекламный бюджет и не меняем расходы без письменного согласования. Каждую предлагаемую правку можно принять, отклонить или отложить.</p></section>

  <section><p class="eyebrow">Авито продолжает работать</p><h2>Профиль, история и бюджет остаются у вас</h2><ul class="check-list"><li>Авито оплачивается напрямую площадке.</li><li>Профиль и объявления остаются в вашем аккаунте.</li><li>ПРАКСЕЛЬТА получает только согласованный доступ или обезличенные выгрузки.</li><li>Текущая реклама не отключается без согласования.</li></ul></section>

  <section><p class="eyebrow">Что вы получаете за {express}</p><h2>Экспресс-разбор за семь дней</h2><div class="number-grid"><ol><li>Разбор профиля Авито и доступной статистики.</li><li>Проверка расходов, просмотров, звонков и сообщений.</li><li>Проверка до трёх главных объявлений.</li><li>Анализ заголовков, текстов, первых фото и структуры предложения.</li><li>Проверка цены или принципа расчёта.</li><li>Проверка первого ответа и возможных разрывов в маршруте.</li><li>Переработка до трёх объявлений.</li><li>Шаблоны ответов на частые вопросы.</li><li>Десять конкретных действий по улучшению.</li><li>План на 30 дней и итоговый отчёт.</li></ol></div></section>

  <section><p class="eyebrow">Что не меняется</p><h2>Вы решаете, что менять</h2><p>Объявления, история аккаунта и текущие обращения остаются у вас. Вы по-прежнему сами оплачиваете Авито и можете принять, отклонить или отложить любую правку. Подготовленные материалы после оплаты принадлежат вам в объёме письменного заказа.</p></section>

  <section><p class="eyebrow">Что можно улучшить</p><h2>Проверяем конкретные места, где разговор может оборваться</h2><p>Можно яснее разделить услуги в объявлениях, заранее ответить на частые вопросы, заметить пропущенные звонки, вовремя попросить отзыв или напомнить об обслуживании. Что из этого действительно полезно, решаем только по доступным данным.</p></section>

  <section><p class="eyebrow">Семь дней</p><h2>Как идёт работа</h2><ol class="timeline"><li><strong>День 1.</strong> Письменно фиксируем заказ, входные данные и границы доступа.</li><li><strong>Дни 2–3.</strong> Разбираем профиль, статистику и три объявления.</li><li><strong>Дни 4–5.</strong> Готовим новые версии и ответы.</li><li><strong>День 6.</strong> Сверяем материалы с вами и вносим согласованные правки.</li><li><strong>День 7.</strong> Передаём отчёт, десять действий и план на месяц.</li></ol></section>

  <section><p class="eyebrow">Что потребуется</p><h2>Материалы по одной выбранной услуге</h2><p>Ссылка на профиль, до трёх объявлений, доступная статистика и примеры первых ответов без персональных данных третьих лиц. Пароли, коды, полный номер карты, прибыль, налоги, себестоимость и стоимость запчастей не нужны.</p></section>

  <section><p class="eyebrow">Тарифы</p><h2>От разбора до системы</h2>{tariff_cards(pricing)}<p class="micro">Сумма экспресс-разбора может быть зачтена в первый месяц ежемесячного тарифа, только если это прямо записано в письменном заказе.</p></section>

  <section><p class="eyebrow">Учёт обращений</p><h2>Отдельно факты из кабинетов и отметки мастера</h2><div class="two-col"><article><h3>Можно получить автоматически</h3><ul><li>расходы, просмотры и открытия контактов;</li><li>сообщения и доступную статистику звонков;</li><li>пропущенные звонки, дату, длительность и источник;</li><li>объявление, с которого пришёл контакт.</li></ul></article><article><h3>Отмечает мастер или сотрудник</h3><ul><li>целевой или нецелевой контакт;</li><li>выезд назначен или состоялся;</li><li>работа выполнена;</li><li>нужна запчасть, перенос или отказ;</li><li>повторный контакт.</li></ul></article></div><p>Если отметки нет, отчёт не приписывает обращению выезд или выполненную работу.</p></section>

  <section><p class="eyebrow">Одна кнопка</p><h2>Отметить итог звонка можно за несколько секунд</h2><div class="status-pills" aria-label="Примеры статусов"><span>Нецелевой</span><span>Перезвонить</span><span>Выезд назначен</span><span>Выезд состоялся</span><span>Работа выполнена</span><span>Нужна запчасть</span><span>Перенос</span><span>Отказ</span></div></section>

  <section><p class="eyebrow">Телефония и Telegram-бот</p><h2>Эти инструменты подключаем только в «Системе» и старших тарифах</h2><p>Там могут появиться отдельный рабочий номер, виртуальная телефония, коллтрекинг, CRM и внутренний Telegram-бот. Сторонние подписки оплачиваются отдельно после согласования. Запись разговоров выключена по умолчанию и включается только после правовой проверки и корректного уведомления.</p></section>

  <section><p class="eyebrow">Развитие бизнеса</p><h2>Сначала порядок в обращениях, затем расширение</h2><p>После проверки базового маршрута можно добавить отзывы, повторные обращения, сезонные напоминания, сервисные пакеты, рекомендации и новые районы. Маржинальность — отдельный добровольный модуль: без согласованных данных мы её не рассчитываем и не обещаем.</p></section>

  <section><p class="eyebrow">FAQ</p><h2>Коротко о главном</h2><details><summary>У меня и так хватает заявок. Зачем разбор?</summary><p>Цель не обязательно в большем потоке. Можно проверить качество обращений, пропущенные контакты, отзывы и повторные обращения, сохранив работающую рекламу.</p></details><details><summary>Вы будете управлять бюджетом?</summary><p>Нет. Бюджет остаётся под вашим контролем, Авито вы оплачиваете напрямую. Изменения расходов возможны только после отдельного согласования.</p></details><details><summary>Нужна ли CRM?</summary><p>Для экспресс-разбора — нет. Начать можно с простой таблицы и коротких статусов.</p></details><details><summary>Сколько клиентов вы гарантируете?</summary><p>Фиксированное число обращений и продаж не гарантируется. Мы отвечаем за согласованный анализ, материалы, настройки и отчёт.</p></details></section>

  <section><p class="eyebrow">Юридические границы</p><h2>Заказ фиксируется письменно</h2><p>В заказе указываются объём, цена, срок, доступы, критерии приёмки, число правок, рекламный бюджет и сторонние подписки. После оплаты выдаётся чек НПД. Персональные данные третьих лиц для экспресс-разбора не требуются.</p></section>

  <section class="local-cta"><p class="eyebrow">Следующий шаг</p><h2>Выберите один путь, который стоит проверить первым</h2><p>Например: «объявление о ремонте котла → сообщение → выезд». В письме можно оставить ссылку и один вопрос. До отправки текст будет виден целиком.</p>{order_link('Подготовить письменный запрос', 'local_growth_express')}</section>
</main>{footer()}{dialog()}</body></html>"""


def sample_page(pricing: dict) -> str:
    express = price_span(pricing, "services.express.price_once")
    return f"""{head('Обезличенный пример экспресс-разбора', 'Как выглядит результат семидневного разбора продвижения локального мастера.', 'local-growth-sample.html')}
<body>{header()}<main class="local-page printable"><section class="local-hero"><p class="eyebrow">Обезличенный пример · синтетические данные</p><h1>Ремонт бытовых котлов: от объявления до выезда</h1><p class="lead">Пример показывает форму результата. Компания, адреса, контакты и цифры вымышлены и не описывают реального клиента.</p></section><section><h2>Исходная ситуация</h2><p>У мастера три объявления: диагностика, срочный ремонт и обслуживание. В первом ответе клиенту предлагают позвонить, но не уточняют модель котла, ошибку и район. Статусы после звонка нигде не фиксируются.</p></section><section><h2>Что проверено</h2><ul><li>различие заголовков и первых фотографий;</li><li>понятность цены или принципа расчёта;</li><li>путь от сообщения до согласованного выезда;</li><li>повторяющиеся вопросы и первый ответ;</li><li>минимальный набор статусов для учёта.</li></ul></section><section><h2>Три примера правок</h2><div class="two-col"><article><h3>Было</h3><p>«Ремонт котлов быстро и качественно. Звоните».</p></article><article><h3>Стало</h3><p>«Ремонт бытовых газовых котлов: диагностика ошибки, согласование стоимости до работ, выезд по городу».</p></article></div><p><strong>Первый ответ:</strong> «Здравствуйте. Напишите марку котла, код ошибки и район. Если удобно, приложите фото панели — скажу, можно ли начать с консультации или нужен выезд».</p><p><strong>Статусы:</strong> перезвонить → выезд назначен → выезд состоялся → работа выполнена / нужна запчасть / отказ.</p></section><section><h2>Что передаётся</h2><p>Три переработанных объявления, пять шаблонов ответа, список из десяти действий и план на 30 дней. Цена такого объёма — {express}; рекламный бюджет не входит.</p></section><section><h2>Чего пример не доказывает</h2><p>Он не обещает число обращений, выездов или продаж. Реальный вывод делается только по данным конкретного клиента и его отметкам.</p></section>{order_link('Обсудить такой разбор', 'local_growth_express', 'sample')}</main>{footer()}{dialog()}</body></html>"""


def commercial_page(pricing: dict) -> str:
    express = price_span(pricing, "services.express.price_once")
    return f"""{head('Коммерческое предложение: локальное продвижение', 'Полное коммерческое предложение ПРАКСЕЛЬТЫ для локального сервисного бизнеса.', 'local-growth-commercial.html')}
<body>{header()}<main class="local-page printable commercial"><section class="local-hero"><p class="eyebrow">Коммерческое предложение</p><h1>Управляемое продвижение и учёт обращений</h1><p class="lead">Для мастеров и сервисных компаний, которые получают звонки и сообщения через Авито, сайт, Яндекс, 2ГИС и мессенджеры.</p><p class="price-line">Первый шаг: <strong>{express}</strong> · семь дней</p></section><section><h2>Что меняется после экспресс-разбора</h2><p>У вас остаётся понятный набор материалов: до трёх переработанных объявлений, ответы на частые вопросы, десять приоритетных действий и план на месяц. Работающая реклама сохраняется; бюджет остаётся под вашим контролем.</p></section><section><h2>Состав работы</h2><ol><li>Проверяем профиль, доступную статистику и текущие расходы.</li><li>Разбираем до трёх объявлений: заголовок, текст, первые фото, предложение и цену.</li><li>Смотрим, что происходит между первым сообщением и выездом.</li><li>Готовим новые версии объявлений и шаблоны ответов.</li><li>Передаём отчёт, десять действий и план на 30 дней.</li></ol></section><section><h2>Что остаётся без изменений</h2><ul><li>Авито продолжает работать и оплачивается клиентом напрямую.</li><li>Профиль, история и объявления принадлежат клиенту.</li><li>Расходы и настройки не меняются без согласования.</li><li>Прибыль, налоги, себестоимость и стоимость запчастей не запрашиваются.</li></ul></section><section><h2>Тарифы после разбора</h2>{tariff_cards(pricing)}</section><section><h2>Порядок заказа</h2><p>До оплаты стороны письменно фиксируют номер и название услуги, входные данные, объём, цену, срок, рекламный бюджет, сторонние подписки, доступы, критерии приёмки, число правок, отмену и ограничения. После оплаты ПРАКСЕЛЬТА выдаёт чек НПД.</p><p>Зачёт {express} в первый месяц ежемесячного тарифа действует только при прямой записи в заказе.</p></section><section><h2>Ограничения</h2><p>ПРАКСЕЛЬТА не гарантирует число обращений или продаж и не отключает рекламу без согласования. Результат — анализ, материалы, настройки в согласованном объёме и отчёт. Телефония, CRM, бот и сторонние подписки входят только в соответствующие тарифы.</p></section><section class="local-cta"><h2>С чего начать разговор</h2><p>Пришлите город, ссылку на профиль и один путь обращения, который важнее всего проверить.</p>{order_link('Подготовить запрос', 'local_growth_express', 'commercial')}</section></main>{footer()}{dialog()}</body></html>"""


def teaser_page(pricing: dict) -> str:
    express = price_span(pricing, "services.express.price_once")
    return f"""{head('Экспресс-разбор локального продвижения', 'Короткое предложение: разбор Авито и пути обращения за семь дней.', 'local-growth-teaser.html')}
<body>{header()}<main class="local-page printable teaser"><section class="local-hero"><p class="eyebrow">ПРАКСЕЛЬТА · 7 дней</p><h1>Проверим, как объявление приводит человека к разговору и выезду</h1><p class="lead">Разберём действующий профиль Авито, доступную статистику и до трёх объявлений. Перепишем слабые части, подготовим ответы и план на 30 дней.</p><p class="price-line"><strong>{express}</strong> за работу ПРАКСЕЛЬТЫ</p></section><section class="two-col"><article><h2>Входит</h2><ul><li>до трёх объявлений;</li><li>проверка расходов и обращений по доступным данным;</li><li>шаблоны первого ответа;</li><li>десять действий и отчёт.</li></ul></article><article><h2>Не меняется</h2><ul><li>Авито продолжает работать;</li><li>вы оплачиваете площадку напрямую;</li><li>бюджет остаётся под вашим контролем;</li><li>каждую правку вы согласуете.</li></ul></article></section><section><p>Рекламный бюджет не входит. Число обращений и продаж не гарантируется. Пароли, прибыль, налоги и персональные данные третьих лиц не нужны.</p>{order_link('Обсудить один маршрут', 'local_growth_express', 'teaser')}</section></main>{footer()}{dialog()}</body></html>"""


def checklist_page(pricing: dict) -> str:
    express = price_span(pricing, "services.express.price_once")
    return f"""{head('7 точек между рекламой и выполненной работой', 'Чек-лист для локального бизнеса: где обращение может потеряться до выполненной работы.', 'local-growth-checklist.html')}
<body>{header()}<main class="local-page printable checklist"><section class="local-hero"><p class="eyebrow">Короткий чек-лист</p><h1>7 точек, где локальный бизнес может терять обращения между рекламой и выполненной работой</h1><p class="lead">Не каждая точка означает проблему. Пройдите маршрут на одном объявлении и отметьте только то, что подтверждается.</p></section><ol class="checklist-steps"><li><strong>Первый экран объявления.</strong> Понятно ли, какую задачу вы решаете, где работаете и как формируется цена?</li><li><strong>Первый вопрос клиента.</strong> Есть ли короткий ответ, который собирает нужные данные без допроса?</li><li><strong>Пропущенный звонок.</strong> Видно ли, кто и когда перезвонил?</li><li><strong>Договорённость о выезде.</strong> Зафиксированы ли время, адрес и что подготовить клиенту?</li><li><strong>Результат выезда.</strong> Можно ли за несколько секунд отметить: выполнено, нужна запчасть, перенос или отказ?</li><li><strong>Отзыв.</strong> Есть ли уместный момент и готовая формулировка для просьбы?</li><li><strong>Повторный контакт.</strong> Понятно ли, кому и когда полезно напомнить об обслуживании?</li></ol><section><h2>Что делать дальше</h2><p>Выберите одну точку, соберите факты за неделю и исправьте только то, что можно проверить. Если нужен внешний разбор, ПРАКСЕЛЬТА проводит его за семь дней: {express}, до трёх объявлений, ответы, десять действий и план на месяц.</p>{order_link('Запросить экспресс-разбор', 'local_growth_express', 'checklist')}</section></main>{footer()}{dialog()}</body></html>"""


CITY_DATA = [
    ("saratov", "Саратов", "Котлы, отопление, сантехника, электрика, ремонт техники, окна, клининг и автосервис.", "объявление → уточнение района и задачи → согласованный выезд", "Для выездной услуги важно сразу уточнять район и доступное время, чтобы обещание по сроку не опережало реальный маршрут."),
    ("engels", "Энгельс", "Отопление, ремонт техники, окна и двери, сантехника, электрика, ремонт и клининг.", "объявление → вопрос о модели или объекте → время выезда", "При работе по Энгельсу и соседним населённым пунктам полезно заранее разделить зоны выезда и не смешивать их в одном обещании."),
    ("voronezh", "Воронеж", "Климат, котлы, бытовая техника, ремонт квартир, окна, клининг и автосервис.", "поиск услуги → выбор района → сообщение → запись", "Когда мастер работает в нескольких районах, клиенту проще ответить, если в первом сообщении уже есть вопрос о месте и характере задачи."),
    ("tyumen", "Тюмень", "Отопление, климатическая техника, котлы, сантехника, электрика, автосервис и клининг.", "объявление → описание неисправности → решение о консультации или выезде", "В длинный отопительный сезон особенно важно отличать срочный ремонт от планового обслуживания и не обещать одинаковый срок для разных задач."),
    ("tambov", "Тамбов", "Котлы, сантехника, электрика, ремонт техники, окна, ремонт квартир и клининг.", "объявление → уточнение объекта → расчёт или выезд", "Для города и ближайших пригородов полезно заранее объяснить границы выезда и какие исходные данные нужны для предварительного разговора."),
    ("penza", "Пенза", "Отопление, бытовая техника, электрика, сантехника, окна, ремонт, клининг и шиномонтаж.", "карточка услуги → первый вопрос → согласование визита", "Если услуги заметно отличаются по времени и подготовке, их лучше развести по объявлениям, а не оставлять один общий текст на все случаи."),
]


def city_page(pricing: dict, slug: str, city: str, niches: str, route: str, note: str) -> str:
    express = price_span(pricing, "services.express.price_once")
    filename = f"local-growth-{slug}.html"
    return f"""{head(f'Продвижение локального бизнеса в городе {city}', f'ПРАКСЕЛЬТА: разбор Авито и учёт обращений для сервисного бизнеса, {city}.', filename)}
<body>{header()}<main class="local-page city-page"><section class="local-hero"><p class="eyebrow">{city} · локальный сервис</p><h1>Понятный путь от объявления до выезда</h1><p class="lead">ПРАКСЕЛЬТА разбирает действующее продвижение. Объявления продолжают работать, а расходы меняются только после вашего согласия.</p></section><section><h2>Подходящие направления</h2><p>{niches}</p><p>{note}</p></section><section><h2>Один маршрут для первой проверки</h2><p class="route-example">{route}</p><p>Смотрим, что человек видит, какие данные у него просят и где фиксируется договорённость. Если результата выезда нет в кабинете, его отмечает мастер — система ничего не додумывает.</p></section><section><h2>Экспресс-разбор</h2><p>{express} за семь дней: до трёх объявлений, доступная статистика, новые тексты, шаблоны ответов, десять действий и план на 30 дней. Авито оплачивается напрямую площадке, рекламный бюджет не входит.</p><a class="button" href="local-growth.html?ref=city_{slug}">Посмотреть полный состав</a></section><section><h2>Вопросы</h2><details><summary>Нужно ли передавать пароль?</summary><p>Нет. Сначала достаточно ссылок, обезличенной статистики и согласованного объёма данных.</p></details><details><summary>ПРАКСЕЛЬТА обещает больше заявок?</summary><p>Нет. Мы отвечаем за анализ, материалы и согласованные настройки, а не за фиксированное число обращений.</p></details><details><summary>Можно начать без CRM?</summary><p>Да. Для первого цикла достаточно простой таблицы и коротких отметок после обращения.</p></details></section><section class="local-cta"><h2>Проверить один путь в {city}</h2><p>В письме укажите услугу, ссылку и район работы. Текст можно отредактировать до отправки.</p>{order_link('Подготовить запрос', 'local_growth_express', f'city_{slug}')}</section></main>{footer()}{dialog()}</body></html>"""


def update_sitemap(files: list[str]) -> None:
    urls = "\n".join(
        f"  <url><loc>{BASE_URL}{name}</loc><lastmod>2026-08-12</lastmod></url>"
        for name in files
    )
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
        encoding="utf-8",
    )


def main() -> None:
    pricing = json.loads((ROOT / "pricing.json").read_text(encoding="utf-8"))
    pages = {
        "local-growth.html": local_growth(pricing),
        "local-growth-sample.html": sample_page(pricing),
        "local-growth-commercial.html": commercial_page(pricing),
        "local-growth-teaser.html": teaser_page(pricing),
        "local-growth-checklist.html": checklist_page(pricing),
    }
    for slug, city, niches, route, note in CITY_DATA:
        pages[f"local-growth-{slug}.html"] = city_page(pricing, slug, city, niches, route, note)
    for filename, content in pages.items():
        (ROOT / filename).write_text(content + "\n", encoding="utf-8")
    existing = [
        "", "index.html", "partner.html", "marketplace.html", "marketplace-sample.html",
        "offer.html", "privacy.html", "refund.html", "terms.html", "sample.html",
    ]
    update_sitemap(existing + list(pages))
    print(f"Rendered {len(pages)} local-growth pages from pricing.json")


if __name__ == "__main__":
    main()
