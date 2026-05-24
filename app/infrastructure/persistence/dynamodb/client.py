"""DynamoDB connection helpers.

Single source of truth for building boto3 clients/resources from application
settings. Repositories and operational scripts obtain their table handle here so
connection configuration lives in exactly one place.

- Local (``dynamodb_endpoint_url`` set): point boto3 at DynamoDB Local and pass
  dummy credentials so it does not search the AWS credential chain.
- Real AWS (``dynamodb_endpoint_url`` is None): pass only the region and let the
  default credential chain / IAM role resolve credentials.
"""

from __future__ import annotations

from typing import Any

import boto3

from app.infrastructure.config.settings import get_settings


def _boto3_kwargs() -> dict[str, Any]:
    """Build common kwargs for boto3 dynamodb client/resource from settings."""
    settings = get_settings()
    kwargs: dict[str, Any] = {"region_name": settings.aws_region}

    if settings.dynamodb_endpoint_url:
        # DynamoDB Local: explicit endpoint + dummy creds (never hits real AWS).
        kwargs["endpoint_url"] = settings.dynamodb_endpoint_url
        kwargs["aws_access_key_id"] = "local"
        kwargs["aws_secret_access_key"] = "local"

    return kwargs


def get_dynamodb_resource() -> Any:
    """Return a boto3 DynamoDB *resource* (high-level Table interface)."""
    return boto3.resource("dynamodb", **_boto3_kwargs())


def get_dynamodb_client() -> Any:
    """Return a boto3 DynamoDB *client* (low-level API, e.g. for create_table)."""
    return boto3.client("dynamodb", **_boto3_kwargs())


def get_table() -> Any:
    """Return the configured single table as a boto3 Table resource."""
    settings = get_settings()
    return get_dynamodb_resource().Table(settings.dynamodb_table_name)
