"""List a client's transaction history (openings and cancellations)."""

from __future__ import annotations

from app.domain.entities.transaction import Transaction
from app.domain.exceptions.errors import ClientNotFoundError
from app.domain.repositories.fund_manager_repository import FundManagerRepository


class GetTransactionHistoryUseCase:
    def __init__(self, repo: FundManagerRepository) -> None:
        self._repo = repo

    def execute(self, client_id: str) -> list[Transaction]:
        if self._repo.get_client(client_id) is None:
            raise ClientNotFoundError(client_id)
        return self._repo.list_transactions(client_id)
