"""The DI provider picks SES/SNS senders for the "aws" backend, log otherwise."""

from __future__ import annotations

import pytest

from app.domain.value_objects.enums import NotificationPreference
from app.infrastructure.config.settings import get_settings
from app.infrastructure.notifications.aws_notification_sender import (
    SesEmailSender,
    SnsSmsSender,
)
from app.infrastructure.notifications.log_notification_sender import (
    EmailNotificationSender,
    SmsNotificationSender,
)
from app.presentation.api.dependencies.providers import get_dispatcher


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_log_backend_uses_log_senders(monkeypatch):
    monkeypatch.setenv("NOTIFICATIONS_BACKEND", "log")
    get_settings.cache_clear()
    senders = get_dispatcher()._senders
    assert isinstance(senders[NotificationPreference.EMAIL], EmailNotificationSender)
    assert isinstance(senders[NotificationPreference.SMS], SmsNotificationSender)


def test_aws_backend_uses_ses_sns_senders(monkeypatch):
    monkeypatch.setenv("NOTIFICATIONS_BACKEND", "aws")
    get_settings.cache_clear()
    senders = get_dispatcher()._senders
    assert isinstance(senders[NotificationPreference.EMAIL], SesEmailSender)
    assert isinstance(senders[NotificationPreference.SMS], SnsSmsSender)
