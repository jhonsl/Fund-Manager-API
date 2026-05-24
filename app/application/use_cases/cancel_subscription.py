"""Cancel a client's subscription to a fund.

The subscription amount is returned to the client's balance. The credit, the
subscription deletion and the CANCEL transaction are persisted atomically.
"""

from __future__ import annotations

from app.application.dtos.commands import CancelCommand
from app.application.exceptions import IdempotentReplay
from app.application.use_cases._util import new_id, now_utc
from app.domain.entities.client import Client
from app.domain.entities.transaction import Transaction
from app.domain.exceptions.errors import ClientNotFoundError, NotSubscribedError
from app.domain.repositories.fund_manager_repository import FundManagerRepository
from app.domain.value_objects.enums import TransactionType


class CancelSubscriptionUseCase:
    def __init__(self, repo: FundManagerRepository) -> None:
        self._repo = repo

    def execute(self, command: CancelCommand) -> Client:
        if command.idempotency_key is not None:
            replayed = self._repo.get_idempotency_result(command.idempotency_key)
            if replayed is not None:
                return replayed

        client = self._repo.get_client(command.client_id)
        if client is None:
            raise ClientNotFoundError(command.client_id)

        subscription = self._repo.get_subscription(command.client_id, command.fund_id)
        if subscription is None:
            raise NotSubscribedError(command.client_id, command.fund_id)

        client.balance = client.balance.add(subscription.amount)
        transaction = Transaction(
            id=new_id(),
            client_id=client.id,
            type=TransactionType.CANCEL,
            fund_id=command.fund_id,
            amount=subscription.amount,
            created_at=now_utc(),
        )
        try:
            self._repo.cancel_atomically(
                client, command.fund_id, transaction, command.idempotency_key
            )
        except IdempotentReplay as replay:
            return replay.client
        return client
