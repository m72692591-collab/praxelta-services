from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.praxelta_order_ledger import LedgerError, OrderLedger, PRICE_RUB

ORDER_1 = "PRX-EX-20260820-ABCDEF12"
ORDER_2 = "PRX-EX-20260820-ABCDEF34"
SCOPE = "1" * 64
CUSTOMER = "2" * 64
WRITTEN = "3" * 64
PAYMENT_ID = "4" * 64
PAYMENT_EVIDENCE = "5" * 64
DELIVERY = "6" * 64
ACCEPTANCE = "7" * 64
RECONCILIATION = "8" * 64
REFUND = "9" * 64


@pytest.fixture()
def ledger_root() -> Path:
    with tempfile.TemporaryDirectory() as directory:
        yield Path(directory)


def register(ledger: OrderLedger, order_id: str = ORDER_1):
    return ledger.register_order(
        order_id=order_id,
        scope_sha256=SCOPE,
        customer_ref_sha256=CUSTOMER,
        written_order_evidence_sha256=WRITTEN,
    )


def paid(ledger: OrderLedger, order_id: str = ORDER_1):
    register(ledger, order_id)
    return ledger.confirm_payment(
        order_id=order_id,
        provider="Bank provider",
        payment_id_sha256=PAYMENT_ID,
        evidence_sha256=PAYMENT_EVIDENCE,
        confirmed_at_utc="2026-08-20T10:00:00+00:00",
    )


def test_register_is_idempotent_and_fixed_to_exact_offer(ledger_root: Path) -> None:
    with OrderLedger(ledger_root) as ledger:
        first_state, first_receipt, first_created = register(ledger)
        second_state, second_receipt, second_created = register(ledger)
        assert first_created is True
        assert second_created is False
        assert first_state == second_state
        assert first_state["price_rub"] == 7900
        assert first_state["currency"] == "RUB"
        assert first_state["duration_days"] == 7
        assert first_state["written_order_confirmed"] is True
        assert first_state["payment_status"] == "NOT_VERIFIED"
        assert first_state["revenue_verified"] is False
        assert first_state["profit_verified"] is False
        assert first_receipt.is_file()
        assert second_receipt.is_file()
        assert str(first_receipt).startswith(
            str(ledger_root / ".praxelta-local")
        )


def test_same_order_id_with_changed_scope_is_rejected(ledger_root: Path) -> None:
    with OrderLedger(ledger_root) as ledger:
        register(ledger)
        with pytest.raises(LedgerError, match="ORDER_ID_CONFLICT"):
            ledger.register_order(
                order_id=ORDER_1,
                scope_sha256="a" * 64,
                customer_ref_sha256=CUSTOMER,
                written_order_evidence_sha256=WRITTEN,
            )


def test_payment_requires_written_order(ledger_root: Path) -> None:
    with OrderLedger(ledger_root) as ledger:
        with pytest.raises(LedgerError, match="ORDER_NOT_FOUND"):
            ledger.confirm_payment(
                order_id=ORDER_1,
                provider="Bank provider",
                payment_id_sha256=PAYMENT_ID,
                evidence_sha256=PAYMENT_EVIDENCE,
                confirmed_at_utc="2026-08-20T10:00:00+00:00",
            )


def test_provider_payment_is_idempotent(ledger_root: Path) -> None:
    with OrderLedger(ledger_root) as ledger:
        register(ledger)
        first_state, _, first_created = ledger.confirm_payment(
            order_id=ORDER_1,
            provider="Bank provider",
            payment_id_sha256=PAYMENT_ID,
            evidence_sha256=PAYMENT_EVIDENCE,
            confirmed_at_utc="2026-08-20T10:00:00+00:00",
        )
        second_state, _, second_created = ledger.confirm_payment(
            order_id=ORDER_1,
            provider="Bank provider",
            payment_id_sha256=PAYMENT_ID,
            evidence_sha256=PAYMENT_EVIDENCE,
            confirmed_at_utc="2026-08-20T10:00:00+00:00",
        )
        assert first_created is True
        assert second_created is False
        assert first_state == second_state
        assert first_state["first_real_payment_verified"] is True
        assert first_state["revenue_verified"] is False


