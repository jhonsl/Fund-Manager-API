"""Unit tests for LoginUseCase."""

from __future__ import annotations

import pytest

from app.application.exceptions import InvalidCredentialsError
from app.application.use_cases.login import LoginUseCase
from app.domain.entities.client import Client
from app.domain.value_objects.enums import NotificationPreference, Role
from app.domain.value_objects.money import Money
from tests.unit.conftest import FakeTokenService


def _register(repo, hasher, email="ana@example.com", password="secret123") -> Client:
    client = Client(
        id="client-1",
        email=email,
        phone="+57300",
        balance=Money.of(500_000),
        notify_pref=NotificationPreference.EMAIL,
        role=Role.CLIENT,
        password_hash=hasher.hash(password),
    )
    repo.save_client(client)
    return client


def test_login_success_returns_token(repo, hasher):
    _register(repo, hasher)
    use_case = LoginUseCase(repo, hasher, FakeTokenService())

    token = use_case.execute("ana@example.com", "secret123")

    assert token == "client-1:CLIENT"


def test_login_unknown_email_raises(repo, hasher):
    use_case = LoginUseCase(repo, hasher, FakeTokenService())
    with pytest.raises(InvalidCredentialsError):
        use_case.execute("ghost@example.com", "secret123")


def test_login_wrong_password_raises(repo, hasher):
    _register(repo, hasher)
    use_case = LoginUseCase(repo, hasher, FakeTokenService())
    with pytest.raises(InvalidCredentialsError):
        use_case.execute("ana@example.com", "wrong")
