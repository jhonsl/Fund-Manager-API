"""DynamoDB implementation of the FundManagerRepository port.

Reads use the high-level Table resource. The atomic subscribe/cancel operations
use the low-level client's ``transact_write_items`` (TransactWriteItems), which
the Table resource does not expose, with ConditionExpressions enforcing the
business invariants at write time.
"""

from __future__ import annotations

from typing import Any

from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer

from app.application.exceptions import IdempotencyConflictError, IdempotentReplay
from app.application.use_cases._util import now_utc
from app.domain.entities.client import Client
from app.domain.entities.fund import Fund
from app.domain.entities.subscription import Subscription
from app.domain.entities.transaction import Transaction
from app.domain.exceptions.errors import (
    AlreadySubscribedError,
    EmailAlreadyExistsError,
    NotSubscribedError,
)
from app.domain.repositories.fund_manager_repository import FundManagerRepository
from app.domain.value_objects.money import Money
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.dynamodb import mappers
from app.infrastructure.persistence.dynamodb.client import (
    get_dynamodb_client,
    get_dynamodb_resource,
)

_serializer = TypeSerializer()

# How long an idempotency record lives before DynamoDB TTL expires it.
TTL_SECONDS = 24 * 3600

# Operation labels stored on the idempotency record.
_OP_SUBSCRIBE = "SUBSCRIBE"
_OP_CANCEL = "CANCEL"


def _serialize(item: dict[str, Any]) -> dict[str, Any]:
    """Convert a plain item dict to the low-level TransactWriteItems format."""
    return {k: _serializer.serialize(v) for k, v in item.items()}


