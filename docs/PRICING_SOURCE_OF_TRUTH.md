# Единый источник продукта и цен

Публичный активный продукт:

```text
Управляемое продвижение и учёт обращений
Экспресс — 7 900 ₽ — 7 дней
```

Машиночитаемый источник — `pricing.json`:

- `active_product.name` задаёт каноническое название;
- `active_product.entry_tariff_id` указывает входной тариф;
- `services.express.price_once` должен быть равен `7900`;
- `services.express.duration_days` должен быть равен `7`;
- валюта — `RUB`.

Страницы направления создаются из `templates/local-growth/*.html` командой:

```powershell
python scripts/render_local_growth.py
```

Общие проверки:

```powershell
python scripts/check_public_site.py
python scripts/validate_active_product_v2.py --root .
pytest -q
```

Ручная правка тарифной суммы в сгенерированных страницах не допускается. Главная страница и локальный конструктор запроса обязаны совпадать с `pricing.json`.

Сторонние подписки, рекламный бюджет и платные размещения не входят в 7 900 ₽. Зачёт экспресс-разбора в первый месяц другого тарифа действует только тогда, когда это прямо записано в индивидуальном письменном заказе.

Публичная цена не является подтверждением продажи. Статусы `PAID`, `REVENUE` и `PROFIT` допускаются только через локальный evidence-ledger после письменного заказа, provider receipt, отсутствия возврата, delivery, acceptance и reconciliation.
