"""Round-trip tests for entity <-> DynamoDB item mappers."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.client import Client
from app.domain.entities.subscription import Subscription
from app.domain.entities.transaction import Transaction
from app.domain.value_objects.enums import (
    NotificationPreference,
    Role,
    TransactionType,
)
from app.domain.value_objects.money import Money
from app.infrastructure.persistence.dynamodb import mappers


def test_client_round_trip():
    client = Client(
        id="c1",
        email="ana@example.com",
        phone="+57300",
        balance=Money.of(500_000),
        notify_pref=NotificationPreference.SMS,
        role=Role.CLIENT,
        password_hash="hashed",
    )
    item = mappers.client_to_item(client)
    assert item["PK"] == "CLIENT#c1" and item["SK"] == "PROFILE"
    assert mappers.item_to_client(item) == client


def test_subscription_round_trip():
    sub = Subscription("c1", "3", Money.of(50_000), datetime(2026, 1, 1, tzinfo=UTC))
    item = mappers.subscription_to_item(sub)
    assert item["PK"] == "CLIENT#c1" and item["SK"] == "SUB#3"
    assert mappers.item_to_subscription(item) == sub


def test_transaction_round_trip_with_gsi():
    ts = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    txn = Transaction("t1", "c1", TransactionType.OPEN, "3", Money.of(50_000), ts)
    item = mappers.transaction_to_item(txn)
    assert item["PK"] == "CLIENT#c1"
    assert item["SK"].startswith("TXN#") and item["SK"].endswith("#t1")
    assert item["GSI1PK"] == "CLIENT#c1"
    assert item["GSI1SK"] == f"TXN#{ts.isoformat()}"
    assert mappers.item_to_transaction(item) == txn