class DynamoDbFundManagerRepository(FundManagerRepository):
    def __init__(self) -> None:
        settings = get_settings()
        self._table_name = settings.dynamodb_table_name
        self._table = get_dynamodb_resource().Table(self._table_name)
        self._client = get_dynamodb_client()

    # --- Reads ------------------------------------------------------------

    def get_client(self, client_id: str) -> Client | None:
        resp = self._table.get_item(
            Key={"PK": mappers.client_pk(client_id), "SK": mappers.SK_PROFILE}
        )
        item = resp.get("Item")
        return mappers.item_to_client(item) if item else None

    def get_client_by_email(self, email: str) -> Client | None:
        resp = self._table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(mappers.email_key(email)),
        )
        items = resp.get("Items", [])
        return mappers.item_to_client(items[0]) if items else None

    def list_funds(self) -> list[Fund]:
        resp = self._table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(mappers.GSI1PK_FUND),
        )
        return [mappers.item_to_fund(i) for i in resp.get("Items", [])]

    def get_fund(self, fund_id: str) -> Fund | None:
        resp = self._table.get_item(
            Key={"PK": mappers.fund_pk(fund_id), "SK": mappers.SK_METADATA}
        )
        item = resp.get("Item")
        return mappers.item_to_fund(item) if item else None

    def get_subscription(self, client_id: str, fund_id: str) -> Subscription | None:
        resp = self._table.get_item(
            Key={
                "PK": mappers.client_pk(client_id),
                "SK": mappers.subscription_sk(fund_id),
            }
        )
        item = resp.get("Item")
        return mappers.item_to_subscription(item) if item else None

    def list_transactions(self, client_id: str) -> list[Transaction]:
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(mappers.client_pk(client_id))
            & Key("SK").begins_with(mappers.TXN_PREFIX),
            ScanIndexForward=False,  # newest first
        )
        return [mappers.item_to_transaction(i) for i in resp.get("Items", [])]

    def get_idempotency_result(self, key: str) -> Client | None:
        resp = self._table.get_item(
            Key={"PK": mappers.idempotency_pk(key), "SK": mappers.SK_IDEMPOTENCY}
        )
        item = resp.get("Item")
        return self._rebuild_client_from_idempotency(item) if item else None

    def _rebuild_client_from_idempotency(self, item: dict[str, Any]) -> Client | None:
        """Rebuild the post-operation client snapshot: fetch the current client
        and override its balance with the stored result balance."""
        record = mappers.item_to_idempotency_result(item)
        client = self.get_client(record["client_id"])
        if client is None:
            return None
        client.balance = Money.of(record["result_balance"])
        return client

    # --- Writes -----------------------------------------------------------

    def save_client(self, client: Client) -> None:
        # Two writes in one transaction: the profile (guarded against id reuse)
        # and an email-uniqueness item (guarded so two clients can't share an
        # email). Either both commit or neither does.
        try:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": _serialize(mappers.client_to_item(client)),
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": _serialize(
                                mappers.email_unique_item(client.email, client.id)
                            ),
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                ]
            )
        except self._client.exceptions.TransactionCanceledException as exc:
            # Index 1 is the email-uniqueness item; its failure means the email
            # is taken (the profile id is a fresh uuid, so index 0 won't clash).
            raise EmailAlreadyExistsError(client.email) from exc

    def _idempotency_transact_item(
        self, key: str, operation: str, client: Client, fund_id: str
    ) -> dict[str, Any]:
        """Build the idempotency-record Put: written in the same transaction so a
        duplicate key cannot commit twice (attribute_not_exists guard)."""
        ttl_epoch = int(now_utc().timestamp()) + TTL_SECONDS
        return {
            "Put": {
                "TableName": self._table_name,
                "Item": _serialize(
                    mappers.idempotency_to_item(key, operation, client, fund_id, ttl_epoch)
                ),
                "ConditionExpression": "attribute_not_exists(PK)",
            }
        }

    def _replay_or_conflict(
        self, key: str, operation: str, fund_id: str
    ) -> IdempotentReplay:
        """A duplicate idempotency key was hit. Fetch the stored record; replay it
        if it matches the same operation+fund, else flag a conflict."""
        resp = self._table.get_item(
            Key={"PK": mappers.idempotency_pk(key), "SK": mappers.SK_IDEMPOTENCY}
        )
        item = resp.get("Item")
        if item is None:  # pragma: no cover - record vanished between calls
            raise IdempotencyConflictError(key)
        record = mappers.item_to_idempotency_result(item)
        if record["operation"] != operation or record["fund_id"] != fund_id:
            raise IdempotencyConflictError(key)
        client = self._rebuild_client_from_idempotency(item)
        if client is None:  # pragma: no cover - client vanished
            raise IdempotencyConflictError(key)
        return IdempotentReplay(client)

    def subscribe_atomically(
        self,
        client: Client,
        subscription: Subscription,
        transaction: Transaction,
        idempotency_key: str | None = None,
    ) -> Client:
        client_item = mappers.client_to_item(client)
        transact_items: list[dict[str, Any]] = []
        if idempotency_key is not None:
            transact_items.append(
                self._idempotency_transact_item(
                    idempotency_key, _OP_SUBSCRIBE, client, subscription.fund_id
                )
            )
        transact_items += [
            {
                "Update": {
                    "TableName": self._table_name,
                    "Key": _serialize(
                        {"PK": client_item["PK"], "SK": mappers.SK_PROFILE}
                    ),
                    "UpdateExpression": "SET balance = :new_balance",
                    "ConditionExpression": "attribute_exists(PK) AND balance >= :amount",
                    "ExpressionAttributeValues": _serialize(
                        {
                            ":new_balance": client.balance.amount,
                            ":amount": subscription.amount.amount,
                        }
                    ),
                }
            },
            {
                "Put": {
                    "TableName": self._table_name,
                    "Item": _serialize(mappers.subscription_to_item(subscription)),
                    "ConditionExpression": "attribute_not_exists(SK)",
                }
            },
            {
                "Put": {
                    "TableName": self._table_name,
                    "Item": _serialize(mappers.transaction_to_item(transaction)),
                }
            },
        ]
        try:
            self._client.transact_write_items(TransactItems=transact_items)
        except self._client.exceptions.TransactionCanceledException as exc:
            if self._idempotency_item_failed(exc, idempotency_key):
                raise self._replay_or_conflict(
                    idempotency_key, _OP_SUBSCRIBE, subscription.fund_id
                ) from exc
            # The use case pre-validates, so this is a race safety net.
            raise AlreadySubscribedError(client.id, subscription.fund_id) from exc
        return client

    def cancel_atomically(
        self,
        client: Client,
        fund_id: str,
        transaction: Transaction,
        idempotency_key: str | None = None,
    ) -> Client:
        client_item = mappers.client_to_item(client)
        transact_items: list[dict[str, Any]] = []
        if idempotency_key is not None:
            transact_items.append(
                self._idempotency_transact_item(
                    idempotency_key, _OP_CANCEL, client, fund_id
                )
            )
        transact_items += [
            {
                "Update": {
                    "TableName": self._table_name,
                    "Key": _serialize(
                        {"PK": client_item["PK"], "SK": mappers.SK_PROFILE}
                    ),
                    "UpdateExpression": "SET balance = :new_balance",
                    "ConditionExpression": "attribute_exists(PK)",
                    "ExpressionAttributeValues": _serialize(
                        {":new_balance": client.balance.amount}
                    ),
                }
            },
            {
                "Delete": {
                    "TableName": self._table_name,
                    "Key": _serialize(
                        {
                            "PK": client_item["PK"],
                            "SK": mappers.subscription_sk(fund_id),
                        }
                    ),
                    "ConditionExpression": "attribute_exists(SK)",
                }
            },
            {
                "Put": {
                    "TableName": self._table_name,
                    "Item": _serialize(mappers.transaction_to_item(transaction)),
                }
            },
        ]
        try:
            self._client.transact_write_items(TransactItems=transact_items)
        except self._client.exceptions.TransactionCanceledException as exc:
            if self._idempotency_item_failed(exc, idempotency_key):
                raise self._replay_or_conflict(
                    idempotency_key, _OP_CANCEL, fund_id
                ) from exc
            raise NotSubscribedError(client.id, fund_id) from exc
        return client

    @staticmethod
    def _idempotency_item_failed(exc: Any, idempotency_key: str | None) -> bool:
        """True if the failed transaction item was the idempotency record (index 0
        when a key is present), i.e. a duplicate request."""
        if idempotency_key is None:
            return False
        reasons = exc.response.get("CancellationReasons", [])
        return bool(reasons) and reasons[0].get("Code") == "ConditionalCheckFailed"
