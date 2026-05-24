"""Integration test fixtures: a moto-backed DynamoDB with table + seeded funds."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from app.domain.fund_catalog import FUND_CATALOG
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.dynamodb import mappers

TABLE_NAME = "fund_manager"


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mocked AWS env so boto3 (under moto) never touches real AWS or a local endpoint."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    # Force an empty endpoint so moto intercepts. An OS env var overrides the
    # value in .env (which points at DynamoDB Local); an empty string is falsy
    # in client.py, so no local endpoint is used.
    monkeypatch.setenv("DYNAMODB_ENDPOINT_URL", "")
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", TABLE_NAME)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create the single table + GSI1 and seed funds, inside a moto context."""
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
        client.update_time_to_live(
            TableName=TABLE_NAME,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
        )

        table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
        for fund in FUND_CATALOG:
            table.put_item(Item=mappers.fund_to_item(fund))
        yield table
