"""Domain exceptions.

These represent business-rule violations, independent of HTTP or any framework.
The presentation layer maps them to status codes (see exception handlers).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ClientNotFoundError(DomainError):
    def __init__(self, client_id: str) -> None:
        super().__init__(f"Client '{client_id}' not found")
        self.client_id = client_id


class FundNotFoundError(DomainError):
    def __init__(self, fund_id: str) -> None:
        super().__init__(f"Fund '{fund_id}' not found")
        self.fund_id = fund_id


class InsufficientBalanceError(DomainError):
    """Raised when a client lacks the balance to subscribe to a fund.

    The message is the exact Spanish wording required by the challenge.
    """

    def __init__(self, fund_name: str) -> None:
        super().__init__(
            f"No tiene saldo disponible para vincularse al fondo {fund_name}"
        )
        self.fund_name = fund_name


class EmailAlreadyExistsError(DomainError):
    def __init__(self, email: str) -> None:
        super().__init__(f"A client with email '{email}' already exists")
        self.email = email


class AlreadySubscribedError(DomainError):
    def __init__(self, client_id: str, fund_name: str) -> None:
        super().__init__(
            f"Client '{client_id}' is already subscribed to fund {fund_name}"
        )
        self.client_id = client_id
        self.fund_name = fund_name


class NotSubscribedError(DomainError):
    def __init__(self, client_id: str, fund_id: str) -> None:
        super().__init__(
            f"Client '{client_id}' is not subscribed to fund '{fund_id}'"
        )
        self.client_id = client_id
        self.fund_id = fund_id
