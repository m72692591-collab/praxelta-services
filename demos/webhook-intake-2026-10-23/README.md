# PRAXELTA — Webhook Lead Intake (synthetic local demo)

Small reference implementation for a **paid pilot proposal**: input JSON validation, local SQLite persistence, repeat-event idempotency, duplicate lead detection, and auditable processing results. Zero external APIs and zero paid dependencies. This is **not** deployed in production, does **not** send messages to Telegram/WhatsApp, and is not an n8n/Make export.

## Test
Python 3.10+: `python -m unittest -v test_intake.py`

## Run locally
`python intake.py` (binds only to `127.0.0.1:8765`)

```sh
curl -s -X POST http://127.0.0.1:8765/intake \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-001","email":"demo@example.com","name":"Demo Person","source":"website","message":"Need a quote"}'
```

Expected first result: `{"status":"accepted","lead_id":1,"operation":"created"}`. Same event ID + payload: `duplicate_event`; same event ID + changed payload: HTTP 409. Another event ID with same email updates the record.

## Pilot handover checklist
1. Confirm client webhook source, event identifier, fields and desired output.
2. Agree GDPR/data protection, retention/deletion, authorization, HTTPS and secret management for any production version.
3. Agree downstream API/CRM/messenger access through customer-owned accounts.
4. Add authenticated webhook verification, proper upstream delivery confirmations, a retry/outbox mechanism, rate limiting, monitoring, migrations, and backups before production deployment.
5. Test using synthetic and customer-approved non-sensitive test data; document acceptance cases.

This demo intentionally has **no authentication** (loopback only). Do not expose it to the public internet or pass real customer data into it.
