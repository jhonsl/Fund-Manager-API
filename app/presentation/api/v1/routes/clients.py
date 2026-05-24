"""Client endpoints: subscriptions and transaction history.

All routes require authentication. A CLIENT may act only on their own
``client_id``; an ADMIN may act on any (enforced by ``require_owner_or_admin``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.dtos.commands import CancelCommand, SubscribeCommand
from app.application.use_cases.cancel_subscription import CancelSubscriptionUseCase
from app.application.use_cases.get_transaction_history import (
    GetTransactionHistoryUseCase,
)
from app.application.use_cases.subscribe_to_fund import SubscribeToFundUseCase
from app.domain.entities.client import Client
from app.presentation.api.dependencies.auth import require_owner_or_admin
from app.presentation.api.dependencies.idempotency import idempotency_key
from app.presentation.api.dependencies.providers import (
    get_cancel_use_case,
    get_history_use_case,
    get_subscribe_use_case,
)
from app.presentation.api.v1.schemas.client import ClientResponse
from app.presentation.api.v1.schemas.transaction import TransactionResponse

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post(
    "/{client_id}/subscriptions/{fund_id}",
    response_model=ClientResponse,
    status_code=201,
)
def subscribe(
    client_id: str,
    fund_id: str,
    idem_key: Annotated[str | None, Depends(idempotency_key)],
    _: Annotated[Client, Depends(require_owner_or_admin)],
    use_case: Annotated[SubscribeToFundUseCase, Depends(get_subscribe_use_case)],
) -> ClientResponse:
    client = use_case.execute(
        SubscribeCommand(client_id=client_id, fund_id=fund_id, idempotency_key=idem_key)
    )
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}/subscriptions/{fund_id}", response_model=ClientResponse)
def cancel_subscription(
    client_id: str,
    fund_id: str,
    idem_key: Annotated[str | None, Depends(idempotency_key)],
    _: Annotated[Client, Depends(require_owner_or_admin)],
    use_case: Annotated[CancelSubscriptionUseCase, Depends(get_cancel_use_case)],
) -> ClientResponse:
    client = use_case.execute(
        CancelCommand(client_id=client_id, fund_id=fund_id, idempotency_key=idem_key)
    )
    return ClientResponse.model_validate(client)


@router.get("/{client_id}/transactions", response_model=list[TransactionResponse])
def get_transaction_history(
    client_id: str,
    _: Annotated[Client, Depends(require_owner_or_admin)],
    use_case: Annotated[GetTransactionHistoryUseCase, Depends(get_history_use_case)],
) -> list[TransactionResponse]:
    transactions = use_case.execute(client_id)
    return [TransactionResponse.model_validate(t) for t in transactions]
