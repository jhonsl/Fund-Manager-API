"""Authenticate a client and issue an access token."""

from __future__ import annotations

from app.application.exceptions import InvalidCredentialsError
from app.application.services.password_hasher import PasswordHasher
from app.application.services.token_service import TokenService
from app.domain.repositories.fund_manager_repository import FundManagerRepository


class LoginUseCase:
    def __init__(
        self,
        repo: FundManagerRepository,
        hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._repo = repo
        self._hasher = hasher
        self._token_service = token_service

    def execute(self, email: str, password: str) -> str:
        """Return an access token, or raise InvalidCredentialsError.

        The same error covers unknown-email and wrong-password to avoid
        revealing which emails are registered.
        """
        client = self._repo.get_client_by_email(email)
        if client is None or not self._hasher.verify(password, client.password_hash):
            raise InvalidCredentialsError()
        return self._token_service.create_access_token(client.id, client.role)
