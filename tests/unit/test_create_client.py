"""Unit tests for CreateClientUseCase (registration)."""

from __future__ import annotations

from app.application.dtos.commands import CreateClientCommand
from app.application.use_cases.create_client import CreateClientUseCase
from app.domain.value_objects.enums import NotificationPreference, Role
from app.domain.value_objects.money import Money


def test_create_client_sets_initial_balance_role_and_hashes_password(repo, hasher):
    use_case = CreateClientUseCase(repo, hasher)
    command = CreateClientCommand(
        email="ana@example.com",
        phone="+573001112233",
        notify_pref=NotificationPreference.EMAIL,
        password="secret123",
    )

    client = use_case.execute(command)

    assert client.balance == Money.of(500_000)
    assert client.role is Role.CLIENT
    assert client.id  # uuid assigned
    # Password is hashed via the hasher (not stored as the raw plaintext field).
    assert client.password_hash == hasher.hash("secret123")
    assert client.password_hash != "secret123"
    assert repo.get_client(client.id) is client
