"""Integration tests for the DynamoDB repository (moto-backed)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.client import Client
from app.domain.entities.subscription import Subscription
from app.domain.entities.transaction import Transaction
from app.domain.exceptions.errors import AlreadySubscribedError, NotSubscribedError
from app.domain.value_objects.enums import (
    NotificationPreference,
    Role,
    TransactionType,
)
from app.domain.value_objects.money import Money
from app.infrastructure.persistence.dynamodb.fund_manager_repository import (
    DynamoDbFundManagerRepository,
)


def _client(balance: int = 500_000) -> Client:
    return Client(
        id="client-1",
        email="ana@example.com",
        phone="+573001112233",
        balance=Money.of(balance),
        notify_pref=NotificationPreference.EMAIL,
        role=Role.CLIENT,
        password_hash="",
    )


def _now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_save_and_get_client(dynamodb_table):
    repo = DynamoDbFundManagerRepository()
    client = _client()
    repo.save_client(client)

    loaded = repo.get_client(client.id)
    assert loaded is not None
    assert loaded.balance == Money.of(500_000)
    assert loaded.email == client.email


def test_list_funds_returns_five_via_gsi(dynamodb_table):
    repo = DynamoDbFundManagerRepository()
    funds = repo.list_funds()
    assert len(funds) == 5
    assert {f.name for f in funds} >= {"DEUDAPRIVADA", "FDO-ACCIONES"}


def test_subscribe_atomically_persists_all_three(dynamodb_table):
    repo = DynamoDbFundManagerRepository()
    client = _client()
    repo.save_client(client)
    fund = repo.get_fund("3")  # DEUDAPRIVADA, 50000

    client.balance = client.balance.subtract(fund.min_amount)
    sub = Subscription(client.id, fund.id, fund.min_amount, _now())
    txn = Transaction("txn-1", client.id, TransactionType.OPEN, fund.id, fund.min_amount, _now())
    repo.subscribe_atomically(client, sub, txn)

    assert repo.get_client(client.id).balance == Money.of(450_000)
    assert repo.get_subscription(client.id, fund.id) is not None
    history = repo.list_transactions(client.id)
    assert len(history) == 1 and history[0].type is TransactionType.OPEN


def test_subscribe_second_time_same_fund_raises(dynamodb_table):
    repo = DynamoDbFundManagerRepository()
    client = _client()
    repo.save_client(client)
    fund = repo.get_fund("3")

    client.balance = client.balance.subtract(fund.min_amount)
    sub = Subscription(client.id, fund.id, fund.min_amount, _now())
    txn = Transaction("txn-1", client.id, TransactionType.OPEN, fund.id, fund.min_amount, _now())
    repo.subscribe_atomically(client, sub, txn)

    # Second attempt: the subscription Put condition fails -> the whole tx cancels.
    txn2 = Transaction("txn-2", client.id, TransactionType.OPEN, fund.id, fund.min_amount, _now())
    with pytest.raises(AlreadySubscribedError):
        repo.subscribe_atomically(client, sub, txn2)


def test_cancel_atomically_credits_and_deletes(dynamodb_table):
    repo = DynamoDbFundManagerRepository()
    client = _client()
    repo.save_client(client)
    fund = repo.get_fund("3")

    client.balance = client.balance.subtract(fund.min_amount)
    sub = Subscription(client.id, fund.id, fund.min_amount, _now())
    txn = Transaction("txn-1", client.id, TransactionType.OPEN, fund.id, fund.min_amount, _now())
    repo.subscribe_atomically(client, sub, txn)

    # Now cancel.
    client.balance = client.balance.add(sub.amount)
    cancel_txn = Transaction(
        "txn-2", client.id, TransactionType.CANCEL, fund.id, sub.amount, _now()
    )
    repo.cancel_atomically(client, fund.id, cancel_txn)

    assert repo.get_client(client.id).balance == Money.of(500_000)
    assert repo.get_subscription(client.id, fund.id) is None
    history = repo.list_transactions(client.id)
    assert len(history) == 2


def test_cancel_when_not_subscribed_raises(dynamodb_table):
    repo = DynamoDbFundManagerRepository()
    client = _client()
    repo.save_client(client)

    cancel_txn = Transaction(
        "txn-x", client.id, TransactionType.CANCEL, "3", Money.of(50_000), _now()
    )
    with pytest.raises(NotSubscribedError):
        repo.cancel_atomically(client, "3", cancel_txn)
