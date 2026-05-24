"""Fund endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.use_cases.list_funds import ListFundsUseCase
from app.domain.entities.client import Client
from app.presentation.api.dependencies.auth import get_current_client
from app.presentation.api.dependencies.providers import get_list_funds_use_case
from app.presentation.api.v1.schemas.fund import FundResponse

router = APIRouter(prefix="/funds", tags=["funds"])


@router.get("", response_model=list[FundResponse])
def list_funds(
    _: Annotated[Client, Depends(get_current_client)],
    use_case: Annotated[ListFundsUseCase, Depends(get_list_funds_use_case)],
) -> list[FundResponse]:
    funds = use_case.execute()
    return [FundResponse.model_validate(f) for f in funds]
