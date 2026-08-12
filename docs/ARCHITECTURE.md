# Архитектура ПРАКСЕЛЬТА Маркет

## Публичный контур

Статический GitHub Pages содержит тексты, обезличенные примеры, тестовую форму и безопасный JavaScript. `request-service.html` не отправляет и не сохраняет данные: `connect-src 'none'`, `form-action 'none'`, в скрипте нет сетевых и постоянных хранилищ. `order.js` не изменён по смыслу и по-прежнему только собирает письмо.

## Закрытый контур

Соседний локальный проект `praxelta-ops` использует FastAPI, SQLAlchemy и SQLite. Его поток:

`InboundSourceAdapter → ServiceRequest → Consent → Qualification → LeadRouter → LeadOffer → sandbox LeadCharge → ContactDisclosureEvent → WorkOrder → PartRequest → SupplierOffer → ReferralAttribution → sandbox CommissionEvent`.

Публичный сайт не подключён к локальной базе. Реальный backend и его размещение требуют отдельного проекта развёртывания и security review.

## Инварианты

- `CLIENT_OWNED_LEAD` не распределяется чужому мастеру.
- `PRAXELTA_MARKETPLACE_LEAD` передаётся только в пределах согласия.
- контакт шифруется и скрыт до принятия;
- аварийные признаки дают `SAFETY_BLOCKED`;
- цена копируется в предложение и не меняется задним числом;
- начисление и оплата — разные поля и события;
- все production side effects выключены режимом `NPD_PRELAUNCH`.
