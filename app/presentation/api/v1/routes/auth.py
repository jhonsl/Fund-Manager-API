"""Authentication endpoints: register and login."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.application.dtos.commands import CreateClientCommand
from app.application.use_cases.create_client import CreateClientUseCase
from app.application.use_cases.login import LoginUseCase
from app.presentation.api.dependencies.providers import (
    get_create_client_use_case,
    get_login_use_case,
)
from app.presentation.api.v1.schemas.auth import RegisterRequest, TokenResponse
from app.presentation.api.v1.schemas.client import ClientResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=ClientResponse, status_code=status.HTTP_201_CREATED
)
def register(
    body: RegisterRequest,
    use_case: Annotated[CreateClientUseCase, Depends(get_create_client_use_case)],
) -> ClientResponse:
    """Public registration. Always creates a CLIENT with the initial balance."""
    client = use_case.execute(
        CreateClientCommand(
            email=body.email,
            phone=body.phone,
            notify_pref=body.notify_pref,
            password=body.password,
        )
    )
    return ClientResponse.model_validate(client)


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    use_case: Annotated[LoginUseCase, Depends(get_login_use_case)],
) -> TokenResponse:
    """Exchange email (username) + password for a JWT access token."""
    token = use_case.execute(form.username, form.password)
    return TokenResponse(access_token=token)
