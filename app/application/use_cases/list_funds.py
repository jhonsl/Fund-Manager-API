"""List the available funds."""

from __future__ import annotations

from app.domain.entities.fund import Fund
from app.domain.repositories.fund_manager_repository import FundManagerRepository


class ListFundsUseCase:
    def __init__(self, repo: FundManagerRepository) -> None:
        self._repo = repo

    def execute(self) -> list[Fund]:
        return self._repo.list_funds()
