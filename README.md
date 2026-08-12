# Публичная витрина ПРАКСЕЛЬТЫ

Статический сайт услуг ПРАКСЕЛЬТЫ. Целевой адрес: `https://m72692591-collab.github.io/praxelta-services/`.

## Локальная проверка

```powershell
python scripts/render_local_growth.py
python scripts/render_service_network.py
python scripts/render_multicategory.py
python scripts/render_campaigns.py
python scripts/check_public_site.py
node scripts/test_service_network_js.mjs
python -m http.server 8000
```

Цены направления локального продвижения хранятся в `pricing.json`, а категории и правила их подключения — в `service-categories.json`. `scripts/render_multicategory.py` создаёт каталог и страницы первой волны для Саратова и Энгельса. `scripts/render_campaigns.py` создаёт только черновики кампаний: бюджет равен нулю, расход выключен.

Ближайший денежный продукт и границы работы при бюджете 0 ₽ зафиксированы в `docs/ZERO_BUDGET_MONETIZATION.md`.

PDF создаются командой `python scripts/generate_pdfs.py`. Зависимости для проверок перечислены в `requirements-dev.txt`.

## Границы

В публичном репозитории нет CRM, автоматической отправки сообщений и реальных контактов. `order.js` по-прежнему лишь формирует письмо и открывает Gmail или почтовое приложение. Тестовая форма `request-service.html` работает только в памяти страницы: сеть и постоянное хранилище не используются. Закрытый операционный контур находится в отдельном локальном проекте `praxelta-ops`.

Публикация разрешается только после прохождения migration deployment gate. Merge в `main`, deploy, реальная отправка, передача лида и рекламные расходы требуют отдельных подтверждений и включения соответствующих gates.
