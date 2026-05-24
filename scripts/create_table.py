"""Create the single DynamoDB table for the Fund Manager API.

Single-table design: generic ``PK``/``SK`` keys plus one GSI (``GSI1``) used for
transaction history and for listing funds. Idempotent — running it again when the
table already exists is a no-op.

Run from the repo root:

    python -m scripts.create_table
"""

from __future__ import annotations

from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.dynamodb.client import get_dynamodb_client


def create_table() -> None:
    settings = get_settings()
    client = get_dynamodb_client()
    table_name = settings.dynamodb_table_name

    try:
        client.create_table(
            TableName=table_name,
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
        client.get_waiter("table_exists").wait(TableName=table_name)
        print(f"Table '{table_name}' created (with GSI1).")
    except client.exceptions.ResourceInUseException:
        print(f"Table '{table_name}' already exists — skipping creation.")

    # Always ensure TTL is enabled (idempotent), even if the table pre-existed,
    # so idempotency records expire automatically via the `ttl` attribute.
    try:
        client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
        )
        print("TTL enabled on attribute 'ttl'.")
    except client.exceptions.ClientError:
        pass  # TTL already enabled — idempotent


if __name__ == "__main__":
    create_table()
