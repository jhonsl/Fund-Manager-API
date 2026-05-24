"""Create a new client with the initial balance defined by the challenge."""

from __future__ import annotations

from app.application.dtos.commands import CreateClientCommand
from app.application.services.password_hasher import PasswordHasher
from app.application.use_cases._util import new_id
from app.domain.entities.client import Client
from app.domain.repositories.fund_manager_repository import FundManagerRepository
from app.domain.value_objects.enums import Role
from app.domain.value_objects.money import Money

INITIAL_BALANCE = Money.of(500_000)  # COP $500.000 (business rule)


class CreateClientUseCase:
    """Public registration: always creates a CLIENT with the initial balance."""

    def __init__(self, repo: FundManagerRepository, hasher: PasswordHasher) -> None:
        self._repo = repo
        self._hasher = hasher

    def execute(self, command: CreateClientCommand) -> Client:
        client = Client(
            id=new_id(),
            email=command.email,
            phone=command.phone,
            balance=INITIAL_BALANCE,
            notify_pref=command.notify_pref,
            role=Role.CLIENT,
            password_hash=self._hasher.hash(command.password),
        )
        self._repo.save_client(client)
        return client
