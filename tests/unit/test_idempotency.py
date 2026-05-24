"""Unit tests for Idempotency-Key behavior in the use cases (fake repo)."""

from __future__ import annotations

from app.application.dtos.commands import CancelCommand, SubscribeCommand
from app.application.use_cases.cancel_subscription import CancelSubscriptionUseCase
from app.application.use_cases.subscribe_to_fund import SubscribeToFundUseCase
from app.domain.value_objects.enums import TransactionType
from app.domain.value_objects.money import Money
from tests.unit.conftest import make_subscription


def _seed(repo, client, fund):
    repo.save_client(client)
    repo.funds[fund.id] = fund


def test_subscribe_same_key_twice_processes_once(
    repo, dispatcher, sample_client, sample_fund
):
    _seed(repo, sample_client, sample_fund)
    use_case = SubscribeToFundUseCase(repo, dispatcher)
    cmd = SubscribeCommand(sample_client.id, sample_fund.id, idempotency_key="k1")

    first = use_case.execute(cmd)
    second = use_case.execute(cmd)

    # Same result, debited once, single transaction, single notification.
    assert first.balance == Money.of(450_000)
    assert second.balance == Money.of(450_000)
    assert len([t for t in repo.transactions if t.type is TransactionType.OPEN]) == 1
    assert len(dispatcher.sent) == 1


def test_subscribe_different_keys_independent(
    repo, dispatcher, sample_client, sample_fund
):
    _seed(repo, sample_client, sample_fund)
    # A second fund so the two subscriptions are independent.
    from app.domain.entities.fund import Fund
    from app.domain.value_objects.enums import FundCategory

    other = Fund("5", "FPV_BTG_PACTUAL_DINAMICA", Money.of(100_000), FundCategory.FIC)
    repo.funds[other.id] = other
    use_case = SubscribeToFundUseCase(repo, dispatcher)

    use_case.execute(SubscribeCommand(sample_client.id, sample_fund.id, idempotency_key="ka"))
    use_case.execute(SubscribeCommand(sample_client.id, other.id, idempotency_key="kb"))

    # 500k - 50k - 100k = 350k; two OPEN transactions.
    assert repo.get_client(sample_client.id).balance == Money.of(350_000)
    assert len([t for t in repo.transactions if t.type is TransactionType.OPEN]) == 2


def test_cancel_same_key_twice_processes_once(repo, sample_client, sample_fund):
    sample_client.balance = Money.of(450_000)
    repo.save_client(sample_client)
    repo.subscriptions[(sample_client.id, sample_fund.id)] = make_subscription(
        sample_client.id, sample_fund
    )
    use_case = CancelSubscriptionUseCase(repo)
    cmd = CancelCommand(sample_client.id, sample_fund.id, idempotency_key="kc")

    first = use_case.execute(cmd)
    second = use_case.execute(cmd)

    assert first.balance == Money.of(500_000)
    assert second.balance == Money.of(500_000)
    assert len([t for t in repo.transactions if t.type is TransactionType.CANCEL]) == 1
