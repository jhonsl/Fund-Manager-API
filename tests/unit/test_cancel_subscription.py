"""Unit tests for CancelSubscriptionUseCase."""

from __future__ import annotations

import pytest

from app.application.dtos.commands import CancelCommand
from app.application.use_cases.cancel_subscription import CancelSubscriptionUseCase
from app.domain.exceptions.errors import ClientNotFoundError, NotSubscribedError
from app.domain.value_objects.enums import TransactionType
from app.domain.value_objects.money import Money
from tests.unit.conftest import make_subscription


def test_cancel_returns_amount_and_records_cancel(repo, sample_client, sample_fund):
    sample_client.balance = Money.of(450_000)  # already subscribed (50k debited)
    repo.save_client(sample_client)
    repo.subscriptions[(sample_client.id, sample_fund.id)] = make_subscription(
        sample_client.id, sample_fund
    )
    use_case = CancelSubscriptionUseCase(repo)

    client = use_case.execute(CancelCommand(sample_client.id, sample_fund.id))

    assert client.balance == Money.of(500_000)  # amount returned
    assert repo.get_subscription(sample_client.id, sample_fund.id) is None
    assert len(repo.transactions) == 1
    assert repo.transactions[0].type is TransactionType.CANCEL


def test_cancel_not_subscribed_raises(repo, sample_client, sample_fund):
    repo.save_client(sample_client)
    use_case = CancelSubscriptionUseCase(repo)

    with pytest.raises(NotSubscribedError):
        use_case.execute(CancelCommand(sample_client.id, sample_fund.id))


def test_cancel_unknown_client_raises(repo, sample_fund):
    use_case = CancelSubscriptionUseCase(repo)

    with pytest.raises(ClientNotFoundError):
        use_case.execute(CancelCommand("ghost", sample_fund.id))
