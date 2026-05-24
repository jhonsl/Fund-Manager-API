"""Mapping between domain entities and DynamoDB items.

The only place that knows the single-table key grammar and item shapes. Handles
Money<->Decimal and datetime<->ISO-8601 conversions so the domain stays clean.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.domain.entities.client import Client
from app.domain.entities.fund import Fund
from app.domain.entities.subscription import Subscription
from app.domain.entities.transaction import Transaction
from app.domain.value_objects.enums import (
    FundCategory,
    NotificationPreference,
    Role,
    TransactionType,
)
from app.domain.value_objects.money import Money

# --- Single-table key grammar (constants) --------------------------------

SK_PROFILE = "PROFILE"  # client profile item
SK_METADATA = "METADATA"  # fund metadata item
SK_IDEMPOTENCY = "IDEMPOTENCY"  # idempotency record item
GSI1PK_FUND = "FUND"  # GSI1 partition holding all funds
TXN_PREFIX = "TXN#"  # transaction sort-key prefix
IDEMPOTENCY_PREFIX = "IDEMPOTENCY#"  # idempotency partition-key prefix
EMAIL_PREFIX = "EMAIL#"  # email lookup/uniqueness partition-key prefix


def client_pk(client_id: str) -> str:
    return f"CLIENT#{client_id}"


def idempotency_pk(key: str) -> str:
    return f"{IDEMPOTENCY_PREFIX}{key}"


def email_key(email: str) -> str:
    """Partition value used both for the GSI1 email lookup and the uniqueness
    item. Lowercased so emails are treated case-insensitively."""
    return f"{EMAIL_PREFIX}{email.lower()}"


def fund_pk(fund_id: str) -> str:
    return f"FUND#{fund_id}"


def fund_gsi1sk(fund_id: str) -> str:
    return f"{GSI1PK_FUND}#{fund_id}"


def subscription_sk(fund_id: str) -> str:
    return f"SUB#{fund_id}"


def transaction_sk(iso_ts: str, txn_id: str) -> str:
    return f"{TXN_PREFIX}{iso_ts}#{txn_id}"


# --- Client ---------------------------------------------------------------


def client_to_item(client: Client) -> dict[str, Any]:
    return {
        "PK": client_pk(client.id),
        "SK": SK_PROFILE,
        # GSI1 indexes the profile by email so login can look it up by a Query.
        "GSI1PK": email_key(client.email),
        "GSI1SK": email_key(client.email),
        "id": client.id,
        "email": client.email,
        "phone": client.phone,
        "balance": client.balance.amount,
        "notify_pref": client.notify_pref.value,
        "role": client.role.value,
        "password_hash": client.password_hash,
    }


def email_unique_item(email: str, client_id: str) -> dict[str, Any]:
    """A guard item whose PK is the email; written with attribute_not_exists in
    the same transaction as the profile to enforce one client per email."""
    return {
        "PK": email_key(email),
        "SK": email_key(email),
        "client_id": client_id,
    }


def item_to_client(item: dict[str, Any]) -> Client:
    return Client(
        id=item["id"],
        email=item["email"],
        phone=item["phone"],
        balance=Money.of(item["balance"]),
        notify_pref=NotificationPreference(item["notify_pref"]),
        role=Role(item["role"]),
        password_hash=item["password_hash"],
    )


# --- Fund -----------------------------------------------------------------


def fund_to_item(fund: Fund) -> dict[str, Any]:
    return {
        "PK": fund_pk(fund.id),
        "SK": SK_METADATA,
        "id": fund.id,
        "name": fund.name,
        "min_amount": fund.min_amount.amount,
        "category": fund.category.value,
        # GSI1 lets us list all funds with a single Query (GSI1PK="FUND").
        "GSI1PK": GSI1PK_FUND,
        "GSI1SK": fund_gsi1sk(fund.id),
    }


def item_to_fund(item: dict[str, Any]) -> Fund:
    return Fund(
        id=item["id"],
        name=item["name"],
        min_amount=Money.of(item["min_amount"]),
        category=FundCategory(item["category"]),
    )


# --- Subscription ---------------------------------------------------------


def subscription_to_item(subscription: Subscription) -> dict[str, Any]:
    return {
        "PK": client_pk(subscription.client_id),
        "SK": subscription_sk(subscription.fund_id),
        "fund_id": subscription.fund_id,
        "amount": subscription.amount.amount,
        "opened_at": subscription.opened_at.isoformat(),
    }


def item_to_subscription(item: dict[str, Any]) -> Subscription:
    return Subscription(
        client_id=item["PK"].split("#", 1)[1],
        fund_id=item["fund_id"],
        amount=Money.of(item["amount"]),
        opened_at=datetime.fromisoformat(item["opened_at"]),
    )


# --- Transaction ----------------------------------------------------------


def transaction_to_item(transaction: Transaction) -> dict[str, Any]:
    iso_ts = transaction.created_at.isoformat()
    pk = client_pk(transaction.client_id)
    return {
        "PK": pk,
        "SK": transaction_sk(iso_ts, transaction.id),
        "GSI1PK": pk,
        "GSI1SK": f"{TXN_PREFIX}{iso_ts}",
        "id": transaction.id,
        "type": transaction.type.value,
        "fund_id": transaction.fund_id,
        "amount": transaction.amount.amount,
        "created_at": iso_ts,
    }


def item_to_transaction(item: dict[str, Any]) -> Transaction:
    return Transaction(
        id=item["id"],
        client_id=item["PK"].split("#", 1)[1],
        type=TransactionType(item["type"]),
        fund_id=item["fund_id"],
        amount=Money.of(item["amount"]),
        created_at=datetime.fromisoformat(item["created_at"]),
    )


def to_decimal(value: int) -> Decimal:
    """Helper for callers building numeric DynamoDB attributes."""
    return Decimal(str(value))


# --- Idempotency ----------------------------------------------------------


def idempotency_to_item(
    key: str,
    operation: str,
    client: Client,
    fund_id: str,
    ttl_epoch: int,
) -> dict[str, Any]:
    """Build the idempotency record. ``result_balance`` is the client's balance
    AFTER the operation, enough to replay the response (other client fields are
    immutable in these flows). ``ttl`` lets DynamoDB expire the record."""
    return {
        "PK": idempotency_pk(key),
        "SK": SK_IDEMPOTENCY,
        "key": key,
        "operation": operation,
        "client_id": client.id,
        "fund_id": fund_id,
        "result_balance": client.balance.amount,
        "created_at": datetime.now(UTC).isoformat(),
        "ttl": ttl_epoch,
    }


def item_to_idempotency_result(item: dict[str, Any]) -> dict[str, Any]:
    """Extract the stored idempotency data (operation/fund_id for the mismatch
    guard, result_balance to rebuild the client)."""
    return {
        "operation": item["operation"],
        "client_id": item["client_id"],
        "fund_id": item["fund_id"],
        "result_balance": item["result_balance"],
    }
