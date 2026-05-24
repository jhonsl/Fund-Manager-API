"""Subscribe a client to a fund (apertura).

Business rules enforced here:
- client and fund must exist;
- the client must not already hold a subscription to the fund;
- the balance must cover the fund's minimum amount, else the exact Spanish
  insufficient-balance error is raised.
The balance debit, the new subscription and the OPEN transaction are persisted
atomically by the repository. A notification is sent only after the commit.
"""

from __future__ import annotations

from app.application.dtos.commands import SubscribeCommand
from app.application.exceptions import IdempotentReplay
from app.application.services.notification_dispatcher import NotificationDispatcher
from app.application.use_cases._util import new_id, now_utc
from app.domain.entities.client import Client
from app.domain.entities.subscription import Subscription
from app.domain.entities.transaction import Transaction
from app.domain.exceptions.errors import (
    AlreadySubscribedError,
    ClientNotFoundError,
    FundNotFoundError,
    InsufficientBalanceError,
)
from app.domain.repositories.fund_manager_repository import FundManagerRepository
from app.domain.value_objects.enums import TransactionType


class SubscribeToFundUseCase:
    def __init__(
        self,
        repo: FundManagerRepository,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._repo = repo
        self._dispatcher = dispatcher

    def execute(self, command: SubscribeCommand) -> Client:
        # Fast replay path: a previously processed key returns the stored result
        # without re-checking, re-debiting or re-notifying.
        if command.idempotency_key is not None:
            replayed = self._repo.get_idempotency_result(command.idempotency_key)
            if replayed is not None:
                return replayed

        client = self._repo.get_client(command.client_id)
        if client is None:
            raise ClientNotFoundError(command.client_id)

        fund = self._repo.get_fund(command.fund_id)
        if fund is None:
            raise FundNotFoundError(command.fund_id)

        if self._repo.get_subscription(command.client_id, command.fund_id) is not None:
            raise AlreadySubscribedError(command.client_id, fund.name)

        if not client.balance.is_greater_than_or_equal(fund.min_amount):
            raise InsufficientBalanceError(fund.name)

        # Compute the new domain state; persistence is atomic in the repository.
        client.balance = client.balance.subtract(fund.min_amount)
        opened_at = now_utc()
        subscription = Subscription(
            client_id=client.id,
            fund_id=fund.id,
            amount=fund.min_amount,
            opened_at=opened_at,
        )
        transaction = Transaction(
            id=new_id(),
            client_id=client.id,
            type=TransactionType.OPEN,
            fund_id=fund.id,
            amount=fund.min_amount,
            created_at=opened_at,
        )
        try:
            self._repo.subscribe_atomically(
                client, subscription, transaction, command.idempotency_key
            )
        except IdempotentReplay as replay:
            # Concurrent duplicate committed first; return its result, no notify.
            return replay.client

        # Notification must never roll back a committed money operation.
        self._dispatcher.notify(
            client, f"Suscripción exitosa al fondo {fund.name}"
        )
        return client
