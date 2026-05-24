"""Shared fakes for use-case unit tests (no AWS, no FastAPI)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest

from app.application.exceptions import IdempotentReplay
from app.application.services.notification_dispatcher import NotificationDispatcher
from app.application.services.password_hasher import PasswordHasher
from app.application.services.token_service import TokenClaims, TokenService
from app.domain.entities.client import Client
from app.domain.entities.fund import Fund
from app.domain.entities.subscription import Subscription
from app.domain.entities.transaction import Transaction
from app.domain.exceptions.errors import EmailAlreadyExistsError
from app.domain.repositories.fund_manager_repository import FundManagerRepository
from app.domain.value_objects.enums import FundCategory, NotificationPreference, Role
from app.domain.value_objects.money import Money


class FakeFundManagerRepository(FundManagerRepository):
    """In-memory repository for testing use cases."""

    def __init__(self) -> None:
        self.clients: dict[str, Client] = {}
        self.funds: dict[str, Fund] = {}
        self.subscriptions: dict[tuple[str, str], Subscription] = {}
        self.transactions: list[Transaction] = []
        # key -> snapshot client (post-operation state) for idempotent replay.
        self.idempotency: dict[str, Client] = {}

    def get_client(self, client_id: str) -> Client | None:
        return self.clients.get(client_id)

    def get_client_by_email(self, email: str) -> Client | None:
        for client in self.clients.values():
            if client.email.lower() == email.lower():
                return client
        return None

    def save_client(self, client: Client) -> None:
        if self.get_client_by_email(client.email) is not None:
            raise EmailAlreadyExistsError(client.email)
        self.clients[client.id] = client

    def list_funds(self) -> list[Fund]:
        return sorted(self.funds.values(), key=lambda f: f.id)

    def get_fund(self, fund_id: str) -> Fund | None:
        return self.funds.get(fund_id)

    def get_subscription(self, client_id: str, fund_id: str) -> Subscription | None:
        return self.subscriptions.get((client_id, fund_id))

    def get_idempotency_result(self, key: str) -> Client | None:
        stored = self.idempotency.get(key)
        return replace(stored) if stored is not None else None

    def subscribe_atomically(
        self,
        client: Client,
        subscription: Subscription,
        transaction: Transaction,
        idempotency_key: str | None = None,
    ) -> Client:
        if idempotency_key is not None and idempotency_key in self.idempotency:
            raise IdempotentReplay(self.get_idempotency_result(idempotency_key))
        self.clients[client.id] = client
        self.subscriptions[(client.id, subscription.fund_id)] = subscription
        self.transactions.append(transaction)
        if idempotency_key is not None:
            self.idempotency[idempotency_key] = replace(client)
        return client

    def cancel_atomically(
        self,
        client: Client,
        fund_id: str,
        transaction: Transaction,
        idempotency_key: str | None = None,
    ) -> Client:
        if idempotency_key is not None and idempotency_key in self.idempotency:
            raise IdempotentReplay(self.get_idempotency_result(idempotency_key))
        self.clients[client.id] = client
        self.subscriptions.pop((client.id, fund_id), None)
        self.transactions.append(transaction)
        if idempotency_key is not None:
            self.idempotency[idempotency_key] = replace(client)
        return client

    def list_transactions(self, client_id: str) -> list[Transaction]:
        items = [t for t in self.transactions if t.client_id == client_id]
        return sorted(items, key=lambda t: t.created_at, reverse=True)


class FakeDispatcher(NotificationDispatcher):
    """Records notifications instead of sending them."""

    def __init__(self) -> None:
        self.sent: list[tuple[Client, str]] = []

    def notify(self, client: Client, message: str) -> None:
        self.sent.append((client, message))


class FakePasswordHasher(PasswordHasher):
    """Deterministic, fast hasher for tests (no bcrypt cost)."""

    def hash(self, plain: str) -> str:
        return f"hashed::{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed::{plain}"


class FakeTokenService(TokenService):
    """Encodes/decodes a trivial token for tests."""

    def create_access_token(self, client_id: str, role: Role) -> str:
        return f"{client_id}:{role.value}"

    def decode_access_token(self, token: str) -> TokenClaims:
        sub, role = token.split(":", 1)
        return TokenClaims(sub=sub, role=Role(role))


@pytest.fixture
def repo() -> FakeFundManagerRepository:
    return FakeFundManagerRepository()


@pytest.fixture
def dispatcher() -> FakeDispatcher:
    return FakeDispatcher()


@pytest.fixture
def hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.fixture
def sample_client() -> Client:
    return Client(
        id="client-1",
        email="ana@example.com",
        phone="+573001112233",
        balance=Money.of(500_000),
        notify_pref=NotificationPreference.EMAIL,
        role=Role.CLIENT,
        password_hash="",
    )


@pytest.fixture
def sample_fund() -> Fund:
    return Fund(
        id="3",
        name="DEUDAPRIVADA",
        min_amount=Money.of(50_000),
        category=FundCategory.FIC,
    )


def make_subscription(client_id: str, fund: Fund) -> Subscription:
    return Subscription(
        client_id=client_id,
        fund_id=fund.id,
        amount=fund.min_amount,
        opened_at=datetime(2026, 1, 1),
    )


def decimal(value: int) -> Decimal:
    return Decimal(str(value))
