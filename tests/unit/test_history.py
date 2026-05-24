"""Unit tests for GetTransactionHistoryUseCase."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.use_cases.get_transaction_history import (
    GetTransactionHistoryUseCase,
)
from app.domain.entities.transaction import Transaction
from app.domain.exceptions.errors import ClientNotFoundError
from app.domain.value_objects.enums import TransactionType
from app.domain.value_objects.money import Money


def _txn(client_id: str, ts: datetime, ttype: TransactionType) -> Transaction:
    return Transaction(
        id=f"txn-{ts.isoformat()}",
        client_id=client_id,
        type=ttype,
        fund_id="3",
        amount=Money.of(50_000),
        created_at=ts,
    )


def test_history_returns_newest_first(repo, sample_client):
    repo.save_client(sample_client)
    older = _txn(sample_client.id, datetime(2026, 1, 1, tzinfo=UTC), TransactionType.OPEN)
    newer = _txn(sample_client.id, datetime(2026, 2, 1, tzinfo=UTC), TransactionType.CANCEL)
    repo.transactions.extend([older, newer])
    use_case = GetTransactionHistoryUseCase(repo)

    history = use_case.execute(sample_client.id)

    assert [t.id for t in history] == [newer.id, older.id]


def test_history_unknown_client_raises(repo):
    use_case = GetTransactionHistoryUseCase(repo)

    with pytest.raises(ClientNotFoundError):
        use_case.execute("ghost")
