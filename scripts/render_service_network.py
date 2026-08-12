from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://m72692591-collab.github.io/praxelta-services/"
PRICES = json.loads((ROOT / "pricing.json").read_text(encoding="utf-8"))["services"]


def rub(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " ₽"


NAV = """<header class="site-header market-header">
  <a class="brand" href="index.html" aria-label="ПРАКСЕЛЬТА — на главную">ПРАКСЕЛЬТА</a>
  <nav aria-label="ПРАКСЕЛЬТА Маркет">
    <a href="lead-marketplace.html">Как работает</a>
    <a href="request-service.html">Клиентам</a>
    <a href="for-contractors.html">Мастерам</a>
    <a href="for-suppliers.html">Поставщикам</a>
    <a href="pricing.html">Тарифы</a>
  </nav>
</header>"""

FOOTER = """<footer class="market-footer">
  <p><strong>ПРАКСЕЛЬТА Маркет</strong><br>Пилотная система. Реальные платежи и автоматическая передача контактов выключены до отдельных проверок.</p>
  <nav><a href="service-network-safety.html">Безопасность</a><a href="service-network-privacy.html">Данные</a><a href="service-network-terms.html">Условия</a><a href="lead-quality-policy.html">Качество заявки</a></nav>
</footer>"""


def page(filename: str, title: str, description: str, body: str, *, script: bool = False) -> None:
    script_tag = '<script src="service-network.js" defer></script>' if script else ""
    document = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; script-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'self'; form-action 'none'; upgrade-insecure-requests; block-all-mixed-content">
  <meta name="referrer" content="no-referrer">
  <meta name="description" content="{html.escape(description)}">
  <title>{html.escape(title)} — ПРАКСЕЛЬТА</title>
  <link rel="canonical" href="{BASE_URL}{filename}">
  <link rel="icon" type="image/png" href="praxelta-icon.png">
  <link rel="stylesheet" href="styles.css">
  {script_tag}
</head>
<body>{NAV}<main class="local-page market-page">{body}</main>{FOOTER}</body>
</html>
"""
    (ROOT / filename).write_text(document, encoding="utf-8")


def hero(kicker: str, title: str, lead: str, actions: str = "") -> str:
    return f"""<section class="local-hero market-hero"><p class="eyebrow">{kicker}</p><h1>{title}</h1><p class="lead">{lead}</p>{actions}<p class="pilot-badge">SANDBOX · реальные деньги, рассылки и передача контактов выключены</p></section>"""


def render() -> None:
    express = PRICES["express"]
    start = PRICES["start"]
    growth = PRICES["growth"]
    system = PRICES["system"]
    partner = PRICES["business_partner"]

    pricing_cards = f"""<div class="tariff-grid pricing-grid">
<article><p class="eyebrow">7 дней</p><h3>Экспресс</h3><p class="price"><span data-price-key="services.express.price_once">{rub(express['price_once'])}</span></p><p>Разбор Авито, доступной статистики и до трёх объявлений. Десять действий и план на 30 дней.</p></article>
<article><p class="eyebrow">Ведение Авито</p><h3>Старт</h3><p class="price"><span data-price-key="services.start.first_month">{rub(start['first_month'])}</span> первый месяц</p><p>Далее <span data-price-key="services.start.monthly">{rub(start['monthly'])}</span> в месяц. До 5–7 объявлений, корректировки, ответы, отзывы и отчёт.</p></article>
<article><p class="eyebrow">Несколько каналов</p><h3>Рост</h3><p class="price"><span data-price-key="services.growth.first_month">{rub(growth['first_month'])}</span> первый месяц</p><p>Далее <span data-price-key="services.growth.monthly">{rub(growth['monthly'])}</span> в месяц. Сайт, карточки, простой учёт обращений и отзывы.</p></article>
<article><p class="eyebrow">Внедрение</p><h3>Система</h3><p class="price"><span data-price-key="services.system.implementation">{rub(system['implementation'])}</span></p><p>Далее <span data-price-key="services.system.monthly">{rub(system['monthly'])}</span> в месяц. CRM, рабочий номер, телефония и внутренний Telegram-бот. Подписки отдельно.</p></article>
<article><p class="eyebrow">Операционное сопровождение</p><h3>Бизнес-партнёр</h3><p class="price"><span data-price-key="services.business_partner.implementation">{rub(partner['implementation'])}</span></p><p>Далее <span data-price-key="services.business_partner.monthly">{rub(partner['monthly'])}</span> в месяц. Распределение нагрузки, регламенты, повторные обращения, мастера и поставщики.</p></article>
</div>"""

    page(
        "lead-marketplace.html",
        "ПРАКСЕЛЬТА Маркет",
        "Как устроен безопасный пилот заявок, мастеров и поставщиков.",
        hero(
            "ПРАКСЕЛЬТА Маркет",
            "От запроса клиента до нужной детали — в одном понятном маршруте",
            "Клиент описывает задачу. Мы подтверждаем контакт, отдельно фиксируем согласие и проверяем город и категорию. До принятия заявки мастер видит только обезличенную карточку и условия. Затем контакт открывается тому мастеру, которого выбрала система или сам клиент.",
            '<div class="hero-actions"><a class="button primary" href="request-service.html">Открыть тестовую форму</a><a class="button" href="how-it-works.html">Разобрать путь заявки</a></div>',
        )
        + """<section><p class="eyebrow">Один маршрут</p><h2>От запроса до детали — без продажи базы контактов</h2><ol class="market-flow"><li><strong>Клиент</strong><span>описывает задачу и выбирает, скольким мастерам можно передать контакт</span></li><li><strong>ПРАКСЕЛЬТА</strong><span>проверяет согласие, дубль, категорию и признаки аварийной ситуации</span></li><li><strong>Мастер</strong><span>видит обезличенную карточку, цену и условия до принятия</span></li><li><strong>Поставщик</strong><span>отвечает на запрос детали, не получая лишних данных клиента</span></li></ol></section>
<section class="two-col"><article><p class="eyebrow">CLIENT_OWNED_LEAD</p><h2>Заявка предпринимателя</h2><p>Пришла из его Авито, сайта, телефона или рекламы. Она остаётся у этого предпринимателя и не уходит другим мастерам без отдельного основания.</p></article><article><p class="eyebrow">PRAXELTA_MARKETPLACE_LEAD</p><h2>Заявка ПРАКСЕЛЬТЫ</h2><p>Пришла через форму или канал ПРАКСЕЛЬТЫ. Её можно распределять только в пределах согласия клиента.</p></article></section>
<section class="safe-promise"><p class="eyebrow">Граница пилота</p><h2>Система пока работает только на синтетических заявках</h2><p>Ни один реальный контакт не передаётся, деньги не списываются, проценты не начисляются к выплате. Эти функции закрыты юридическим и налоговым gate.</p></section>""",
    )

    form = """<section class="local-hero"><p class="eyebrow">Тестовая форма · данные не отправляются</p><h1>Опишите задачу, не указывая полный адрес</h1><p class="lead">Форма показывает, какие данные понадобятся в будущем. Сейчас всё остаётся только на экране вашего браузера и исчезает после закрытия страницы.</p></section>
<section id="emergency-warning" class="emergency-warning" hidden tabindex="-1"><h2>Похоже на аварийную ситуацию</h2><p>Не ждите ответа коммерческого сервиса. При непосредственной угрозе жизни или признаках утечки газа обратитесь в официальную аварийную службу или по номеру 112. Не пытайтесь ремонтировать газовое оборудование самостоятельно.</p></section>
<form id="service-request-form" class="market-form" novalidate>
<fieldset><legend>Где и что случилось</legend><div class="form-grid"><label>Город<select name="city" required><option value="">Выберите</option><option>Саратов</option><option>Энгельс</option></select></label><label>Район<input name="district" autocomplete="address-level3" required></label><label>Услуга<select name="category" required><option value="">Выберите</option><option>Ремонт котлов</option><option>Обслуживание котлов</option><option>Отопление</option></select></label><label>Оборудование<input name="equipment" placeholder="Например, бытовой котёл"></label><label>Марка<input name="brand"></label><label>Модель<input name="model"></label><label>Код ошибки<input name="error_code"></label><label>Срочность<select name="urgency" required><option>Сегодня</option><option>В течение 2–3 дней</option><option>Планово</option></select></label></div><label>Что происходит<textarea name="problem" minlength="12" required placeholder="Опишите наблюдаемые признаки. Не пишите полный домашний адрес."></textarea></label></fieldset>
<fieldset><legend>Как связаться</legend><div class="form-grid"><label>Удобный канал<select name="channel" required><option>Телефон</option><option>Telegram</option><option>Email</option></select></label><label>Контакт<input name="contact" autocomplete="tel" required></label><label>Удобное время<input name="preferred_time" placeholder="Например, после 18:00"></label><label>Фото или видео<input type="file" name="media" accept="image/*,video/*" aria-describedby="media-note"></label></div><p id="media-note" class="micro">В тестовом режиме файл не загружается и никуда не отправляется.</p></fieldset>
<fieldset><legend>Кому можно показать заявку</legend><label class="radio-row"><input type="radio" name="share_mode" value="one" required> Одному выбранному мастеру</label><label class="radio-row"><input type="radio" name="share_mode" value="sequential"> Последовательно подбирать по одному мастеру</label><label class="radio-row"><input type="radio" name="share_mode" value="three"> Не более трёх мастеров для сравнения</label><label class="radio-row"><input type="radio" name="share_mode" value="choice"> Я сам выберу мастера</label></fieldset>
<fieldset><legend>Согласия</legend><label class="check-row"><input type="checkbox" name="processing" required> Согласен на обработку указанных данных для разбора этой заявки.</label><label class="check-row"><input type="checkbox" name="transfer" required> Согласен на передачу контакта выбранному числу подходящих мастеров. Это не согласие на рекламу.</label></fieldset>
<button class="button primary" type="submit">Проверить тестовую заявку</button><p id="form-status" class="form-status" role="status" aria-live="polite"></p></form>
<section id="request-preview" class="request-preview" hidden><p class="eyebrow">Локальный предпросмотр</p><h2>Заявка никуда не отправлена</h2><pre id="request-preview-text"></pre><button class="button" id="clear-preview" type="button">Очистить экран</button></section>"""
    page(
        "request-service.html",
        "Тестовая форма заявки",
        "Тестовая форма обращения ПРАКСЕЛЬТЫ без отправки и хранения данных.",
        form,
        script=True,
    )

    page(
        "find-contractor.html",
        "Как подбирается мастер",
        "Критерии и порядок подбора мастера в ПРАКСЕЛЬТА Маркет.",
        hero("Клиентам", "Сначала подходящий мастер — потом раскрытие контакта", "Подбор учитывает город, район, категорию, график, загрузку и необходимые документы. Платный приоритет не отменяет проверки.")
        + """<section><p class="eyebrow">По умолчанию</p><h2>Последовательный подбор</h2><ol class="timeline"><li>Система находит первого подходящего мастера.</li><li>Мастер видит обезличенную задачу и условия.</li><li>После принятия и проверки согласия контакт раскрывается этому мастеру.</li><li>Если мастер отказался или не ответил вовремя, система переходит к следующему.</li></ol></section><section><h2>Что означает «проверен»</h2><p>Рядом со статусом всегда должно быть написано, что именно проверено: контакт, регистрационные сведения, категория работ, срок действия документа. Один общий значок не заменяет эту расшифровку.</p></section>""",
    )

    page(
        "for-contractors.html",
        "Стать мастером",
        "Условия тестового подключения мастеров к ПРАКСЕЛЬТА Маркет.",
        hero("Мастерам и сервисным компаниям", "Получайте только те задачи, которые готовы рассмотреть", "Вы заранее задаёте города, районы, категории, марки, график и лимит. Перед принятием видны описание, срочность, эксклюзивность и цена заявки — но не контакт клиента.")
        + """<section><p class="eyebrow">Воронка подключения</p><h2>От анкеты до тестовых заявок</h2><ol class="timeline"><li>Анкета и подтверждение рабочего контакта.</li><li>Проверка юридического статуса, категорий и документов.</li><li>Тестовый режим под ручным контролем.</li><li>Первые синтетические или отдельно разрешённые заявки.</li><li>Активный статус с лимитами и возможностью поставить поток на паузу.</li></ol></section><section class="two-col"><article><h3>Что вы отмечаете</h3><p>Принял, связался, перезвонить, выезд назначен, работа начата, нужна запчасть, работа выполнена, перенос или спор.</p></article><article><h3>Чего система не решает за вас</h3><p>Стоимость ремонта, техническое заключение, совместимость детали, гарантийные обязательства и безопасность работ.</p></article></section><section class="safe-promise"><p class="eyebrow">До production</p><h2>Реальные заявки и списания выключены</h2><p>Публичная страница — описание будущего пилота. Она не означает, что мастер принят или документы уже проверены.</p></section>""",
    )

    page(
        "for-suppliers.html",
        "Стать поставщиком",
        "Условия тестового подключения поставщиков к ПРАКСЕЛЬТА Маркет.",
        hero("Поставщикам", "Отвечайте на конкретный запрос детали", "Мастер указывает марку, модель, артикул или фото. Поставщик отвечает по наличию, цене, сроку, гарантии и доставке. Контакт конечного клиента для этого не нужен.")
        + """<section><h2>Что проверяем до подключения</h2><div class="check-list"><li>юридические сведения и регионы;</li><li>марки, категории и склады;</li><li>гарантию, возвраты и доставку;</li><li>актуальность остатков;</li><li>правила атрибуции и сверки;</li><li>происхождение товара.</li></div></section><section><h2>Как подтверждается рекомендация</h2><p>Через referral ID, промокод, номер запроса, webhook или CSV-сверку. Вознаграждение рассчитывается только после подтверждения заказа и учёта возврата. Начисление не равно оплате.</p></section><section class="safe-promise"><p class="eyebrow">Юридический gate</p><h2>Реальные проценты поставщиков выключены</h2><p>Модель договора, размер вознаграждения, налоговый режим и правила маркировки ещё требуют отдельного решения. В коде нет универсального процента.</p></section>""",
    )

    page(
        "find-part.html",
        "Поиск запчасти",
        "Как мастер запрашивает запчасть без лишних данных клиента.",
        hero("Мастерам", "Один запрос — несколько проверяемых предложений", "Укажите оборудование, деталь, артикул, количество, город и срочность. Поставщик не получает контакт конечного клиента.")
        + """<section><h2>В предложении поставщика</h2><div class="check-list"><li>наличие и цена;</li><li>производитель;</li><li>оригинал или аналог;</li><li>гарантия;</li><li>срок и доставка;</li><li>срок действия предложения.</li></div><p class="micro">Система не гарантирует совместимость детали автоматически. Источник данных показывается, а финальную проверку выполняет специалист.</p></section>""",
    )

    page(
        "supplier-network.html",
        "Сеть поставщиков",
        "Принципы сети проверяемых поставщиков ПРАКСЕЛЬТА.",
        hero("ПРАКСЕЛЬТА Маркет", "Поставщик отвечает за товар, ПРАКСЕЛЬТА связывает заказ с конкретным запросом", "Покупка и чек остаются у поставщика. ПРАКСЕЛЬТА передаёт идентификатор рекомендации и сверяет подтверждённый заказ после периода возврата.")
        + """<section class="two-col"><article><h2>Органические варианты</h2><p>Подбираются по наличию, региону, сроку и условиям. Платное размещение не должно скрывать остальные подходящие предложения.</p></article><article><h2>Платное размещение</h2><p>Помечается явно. Оно не отменяет проверку поставщика, товара и совместимости.</p></article></section>""",
    )

    page(
        "how-it-works.html",
        "Как работает система",
        "Подробный путь заявки в ПРАКСЕЛЬТА Маркет.",
        hero("Как работает", "Каждое действие оставляет понятный статус", "Система различает «получено», «квалифицировано», «предложено», «принято», «контакт раскрыт», «выезд состоялся» и «работа выполнена». Один статус не подменяет другой.")
        + """<section><ol class="market-flow vertical"><li><strong>1. Получено</strong><span>Источник, согласие и технический ID зафиксированы.</span></li><li><strong>2. Проверено</strong><span>Контакт подтверждён, категория поддерживается, дубль и аварийные признаки проверены.</span></li><li><strong>3. Предложено</strong><span>Мастер видит обезличенную карточку, цену и правила возврата.</span></li><li><strong>4. Принято</strong><span>Цена фиксируется; в sandbox создаётся только тестовая запись списания.</span></li><li><strong>5. Контакт раскрыт</strong><span>Только в пределах согласия и с отдельной записью в журнале.</span></li><li><strong>6. Работа</strong><span>Статусы отмечает мастер; система не выдумывает результат звонка.</span></li><li><strong>7. Деталь</strong><span>Запрос поставщикам не содержит лишних данных клиента.</span></li></ol></section>""",
    )

    page(
        "lead-quality-policy.html",
        "Правила качественной заявки",
        "Какая заявка считается квалифицированной и когда возможен возврат.",
        hero("Публичные правила", "Платная заявка — не просто найденный телефон", "Нужны подтверждённый контакт, поддерживаемый город и категория, понятная актуальная задача, отсутствие технического дубля и действующее согласие на передачу.")
        + """<section class="two-col"><article><h2>Возможен возврат или замена</h2><ul><li>несуществующий контакт;</li><li>технический дубль;</li><li>неверный город или категория;</li><li>клиент заявку не оставлял;</li><li>системная ошибка;</li><li>тот же контакт уже раскрывался этому мастеру по той же задаче.</li></ul></article><article><h2>Не является автоматическим возвратом</h2><ul><li>клиент выбрал другого мастера после разговора;</li><li>мастер ответил поздно;</li><li>стороны не договорились о цене;</li><li>детали нет в наличии;</li><li>клиент передумал;</li><li>мастер не смог выполнить работу по своей причине.</li></ul></article></section><p class="legal-draft">DRAFT — ТРЕБУЕТСЯ ПРОВЕРКА ЮРИСТА</p>""",
    )

    page(
        "contractor-verification.html",
        "Проверка мастеров",
        "Что именно проверяет ПРАКСЕЛЬТА перед допуском мастера.",
        hero("Проверка мастеров", "Статус объясняет, что проверено", "Контакт, регистрационные сведения, категории и срок действия документа показываются раздельно. Истёкший документ блокирует регулируемую работу.")
        + """<section><h2>Проверка не заменяет выбор клиента</h2><p>Даже подтверждённые сведения не являются гарантией результата конкретной работы. Клиент видит область проверки, условия мастера и может отказаться от предложения.</p></section><section class="safe-promise"><h2>Аварийные признаки не маршрутизируются</h2><p>Запах газа, хлопок, пожар, открытое пламя, срабатывание сигнализатора или угроза жизни переводят заявку в SAFETY_BLOCKED.</p></section>""",
    )

    page(
        "service-network-safety.html",
        "Безопасность сервисной сети",
        "Аварийные и регулируемые сценарии в ПРАКСЕЛЬТА Маркет.",
        hero("Безопасность", "Аварийная ситуация — не коммерческий лид", "При запахе газа, хлопке, пожаре, открытом пламени, срабатывании сигнализатора или угрозе жизни система прекращает коммерческую маршрутизацию.")
        + """<section><h2>Что видит клиент</h2><p>Предупреждение обратиться в официальную аварийную службу или по номеру 112. ПРАКСЕЛЬТА не даёт инструкций по самостоятельному ремонту газового оборудования.</p></section><section><h2>Регулируемые работы</h2><p>Допуск возможен только после отдельной проверки актуальных требований и документов исполнителя. Платный приоритет не обходит этот gate.</p></section>""",
    )

    page(
        "service-network-privacy.html",
        "Данные сервисной сети",
        "Как минимизируются и раскрываются данные клиента в тестовом контуре.",
        hero("Персональные данные", "Контакт скрыт до принятия заявки", "Согласие на подбор мастера фиксируется отдельно от согласия на рекламу. Клиент выбирает предел передачи: одному мастеру, последовательно, максимум трём или никому до собственного выбора.")
        + """<section><h2>Минимум данных</h2><p>Полный домашний адрес до необходимости не запрашивается. Контакт шифруется, не попадает в публичный Git и логи. Каждое раскрытие должно иметь время, получателя и основание.</p></section><section><h2>Отзыв согласия</h2><p>Если согласие отозвано до передачи, дальнейший подбор прекращается. Мастер не получает право использовать контакт для посторонней рекламы.</p></section><p class="legal-draft">DRAFT — ТРЕБУЕТСЯ ПРОВЕРКА ЮРИСТА</p>""",
    )

    page(
        "service-network-terms.html",
        "Условия сервисной сети",
        "Предварительные условия пилота ПРАКСЕЛЬТА Маркет.",
        hero("Предварительные условия", "Пилот ещё не принимает реальные деньги и заявки", "Эта версия описывает архитектуру и правила sandbox. Она не является объявлением production-запуска.")
        + """<section><h2>До запуска необходимо решить</h2><ul><li>организационно-правовой статус и налоговый режим;</li><li>договоры с мастерами и поставщиками;</li><li>пользовательские условия, согласия и чеки;</li><li>роль ПРАКСЕЛЬТЫ перед потребителем;</li><li>возвраты, споры и маркировку рекламы;</li><li>платёжного провайдера и кассовые требования.</li></ul></section><p class="legal-draft">DRAFT — ТРЕБУЕТСЯ ПРОВЕРКА ЮРИСТА</p>""",
    )

    page(
        "pricing.html",
        "Тарифы",
        "Единая тарифная лестница продвижения ПРАКСЕЛЬТЫ.",
        hero("Продвижение предпринимателей", "Начать можно с семидневного разбора", f"<span data-price-key=\"services.express.price_once\">{rub(express['price_once'])}</span> — работа ПРАКСЕЛЬТЫ. Авито клиент оплачивает напрямую, рекламный бюджет не входит, количество заявок не гарантируется.")
        + f"<section><p class=\"eyebrow\">Единый источник цен</p><h2>Пять уровней работы</h2>{pricing_cards}<p class=\"micro\">Экспресс может быть зачтён в первый месяц только при прямом условии в письменном заказе. Прибыль, налоги, себестоимость и закупочные цены не требуются.</p></section>",
    )

    page(
        "service-network-presentation.html",
        "Короткая презентация ПРАКСЕЛЬТА Маркет",
        "Короткая печатная презентация системы заявок, мастеров и поставщиков.",
        hero("Короткая презентация", "ПРАКСЕЛЬТА Маркет", "Заявки, мастера и поставщики в одной управляемой системе — сначала в ручном sandbox-пилоте Саратова и Энгельса.")
        + """<section class="presentation-grid"><article><span>01</span><h2>Клиент</h2><p>Описывает задачу и сам выбирает предел передачи контакта.</p></article><article><span>02</span><h2>Квалификация</h2><p>Подтверждаем контакт, отдельно фиксируем согласие, проверяем категорию, дубль и безопасность.</p></article><article><span>03</span><h2>Мастер</h2><p>Видит обезличенную карточку, цену и правила до принятия.</p></article><article><span>04</span><h2>Поставщик</h2><p>Отвечает на конкретный запрос детали без лишних данных клиента.</p></article><article><span>05</span><h2>ПРАКСЕЛЬТА</h2><p>Связывает подтверждённый заказ с конкретным запросом и не продаёт базу контактов.</p></article><article><span>06</span><h2>Пилот</h2><p>Саратов и Энгельс, котлы, ручной контроль, синтетические заявки, без реальных денег.</p></article></section>""",
    )


if __name__ == "__main__":
    render()
