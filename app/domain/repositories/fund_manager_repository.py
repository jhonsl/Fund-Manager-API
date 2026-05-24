"""Repository port for the fund-management aggregate.

A single cohesive interface: the store is single-table and the core operations
(subscribe, cancel) are atomic writes spanning client balance + subscription +
transaction. The ``*_atomically`` methods are the unit-of-work boundary — the
use case computes the new domain state and hands the entities here; how the
atomicity is achieved (e.g. DynamoDB TransactWriteItems) is an implementation
detail the domain does not know about.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.client import Client
from app.domain.entities.fund import Fund
from app.domain.entities.subscription import Subscription
from app.domain.entities.transaction import Transaction


class FundManagerRepository(ABC):
    """Persistence port for clients, funds, subscriptions and transactions."""

    @abstractmethod
    def get_client(self, client_id: str) -> Client | None:
        ...

    @abstractmethod
    def get_client_by_email(self, email: str) -> Client | None:
        """Look up a client by email (used for login)."""

    @abstractmethod
    def save_client(self, client: Client) -> None:
        """Persist a new client. Implementations must reject id collisions and
        duplicate emails (raising EmailAlreadyExistsError)."""

    @abstractmethod
    def list_funds(self) -> list[Fund]:
        ...

    @abstractmethod
    def get_fund(self, fund_id: str) -> Fund | None:
        ...

    @abstractmethod
    def get_subscription(self, client_id: str, fund_id: str) -> Subscription | None:
        ...

    @abstractmethod
    def get_idempotency_result(self, key: str) -> Client | None:
        """Return the client snapshot stored for a processed Idempotency-Key,
        or None if the key has not been seen."""

    @abstractmethod
    def subscribe_atomically(
        self,
        client: Client,
        subscription: Subscription,
        transaction: Transaction,
        idempotency_key: str | None = None,
    ) -> Client:
        """Atomically: persist the debited client balance, create the
        subscription, and record the OPEN transaction. All-or-nothing.

        When ``idempotency_key`` is provided, an idempotency record is written in
        the same transaction; a duplicate key raises ``IdempotentReplay`` carrying
        the previously stored client. Returns the client on a fresh write."""

    @abstractmethod
    def cancel_atomically(
        self,
        client: Client,
        fund_id: str,
        transaction: Transaction,
        idempotency_key: str | None = None,
    ) -> Client:
        """Atomically: persist the credited client balance, delete the
        subscription, and record the CANCEL transaction. All-or-nothing.

        ``idempotency_key`` behaves as in ``subscribe_atomically``."""

    @abstractmethod
    def list_transactions(self, client_id: str) -> list[Transaction]:
        """Return the client's transactions, newest first."""