def test_payment_identifier_cannot_be_reused_for_another_order(
    ledger_root: Path,
) -> None:
    with OrderLedger(ledger_root) as ledger:
        register(ledger, ORDER_1)
        register(ledger, ORDER_2)
        ledger.confirm_payment(
            order_id=ORDER_1,
            provider="Bank provider",
            payment_id_sha256=PAYMENT_ID,
            evidence_sha256=PAYMENT_EVIDENCE,
            confirmed_at_utc="2026-08-20T10:00:00+00:00",
        )
        with pytest.raises(
            LedgerError,
            match="DUPLICATE_PAYMENT_IDENTIFIER",
        ):
            ledger.confirm_payment(
                order_id=ORDER_2,
                provider="Bank provider",
                payment_id_sha256=PAYMENT_ID,
                evidence_sha256=PAYMENT_EVIDENCE,
                confirmed_at_utc="2026-08-20T10:01:00+00:00",
            )


def test_delivery_requires_verified_payment(ledger_root: Path) -> None:
    with OrderLedger(ledger_root) as ledger:
        register(ledger)
        with pytest.raises(LedgerError, match="PAYMENT_NOT_VERIFIED"):
            ledger.record_delivery(
                order_id=ORDER_1,
                receipt_sha256=DELIVERY,
            )


def test_acceptance_requires_delivery(ledger_root: Path) -> None:
    with OrderLedger(ledger_root) as ledger:
        paid(ledger)
        with pytest.raises(LedgerError, match="DELIVERY_NOT_VERIFIED"):
            ledger.record_acceptance(
                order_id=ORDER_1,
                receipt_sha256=ACCEPTANCE,
            )


def test_reconciliation_requires_complete_chain(ledger_root: Path) -> None:
    with OrderLedger(ledger_root) as ledger:
        paid(ledger)
        with pytest.raises(
            LedgerError,
            match="RECONCILIATION_GATE_INCOMPLETE",
        ):
            ledger.reconcile(
                order_id=ORDER_1,
                direct_costs_rub=900,
                evidence_sha256=RECONCILIATION,
            )


def test_complete_chain_verifies_revenue_and_profit(ledger_root: Path) -> None:
    with OrderLedger(ledger_root) as ledger:
        paid(ledger)
        ledger.record_delivery(
            order_id=ORDER_1,
            receipt_sha256=DELIVERY,
        )
        ledger.record_acceptance(
            order_id=ORDER_1,
            receipt_sha256=ACCEPTANCE,
        )
        state, receipt, created = ledger.reconcile(
            order_id=ORDER_1,
            direct_costs_rub=900,
            evidence_sha256=RECONCILIATION,
        )
        assert created is True
        assert state["reconciliation_status"] == "RECONCILED"
        assert state["revenue_rub"] == PRICE_RUB
        assert state["profit_rub"] == 7000
        assert state["revenue_verified"] is True
        assert state["profit_verified"] is True
        assert receipt.is_file()


def test_refund_prevents_revenue_claim(ledger_root: Path) -> None:
    with OrderLedger(ledger_root) as ledger:
        paid(ledger)
        state, _, _ = ledger.record_refund(
            order_id=ORDER_1,
            evidence_sha256=REFUND,
        )
        assert state["payment_status"] == "REFUNDED"
        assert state["refund_status"] == "FULL"
        assert state["revenue_rub"] == 0
        assert state["first_real_payment_verified"] is False
        assert state["revenue_verified"] is False
        with pytest.raises(
            LedgerError,
            match="RECONCILIATION_GATE_INCOMPLETE",
        ):
            ledger.reconcile(
                order_id=ORDER_1,
                direct_costs_rub=0,
                evidence_sha256=RECONCILIATION,
            )


def test_no_database_or_receipt_is_written_to_repository_root(
    ledger_root: Path,
) -> None:
    with OrderLedger(ledger_root) as ledger:
        register(ledger)
        assert ledger.paths.database.is_file()
        assert ledger.paths.database.parent.name == "order-ledger"
        assert ledger.paths.database.parents[1].name == ".praxelta-local"
        assert not list(ledger_root.glob("*.sqlite3"))
        assert not list(ledger_root.glob("*.json"))
