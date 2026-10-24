# PRAXELTA | Airtable → Telegram safe matching (offline demo)

An offline portfolio proof of concept for reliable record-to-recipient matching. This is not a copy of the client's system and does not imply access to their data or a completed contract.

## Run

Requires Python 3.9+; standard library only. No accounts, credentials, Telegram, Airtable, paid APIs, or internet needed.

```bash
python -m unittest discover -s tests -v
python demo.py
```

## Design

- Airtable-style `person` is an opaque synthetic record identifier, never a name or row number.
- Telegram `chat_id` is obtained after a simulated `/start`-like binding proof. This demo uses an HMAC token generated locally; a real implementation must issue short-lived, single-use tokens from a trusted server and validate the Telegram webhook secret / update authenticity, as well as bind the actual chat ID supplied by Telegram (not a client-supplied value).
- Binding is unique on both person and chat; reassignment is rejected until a separate re-verification flow exists.
- Unknown recipients fail closed: no fallback recipient, no broadcast.
- Delivery event IDs are idempotent; reusing an ID with different content or recipient is rejected.
- A SQLite transaction records delivery intent in a **durable local outbox** and `pending()` recovers queued messages after a process restart. **Not production-grade exactly-once delivery:** process crashes after external send but before acknowledgement can cause repeated sends; real deployments need retry policy, atomic claim/lease, delivery status and reconciliation. Telegram sendMessage itself does not provide a general exactly-once guarantee.
- Never put sensitive codes in logs; this demo prints only synthetic codes.

## Mapping to a real implementation

1. Inspect actual Airtable field schema and Telegram update source.
2. Verify recipient consent and identity using a short-lived one-time `/start` token.
3. Persist verified record-id ↔ chat-id mapping with unique constraints.
4. Store Airtable event ID and a payload digest to prevent duplicate dispatch.
5. Queue outgoing messages durably; handle retry, errors, and reconciliation.
6. Test using fake records before any authorized production rollout.

## Boundaries

No real Airtable or Telegram requests. No client data. No claim that the customer's exact defect has been diagnosed. The HMAC proof here is a simplified trust-boundary illustration, not a complete enrollment protocol. Local tests validate the pure matching logic only.

## Portfolio update: durable offline queue (v2)

- Pending delivery intents now persist in SQLite, including synthetic message payloads.
- `pending()` reads unsent intents after a process restart; `acknowledge(event)` simulates a confirmed send.
- Replayed event IDs are still rejected after acknowledgement; recipient/payload conflicts fail closed.
- **Important:** the local queue is *at-least-once intent*, not an exactly-once Telegram delivery system. A crash after a real network send but before acknowledgement could cause duplicate sending on retry. Production needs explicit retry policy, operator reconciliation, secure credential handling, short-lived single-use enrollment tokens, and an authenticated Telegram update handler. SQLite here is for a local demo, not a scalable multi-worker dispatcher.
- The persisted demo payload is plaintext in SQLite; do not use sensitive data without a production security design.

### Portfolio claim (accurate)

> Built and tested an offline Python/SQLite proof of concept for safe Airtable-record-to-Telegram-chat matching, conflict rejection, idempotent event intake, and restart-persistent delivery intents. Uses only synthetic data and the Python standard library. Not deployed to a client's systems.

## Security / implementation caveats

- The static demo HMAC token is reusable, not expiring and not linked to an authenticated Telegram update. Do not deploy this enrollment flow as-is.
- `chat_id` is supplied by the caller in this local simulation; production must extract it from a verified Telegram update.
- SQLite persists synthetic payloads in plaintext. Real codes need data minimization, access controls, retention and encryption as appropriate.
- `pending()` does not lease rows: multiple workers can race. This demonstration is single-worker only.
- The local test suite is not an end-to-end test of Telegram or Airtable.

## Verified locally on 2026-10-24

15 standard-library tests pass, including three simultaneous traders, concurrent replay of the same event on independent SQLite connections, recipient conflicts, and restart recovery. Intake transactions use `BEGIN IMMEDIATE` to serialize lookup-and-insert operations. Only canonical positive private-chat IDs below 2^52 are accepted; groups are excluded from this person-to-person example. These tests do not validate the live Make, Airtable or Telegram APIs.
