"""Seed the fixed fund catalog into DynamoDB.

The 5 funds come from the shared domain catalog (single source of truth).
Idempotent — each fund is written only if its item does not already exist, so
re-running never duplicates or clobbers data.

Run from the repo root (after creating the table):

    python -m scripts.seed_funds
"""

from __future__ import annotations

from app.domain.fund_catalog import FUND_CATALOG
from app.infrastructure.persistence.dynamodb import mappers
from app.infrastructure.persistence.dynamodb.client import (
    get_dynamodb_client,
    get_table,
)


def seed_funds() -> None:
    table = get_table()
    client = get_dynamodb_client()
    created = 0

    for fund in FUND_CATALOG:
        try:
            table.put_item(
                Item=mappers.fund_to_item(fund),
                ConditionExpression="attribute_not_exists(PK)",
            )
            created += 1
            print(f"Seeded fund {fund.id}: {fund.name}")
        except client.exceptions.ConditionalCheckFailedException:
            print(f"Fund {fund.id} ({fund.name}) already exists — skipping.")

    print(f"Done. {created} new fund(s) seeded, {len(FUND_CATALOG) - created} already present.")


if __name__ == "__main__":
    seed_funds()
