"""Domain exceptions package."""

from app.domain.exceptions.errors import (
    AlreadySubscribedError,
    ClientNotFoundError,
    DomainError,
    EmailAlreadyExistsError,
    FundNotFoundError,
    InsufficientBalanceError,
    NotSubscribedError,
)

__all__ = [
    "AlreadySubscribedError",
    "ClientNotFoundError",
    "DomainError",
    "EmailAlreadyExistsError",
    "FundNotFoundError",
    "InsufficientBalanceError",
    "NotSubscribedError",
]
