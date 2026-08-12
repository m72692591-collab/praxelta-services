# Матрица регистрации площадок

Проверено 13 августа 2026 года. Машиночитаемый источник: `platform-registration.json`.

| Площадка | Фактический статус | Следующий gate |
|---|---|---|
| Сайт GitHub Pages | активна текущая опубликованная версия | новая ветка не публикуется при `PUBLIC_DEPLOY=OFF` |
| Яндекс Бизнес | данные не отправлены | отдельный корпоративный Яндекс ID, рабочий телефон, OTP, модерация |
| Яндекс Директ | кампания не создана в кабинете | supply gate и точный CampaignApproval; бюджет OFF |
| VK-сообщество | live-проверка не завершена | проверить дубль и авторизованный аккаунт |
| VK Реклама | не запущена | supply, оферта и CampaignApproval; бюджет OFF |
| Авито Услуги | `RESEARCH_REQUIRED` | подтвердить допустимость модели подбора мастера |
| 2ГИС | `NOT_ELIGIBLE` при текущих данных | не указывать вымышленный адрес; нужна реально подтверждаемая организация/точка |
| Telegram-канал | активный публичный URL `https://t.me/praxelta_services_ru` | только контент после редакционного approval |
| Telegram-бот | активный публичный профиль `https://t.me/praxelta_service_admin_bot`, транспорт OFF | backend, secret store и отдельный deploy approval |
| Дзен | live-проверка не завершена | проверить дубль, вход и human terms |
| Телефония | провайдер не выбран | цена неизвестна, legal/privacy review и отдельное финансовое approval |

## Официальные источники

- Яндекс Бизнес: `https://yandex.ru/support/business-priority/ru/add-company/add-org` и `https://yandex.ru/support/business-priority/ru/online-company`. Онлайн-компания указывает регион, телефон и сайт; номер подтверждается SMS или звонком; заявка проходит проверку.
- Требования Яндекс Бизнеса: `https://yandex.ru/support/business-priority/ru/add-company/info-terms`.
- 2ГИС: `https://help.2gis.ru/question/kak-dobavit-kompaniyu-v-2gis`. Сведения размещаются после проверки, представитель заполняет форму, затем компания подтверждается звонком.
- Telegram Bot API: `https://core.telegram.org/bots/faq`. Бот создаётся через BotFather и подключается к backend; токен не хранится в репозитории.

## Browser receipt

Официальные формы были открыты через доступные browser routes. Встроенный браузер не подключил webview; Chrome открыл вкладку Яндекс Бизнеса, но навигация и чтение экрана завершились тайм-аутом. Несекретные поля не заполнены, submission не было, новый профиль не создан. Статус этого маршрута: `ROUTE_UNAVAILABLE`, а не `FORM_PREFILLED`.
