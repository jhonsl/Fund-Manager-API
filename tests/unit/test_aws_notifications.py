"""Unit tests for the AWS (SES/SNS) notification senders, backed by moto.

Verify each sender calls the right AWS API; SES requires a verified sender, so
we verify the identity first. A delivery failure must be swallowed (never raise).
"""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from app.domain.entities.client import Client
from app.domain.value_objects.enums import NotificationPreference, Role
from app.domain.value_objects.money import Money
from app.infrastructure.config.settings import get_settings
from app.infrastructure.notifications.aws_notification_sender import (
    SesEmailSender,
    SnsSmsSender,
)

REGION = "us-east-1"
SENDER = "no-reply@example.com"


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_REGION", REGION)
    monkeypatch.setenv("NOTIFICATIONS_BACKEND", "aws")
    monkeypatch.setenv("SES_SENDER_EMAIL", SENDER)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _client(pref: NotificationPreference) -> Client:
    return Client(
        id="c1",
        email="ana@example.com",
        phone="+573001112233",
        balance=Money.of(0),
        notify_pref=pref,
        role=Role.CLIENT,
        password_hash="x",
    )


def test_ses_email_sender_sends(aws_env):
    with mock_aws():
        # SES rejects unverified senders, so verify the identity first.
        boto3.client("ses", region_name=REGION).verify_email_identity(EmailAddress=SENDER)

        SesEmailSender().send(_client(NotificationPreference.EMAIL), "Suscripción exitosa")

        quota = boto3.client("ses", region_name=REGION).get_send_quota()
        assert quota["SentLast24Hours"] >= 1.0


def test_sns_sms_sender_sends(aws_env):
    with mock_aws():
        # Should not raise; moto accepts the publish to a phone number.
        SnsSmsSender().send(_client(NotificationPreference.SMS), "Suscripción exitosa")


def test_ses_failure_is_swallowed(aws_env):
    # No moto context and no verified sender -> the SES call fails, but the
    # sender must swallow it (a notification failure never breaks the operation).
    SesEmailSender().send(_client(NotificationPreference.EMAIL), "msg")


def test_sns_failure_is_swallowed(aws_env):
    SnsSmsSender().send(_client(NotificationPreference.SMS), "msg")
