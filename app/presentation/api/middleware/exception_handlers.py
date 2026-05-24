"""Maps domain exceptions to HTTP responses.

Keeps the use cases / domain free of HTTP concerns: they raise ``DomainError``
subclasses, and these handlers translate each into a status code + JSON body.
A catch-all handler turns any unexpected error into a clean 500 without leaking
internal details to the client (the stack trace is logged server-side instead).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.application.exceptions import IdempotencyConflictError, InvalidCredentialsError
from app.domain.exceptions.errors import (
    AlreadySubscribedError,
    ClientNotFoundError,
    DomainError,
    EmailAlreadyExistsError,
    FundNotFoundError,
    InsufficientBalanceError,
    NotSubscribedError,
)

logger = logging.getLogger("app.errors")

# Each domain error maps to a status code; default is 400.
_STATUS_MAP: dict[type[DomainError], int] = {
    ClientNotFoundError: status.HTTP_404_NOT_FOUND,
    FundNotFoundError: status.HTTP_404_NOT_FOUND,
    InsufficientBalanceError: status.HTTP_409_CONFLICT,
    AlreadySubscribedError: status.HTTP_409_CONFLICT,
    NotSubscribedError: status.HTTP_409_CONFLICT,
    IdempotencyConflictError: status.HTTP_409_CONFLICT,
    EmailAlreadyExistsError: status.HTTP_409_CONFLICT,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        code = _STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=code, content={"detail": exc.message})

    @app.exception_handler(InvalidCredentialsError)
    async def handle_invalid_credentials(
        _: Request, exc: InvalidCredentialsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid email or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Log the full detail for diagnosis; never expose internals to the client.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
