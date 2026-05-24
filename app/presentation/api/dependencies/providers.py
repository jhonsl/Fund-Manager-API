"""Composition root: build repositories, services and use cases for FastAPI DI.

These provider functions are the single place where concrete infrastructure is
wired into use cases. Tests override them with ``app.dependency_overrides`` to
inject fakes or a moto-backed repository.
"""

from __future__ import annotations

from app.application.services.notification_dispatcher import NotificationDispatcher
from app.application.services.password_hasher import PasswordHasher
from app.application.services.token_service import TokenService
from app.application.use_cases.cancel_subscription import CancelSubscriptionUseCase
from app.application.use_cases.create_client import CreateClientUseCase
from app.application.use_cases.get_transaction_history import (
    GetTransactionHistoryUseCase,
)
from app.application.use_cases.list_funds import ListFundsUseCase
from app.application.use_cases.login import LoginUseCase
from app.application.use_cases.subscribe_to_fund import SubscribeToFundUseCase
from app.domain.repositories.fund_manager_repository import FundManagerRepository
from app.infrastructure.notifications.dispatcher import LogNotificationDispatcher
from app.infrastructure.persistence.dynamodb.fund_manager_repository import (
    DynamoDbFundManagerRepository,
)
from app.infrastructure.security.bcrypt_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_service import JoseTokenService


def get_repository() -> FundManagerRepository:
    return DynamoDbFundManagerRepository()


def get_dispatcher() -> NotificationDispatcher:
    return LogNotificationDispatcher()


def get_password_hasher() -> PasswordHasher:
    return BcryptPasswordHasher()


def get_token_service() -> TokenService:
    return JoseTokenService()


def get_create_client_use_case() -> CreateClientUseCase:
    return CreateClientUseCase(get_repository(), get_password_hasher())


def get_login_use_case() -> LoginUseCase:
    return LoginUseCase(get_repository(), get_password_hasher(), get_token_service())


def get_list_funds_use_case() -> ListFundsUseCase:
    return ListFundsUseCase(get_repository())


def get_subscribe_use_case() -> SubscribeToFundUseCase:
    return SubscribeToFundUseCase(get_repository(), get_dispatcher())


def get_cancel_use_case() -> CancelSubscriptionUseCase:
    return CancelSubscriptionUseCase(get_repository())


def get_history_use_case() -> GetTransactionHistoryUseCase:
    return GetTransactionHistoryUseCase(get_repository())
