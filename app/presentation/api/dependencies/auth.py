"""Authentication & authorization FastAPI dependencies.

401/403 are transport concerns, so they are raised here as ``HTTPException``
(which also gives the correct ``WWW-Authenticate`` header for 401). Domain/
business errors remain ``DomainError`` handled elsewhere.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.application.exceptions import InvalidTokenError
from app.application.services.token_service import TokenService
from app.domain.entities.client import Client
from app.domain.repositories.fund_manager_repository import FundManagerRepository
from app.domain.value_objects.enums import Role
from app.presentation.api.dependencies.providers import (
    get_repository,
    get_token_service,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_client(
    token: Annotated[str, Depends(oauth2_scheme)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
    repo: Annotated[FundManagerRepository, Depends(get_repository)],
) -> Client:
    """Resolve the authenticated client from the Bearer token."""
    try:
        claims = token_service.decode_access_token(token)
    except InvalidTokenError:
        raise _UNAUTHORIZED from None
    client = repo.get_client(claims.sub)
    if client is None:
        raise _UNAUTHORIZED
    return client


def require_role(*roles: Role) -> Callable[[Client], Client]:
    """Dependency factory: allow only the given roles."""

    def checker(
        current: Annotated[Client, Depends(get_current_client)],
    ) -> Client:
        if current.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current

    return checker


def require_owner_or_admin(
    client_id: str,
    current: Annotated[Client, Depends(get_current_client)],
) -> Client:
    """Allow a client to act only on its own data; an ADMIN may act on anyone."""
    if current.role is not Role.ADMIN and current.id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own resources",
        )
    return current
