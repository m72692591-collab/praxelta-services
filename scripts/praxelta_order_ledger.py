#!/usr/bin/env python3
"""Local-only evidence ledger for the PRAXELTA Express offer.

The ledger stores operational status in ``.praxelta-local``.  It never writes
customer contacts, bank statements, webhook bodies, credentials, or raw order
text to Git.  Evidence fields are SHA-256 references to records kept in their
proper protected systems (Gmail, bank/provider, local delivery package).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PRODUCT_ID = "managed_promotion_express_v1"
PRODUCT_NAME = "Управляемое продвижение и учёт обращений — Экспресс"
PRICE_RUB = 7900
CURRENCY = "RUB"
DURATION_DAYS = 7
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ORDER_ID_RE = re.compile(r"^PRX-EX-[0-9]{8}-[A-Z0-9]{8,24}$")


class LedgerError(RuntimeError):
    """Fail-closed operational error with a stable diagnostic code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_sha256(value: str, field: str) -> str:
    normalized = value.strip().lower()
    if not SHA256_RE.fullmatch(normalized):
        raise LedgerError("INVALID_SHA256", field)
    return normalized


def require_order_id(value: str) -> str:
    normalized = value.strip().upper()
    if not ORDER_ID_RE.fullmatch(normalized):
        raise LedgerError("INVALID_ORDER_ID")
    return normalized


