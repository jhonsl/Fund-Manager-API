"""Unit tests for SubscribeToFundUseCase."""

from __future__ import annotations

import pytest

from app.application.dtos.commands import SubscribeCommand
from app.application.use_cases.subscribe_to_fund import SubscribeToFundUseCase
from app.domain.exceptions.errors import (
    AlreadySubscribedError,
    ClientNotFoundError,
    FundNotFoundError,
    InsufficientBalanceError,
)
from app.domain.value_objects.enums import TransactionType
from app.domain.value_objects.money import Money
from tests.unit.conftest import make_subscription


def _seed(repo, client, fund):
    repo.save_client(client)
    repo.funds[fund.id] = fund


def test_subscribe_success_debits_balance_and_records_open(
    repo, dispatcher, sample_client, sample_fund
):
    _seed(repo, sample_client, sample_fund)
    use_case = SubscribeToFundUseCase(repo, dispatcher)

    client = use_case.execute(SubscribeCommand(sample_client.id, sample_fund.id))

    assert client.balance == Money.of(450_000)  # 500k - 50k
    assert repo.get_subscription(sample_client.id, sample_fund.id) is not None
    assert len(repo.transactions) == 1
    assert repo.transactions[0].type is TransactionType.OPEN
    assert repo.transactions[0].amount == Money.of(50_000)


def test_subscribe_sends_notification_once(repo, dispatcher, sample_client, sample_fund):
    _seed(repo, sample_client, sample_fund)
    use_case = SubscribeToFundUseCase(repo, dispatcher)

    use_case.execute(SubscribeCommand(sample_client.id, sample_fund.id))

    assert len(dispatcher.sent) == 1
    notified_client, message = dispatcher.sent[0]
    assert notified_client.id == sample_client.id
    assert sample_fund.name in message


def test_subscribe_insufficient_balance_raises_exact_spanish_message(
    repo, dispatcher, sample_client, sample_fund
):
    sample_client.balance = Money.of(10_000)  # below the 50k minimum
    _seed(repo, sample_client, sample_fund)
    use_case = SubscribeToFundUseCase(repo, dispatcher)

    with pytest.raises(InsufficientBalanceError) as exc:
        use_case.execute(SubscribeCommand(sample_client.id, sample_fund.id))

    assert (
        exc.value.message
        == "No tiene saldo disponible para vincularse al fondo DEUDAPRIVADA"
    )
    # No state change and no notification on failure.
    assert repo.get_subscription(sample_client.id, sample_fund.id) is None
    assert dispatcher.sent == []


def test_subscribe_twice_raises_already_subscribed(
    repo, dispatcher, sample_client, sample_fund
):
    _seed(repo, sample_client, sample_fund)
    repo.subscriptions[(sample_client.id, sample_fund.id)] = make_subscription(
        sample_client.id, sample_fund
    )
    use_case = SubscribeToFundUseCase(repo, dispatcher)

    with pytest.raises(AlreadySubscribedError):
        use_case.execute(SubscribeCommand(sample_client.id, sample_fund.id))


def test_subscribe_unknown_client_raises(repo, dispatcher, sample_fund):
    repo.funds[sample_fund.id] = sample_fund
    use_case = SubscribeToFundUseCase(repo, dispatcher)

    with pytest.raises(ClientNotFoundError):
        use_case.execute(SubscribeCommand("ghost", sample_fund.id))


def test_subscribe_unknown_fund_raises(repo, dispatcher, sample_client):
    repo.save_client(sample_client)
    use_case = SubscribeToFundUseCase(repo, dispatcher)

    with pytest.raises(FundNotFoundError):
        use_case.execute(SubscribeCommand(sample_client.id, "999"))