def sha256_json(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


@dataclass(frozen=True)
class LedgerPaths:
    root: Path

    @property
    def private_root(self) -> Path:
        return self.root / ".praxelta-local" / "order-ledger"

    @property
    def database(self) -> Path:
        return self.private_root / "orders.sqlite3"

    @property
    def receipts(self) -> Path:
        return self.private_root / "receipts"


class OrderLedger:
    def __init__(self, root: Path) -> None:
        self.paths = LedgerPaths(root.resolve())
        self.paths.private_root.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.paths.database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        self.initialize()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "OrderLedger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                price_rub INTEGER NOT NULL,
                currency TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                scope_sha256 TEXT NOT NULL,
                customer_ref_sha256 TEXT NOT NULL,
                written_order_evidence_sha256 TEXT NOT NULL,
                written_order_confirmed INTEGER NOT NULL CHECK (written_order_confirmed IN (0,1)),
                order_status TEXT NOT NULL,
                payment_status TEXT NOT NULL,
                payment_provider TEXT,
                payment_id_sha256 TEXT UNIQUE,
                payment_evidence_sha256 TEXT,
                payment_confirmed_at_utc TEXT,
                refund_status TEXT NOT NULL,
                refund_evidence_sha256 TEXT,
                delivery_status TEXT NOT NULL,
                delivery_receipt_sha256 TEXT,
                acceptance_status TEXT NOT NULL,
                acceptance_receipt_sha256 TEXT,
                reconciliation_status TEXT NOT NULL,
                direct_costs_rub INTEGER,
                revenue_rub INTEGER,
                profit_rub INTEGER,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                CHECK (product_id = 'managed_promotion_express_v1'),
                CHECK (price_rub = 7900),
                CHECK (currency = 'RUB'),
                CHECK (duration_days = 7)
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL REFERENCES orders(order_id),
                event_type TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                evidence_sha256 TEXT NOT NULL,
                state_sha256 TEXT NOT NULL,
                occurred_at_utc TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def _row(self, order_id: str) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM orders WHERE order_id = ?",
            (require_order_id(order_id),),
        ).fetchone()
        if row is None:
            raise LedgerError("ORDER_NOT_FOUND", order_id)
        return row

    @staticmethod
    def _public_state(row: sqlite3.Row) -> dict[str, Any]:
        keys = (
            "order_id",
            "product_id",
            "product_name",
            "price_rub",
            "currency",
            "duration_days",
            "scope_sha256",
            "customer_ref_sha256",
            "written_order_evidence_sha256",
            "written_order_confirmed",
            "order_status",
            "payment_status",
            "payment_provider",
            "payment_id_sha256",
            "payment_evidence_sha256",
            "payment_confirmed_at_utc",
            "refund_status",
            "refund_evidence_sha256",
            "delivery_status",
            "delivery_receipt_sha256",
            "acceptance_status",
            "acceptance_receipt_sha256",
            "reconciliation_status",
            "direct_costs_rub",
            "revenue_rub",
            "profit_rub",
            "created_at_utc",
            "updated_at_utc",
        )
        state = {key: row[key] for key in keys}
        state["written_order_confirmed"] = bool(
            state["written_order_confirmed"]
        )
        state["first_real_payment_verified"] = (
            state["payment_status"] == "PROVIDER_CONFIRMED"
            and state["payment_id_sha256"] is not None
            and state["refund_status"] == "NONE"
        )
        state["revenue_verified"] = (
            state["reconciliation_status"] == "RECONCILED"
            and state["revenue_rub"] == PRICE_RUB
        )
        state["profit_verified"] = (
            state["reconciliation_status"] == "RECONCILED"
            and state["profit_rub"] is not None
            and state["direct_costs_rub"] is not None
        )
        return state

    def _receipt(
        self,
        order_id: str,
        event_type: str,
        evidence_sha256: str,
        state: dict[str, Any],
    ) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = self.paths.receipts / order_id / f"{stamp}-{event_type}.json"
        payload = {
            "schema_version": 1,
            "event_type": event_type,
            "recorded_at_utc": now_utc(),
            "order": state,
            "evidence_sha256": evidence_sha256,
            "raw_customer_data_stored": False,
            "raw_payment_data_stored": False,
            "credentials_stored": False,
            "repository_file": False,
        }
        atomic_json(path, payload)
        return path

    def _event(
        self,
        order_id: str,
        event_type: str,
        evidence_sha256: str,
        idempotency_key: str,
    ) -> tuple[dict[str, Any], Path, bool]:
        row = self._row(order_id)
        state = self._public_state(row)
        state_hash = sha256_json(state)
        try:
            self.connection.execute(
                """
                INSERT INTO events (
                    order_id, event_type, idempotency_key,
                    evidence_sha256, state_sha256, occurred_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    event_type,
                    idempotency_key,
                    evidence_sha256,
                    state_hash,
                    now_utc(),
                ),
            )
            self.connection.commit()
            created = True
        except sqlite3.IntegrityError:
            existing = self.connection.execute(
                """
                SELECT order_id, event_type, evidence_sha256, state_sha256
                FROM events WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if (
                existing is None
                or existing["order_id"] != order_id
                or existing["event_type"] != event_type
                or existing["evidence_sha256"] != evidence_sha256
                or existing["state_sha256"] != state_hash
            ):
                raise LedgerError("IDEMPOTENCY_CONFLICT", idempotency_key)
            created = False
        receipt = self._receipt(order_id, event_type, evidence_sha256, state)
        return state, receipt, created

    def register_order(
        self,
        *,
        order_id: str,
        scope_sha256: str,
        customer_ref_sha256: str,
        written_order_evidence_sha256: str,
    ) -> tuple[dict[str, Any], Path, bool]:
        order_id = require_order_id(order_id)
        scope_sha256 = require_sha256(scope_sha256, "scope_sha256")
        customer_ref_sha256 = require_sha256(
            customer_ref_sha256,
            "customer_ref_sha256",
        )
        written_order_evidence_sha256 = require_sha256(
            written_order_evidence_sha256,
            "written_order_evidence_sha256",
        )
        timestamp = now_utc()
        values = (
            order_id,
            PRODUCT_ID,
            PRODUCT_NAME,
            PRICE_RUB,
            CURRENCY,
            DURATION_DAYS,
            scope_sha256,
            customer_ref_sha256,
            written_order_evidence_sha256,
            1,
            "WRITTEN_ORDER_CONFIRMED",
            "NOT_VERIFIED",
            "NONE",
            "NOT_STARTED",
            "NOT_REQUESTED",
            "NOT_READY",
            timestamp,
            timestamp,
        )
        try:
            self.connection.execute(
                """
                INSERT INTO orders (
                    order_id, product_id, product_name, price_rub,
                    currency, duration_days, scope_sha256,
                    customer_ref_sha256, written_order_evidence_sha256,
                    written_order_confirmed, order_status, payment_status,
                    refund_status, delivery_status, acceptance_status,
                    reconciliation_status, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            self.connection.commit()
        except sqlite3.IntegrityError:
            existing = self._public_state(self._row(order_id))
            immutable = {
                "scope_sha256": scope_sha256,
                "customer_ref_sha256": customer_ref_sha256,
                "written_order_evidence_sha256": written_order_evidence_sha256,
                "product_id": PRODUCT_ID,
                "price_rub": PRICE_RUB,
                "currency": CURRENCY,
                "duration_days": DURATION_DAYS,
            }
            if any(existing[key] != value for key, value in immutable.items()):
                raise LedgerError("ORDER_ID_CONFLICT", order_id)
        return self._event(
            order_id,
            "WRITTEN_ORDER_CONFIRMED",
            written_order_evidence_sha256,
            f"order:{order_id}:{written_order_evidence_sha256}",
        )

    def confirm_payment(
        self,
        *,
        order_id: str,
        provider: str,
        payment_id_sha256: str,
        evidence_sha256: str,
        confirmed_at_utc: str,
    ) -> tuple[dict[str, Any], Path, bool]:
        order_id = require_order_id(order_id)
        payment_id_sha256 = require_sha256(
            payment_id_sha256,
            "payment_id_sha256",
        )
        evidence_sha256 = require_sha256(
            evidence_sha256,
            "payment_evidence_sha256",
        )
        provider = provider.strip()
        if not re.fullmatch(r"[A-Za-z0-9._ -]{2,80}", provider):
            raise LedgerError("INVALID_PAYMENT_PROVIDER")
        row = self._row(order_id)
        if not bool(row["written_order_confirmed"]):
            raise LedgerError("WRITTEN_ORDER_NOT_CONFIRMED")
        if row["refund_status"] != "NONE":
            raise LedgerError("REFUND_ALREADY_RECORDED")
        if row["payment_status"] == "PROVIDER_CONFIRMED":
            if (
                row["payment_id_sha256"] != payment_id_sha256
                or row["payment_evidence_sha256"] != evidence_sha256
                or row["payment_provider"] != provider
            ):
                raise LedgerError("PAYMENT_CONFLICT")
        else:
            try:
                self.connection.execute(
                    """
                    UPDATE orders SET
                        payment_status = 'PROVIDER_CONFIRMED',
                        payment_provider = ?,
                        payment_id_sha256 = ?,
                        payment_evidence_sha256 = ?,
                        payment_confirmed_at_utc = ?,
                        updated_at_utc = ?
                    WHERE order_id = ?
                    """,
                    (
                        provider,
                        payment_id_sha256,
                        evidence_sha256,
                        confirmed_at_utc,
                        now_utc(),
                        order_id,
                    ),
                )
                self.connection.commit()
            except sqlite3.IntegrityError as exc:
                raise LedgerError(
                    "DUPLICATE_PAYMENT_IDENTIFIER",
                    payment_id_sha256,
                ) from exc
        return self._event(
            order_id,
            "PROVIDER_CONFIRMED_PAYMENT",
            evidence_sha256,
            f"payment:{payment_id_sha256}",
        )

    def record_delivery(
        self,
        *,
        order_id: str,
        receipt_sha256: str,
    ) -> tuple[dict[str, Any], Path, bool]:
        order_id = require_order_id(order_id)
        receipt_sha256 = require_sha256(
            receipt_sha256,
            "delivery_receipt_sha256",
        )
        row = self._row(order_id)
        if row["payment_status"] != "PROVIDER_CONFIRMED":
            raise LedgerError("PAYMENT_NOT_VERIFIED")
        if row["delivery_status"] == "DELIVERED":
            if row["delivery_receipt_sha256"] != receipt_sha256:
                raise LedgerError("DELIVERY_CONFLICT")
        else:
            self.connection.execute(
                """
                UPDATE orders SET
                    delivery_status = 'DELIVERED',
                    delivery_receipt_sha256 = ?,
                    acceptance_status = 'PENDING',
                    updated_at_utc = ?
                WHERE order_id = ?
                """,
                (receipt_sha256, now_utc(), order_id),
            )
            self.connection.commit()
        return self._event(
            order_id,
            "DELIVERED",
            receipt_sha256,
            f"delivery:{order_id}:{receipt_sha256}",
        )

    def record_acceptance(
        self,
        *,
        order_id: str,
        receipt_sha256: str,
    ) -> tuple[dict[str, Any], Path, bool]:
        order_id = require_order_id(order_id)
        receipt_sha256 = require_sha256(
            receipt_sha256,
            "acceptance_receipt_sha256",
        )
        row = self._row(order_id)
        if row["delivery_status"] != "DELIVERED":
            raise LedgerError("DELIVERY_NOT_VERIFIED")
        if row["acceptance_status"] == "ACCEPTED":
            if row["acceptance_receipt_sha256"] != receipt_sha256:
                raise LedgerError("ACCEPTANCE_CONFLICT")
        else:
            self.connection.execute(
                """
                UPDATE orders SET
                    acceptance_status = 'ACCEPTED',
                    acceptance_receipt_sha256 = ?,
                    updated_at_utc = ?
                WHERE order_id = ?
                """,
                (receipt_sha256, now_utc(), order_id),
            )
            self.connection.commit()
        return self._event(
            order_id,
            "CLIENT_ACCEPTED",
            receipt_sha256,
            f"acceptance:{order_id}:{receipt_sha256}",
        )

    def record_refund(
        self,
        *,
        order_id: str,
        evidence_sha256: str,
    ) -> tuple[dict[str, Any], Path, bool]:
        order_id = require_order_id(order_id)
        evidence_sha256 = require_sha256(
            evidence_sha256,
            "refund_evidence_sha256",
        )
        row = self._row(order_id)
        if row["payment_status"] != "PROVIDER_CONFIRMED":
            raise LedgerError("PAYMENT_NOT_VERIFIED")
        if row["reconciliation_status"] == "RECONCILED":
            raise LedgerError("RECONCILIATION_ALREADY_FINAL")
        if row["refund_status"] == "FULL":
            if row["refund_evidence_sha256"] != evidence_sha256:
                raise LedgerError("REFUND_CONFLICT")
        else:
            self.connection.execute(
                """
                UPDATE orders SET
                    refund_status = 'FULL',
                    refund_evidence_sha256 = ?,
                    payment_status = 'REFUNDED',
                    revenue_rub = 0,
                    profit_rub = NULL,
                    reconciliation_status = 'NOT_READY',
                    updated_at_utc = ?
                WHERE order_id = ?
                """,
                (evidence_sha256, now_utc(), order_id),
            )
            self.connection.commit()
        return self._event(
            order_id,
            "FULL_REFUND",
            evidence_sha256,
            f"refund:{order_id}:{evidence_sha256}",
        )

    def reconcile(
        self,
        *,
        order_id: str,
        direct_costs_rub: int,
        evidence_sha256: str,
    ) -> tuple[dict[str, Any], Path, bool]:
        order_id = require_order_id(order_id)
        evidence_sha256 = require_sha256(
            evidence_sha256,
            "reconciliation_evidence_sha256",
        )
        if direct_costs_rub < 0 or direct_costs_rub > PRICE_RUB:
            raise LedgerError("DIRECT_COSTS_OUT_OF_RANGE")
        row = self._row(order_id)
        required = {
            "written_order_confirmed": bool(row["written_order_confirmed"]),
            "payment_status": row["payment_status"] == "PROVIDER_CONFIRMED",
            "refund_status": row["refund_status"] == "NONE",
            "delivery_status": row["delivery_status"] == "DELIVERED",
            "acceptance_status": row["acceptance_status"] == "ACCEPTED",
        }
        missing = [key for key, ready in required.items() if not ready]
        if missing:
            raise LedgerError("RECONCILIATION_GATE_INCOMPLETE", ",".join(missing))
        profit = PRICE_RUB - direct_costs_rub
        if row["reconciliation_status"] == "RECONCILED":
            if (
                row["direct_costs_rub"] != direct_costs_rub
                or row["revenue_rub"] != PRICE_RUB
                or row["profit_rub"] != profit
            ):
                raise LedgerError("RECONCILIATION_CONFLICT")
        else:
            self.connection.execute(
                """
                UPDATE orders SET
                    reconciliation_status = 'RECONCILED',
                    direct_costs_rub = ?,
                    revenue_rub = ?,
                    profit_rub = ?,
                    updated_at_utc = ?
                WHERE order_id = ?
                """,
                (
                    direct_costs_rub,
                    PRICE_RUB,
                    profit,
                    now_utc(),
                    order_id,
                ),
            )
            self.connection.commit()
        return self._event(
            order_id,
            "RECONCILED",
            evidence_sha256,
            f"reconcile:{order_id}:{evidence_sha256}",
        )

    def status(self, order_id: str) -> dict[str, Any]:
        return self._public_state(self._row(order_id))

    def all_statuses(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM orders ORDER BY created_at_utc, order_id"
        ).fetchall()
        return [self._public_state(row) for row in rows]


def result_payload(
    state: dict[str, Any],
    receipt: Path | None = None,
    created: bool | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "OK",
        "order": state,
    }
    if receipt is not None:
        payload["receipt_path"] = str(receipt)
    if created is not None:
        payload["event_created"] = created
    return payload


def emit(value: dict[str, Any] | list[dict[str, Any]]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = result.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    register = sub.add_parser("register")
    register.add_argument("--order-id", required=True)
    register.add_argument("--scope-sha256", required=True)
    register.add_argument("--customer-ref-sha256", required=True)
    register.add_argument("--written-order-evidence-sha256", required=True)

    payment = sub.add_parser("payment")
    payment.add_argument("--order-id", required=True)
    payment.add_argument("--provider", required=True)
    payment.add_argument("--payment-id-sha256", required=True)
    payment.add_argument("--evidence-sha256", required=True)
    payment.add_argument("--confirmed-at-utc", required=True)

    delivery = sub.add_parser("delivery")
    delivery.add_argument("--order-id", required=True)
    delivery.add_argument("--receipt-sha256", required=True)

    acceptance = sub.add_parser("accept")
    acceptance.add_argument("--order-id", required=True)
    acceptance.add_argument("--receipt-sha256", required=True)

    refund = sub.add_parser("refund")
    refund.add_argument("--order-id", required=True)
    refund.add_argument("--evidence-sha256", required=True)

    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--order-id", required=True)
    reconcile.add_argument("--direct-costs-rub", required=True, type=int)
    reconcile.add_argument("--evidence-sha256", required=True)

    status = sub.add_parser("status")
    status.add_argument("--order-id")
    return result


def main(argv: Iterable[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.root)
    try:
        with OrderLedger(root) as ledger:
            if args.command == "init":
                emit(
                    {
                        "schema_version": 1,
                        "status": "INITIALIZED",
                        "database_path": str(ledger.paths.database),
                        "inside_git": False,
                    }
                )
                return 0
            if args.command == "register":
                emit(
                    result_payload(
                        *ledger.register_order(
                            order_id=args.order_id,
                            scope_sha256=args.scope_sha256,
                            customer_ref_sha256=args.customer_ref_sha256,
                            written_order_evidence_sha256=(
                                args.written_order_evidence_sha256
                            ),
                        )
                    )
                )
                return 0
            if args.command == "payment":
                emit(
                    result_payload(
                        *ledger.confirm_payment(
                            order_id=args.order_id,
                            provider=args.provider,
                            payment_id_sha256=args.payment_id_sha256,
                            evidence_sha256=args.evidence_sha256,
                            confirmed_at_utc=args.confirmed_at_utc,
                        )
                    )
                )
                return 0
            if args.command == "delivery":
                emit(
                    result_payload(
                        *ledger.record_delivery(
                            order_id=args.order_id,
                            receipt_sha256=args.receipt_sha256,
                        )
                    )
                )
                return 0
            if args.command == "accept":
                emit(
                    result_payload(
                        *ledger.record_acceptance(
                            order_id=args.order_id,
                            receipt_sha256=args.receipt_sha256,
                        )
                    )
                )
                return 0
            if args.command == "refund":
                emit(
                    result_payload(
                        *ledger.record_refund(
                            order_id=args.order_id,
                            evidence_sha256=args.evidence_sha256,
                        )
                    )
                )
                return 0
            if args.command == "reconcile":
                emit(
                    result_payload(
                        *ledger.reconcile(
                            order_id=args.order_id,
                            direct_costs_rub=args.direct_costs_rub,
                            evidence_sha256=args.evidence_sha256,
                        )
                    )
                )
                return 0
            if args.command == "status":
                emit(
                    ledger.status(args.order_id)
                    if args.order_id
                    else ledger.all_statuses()
                )
                return 0
    except LedgerError as exc:
        emit(
            {
                "schema_version": 1,
                "status": "BLOCKED_WITH_EXACT_EVIDENCE",
                "error_code": exc.code,
                "detail": exc.detail,
            }
        )
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
