"""End-to-end authentication & authorization tests (real tokens, no override)."""

from __future__ import annotations

import boto3
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.infrastructure.config.settings import get_settings
from app.main import create_app


@pytest.fixture
def client(dynamodb_table) -> TestClient:
    return TestClient(create_app())


def _register(client: TestClient, email="ana@example.com", password="secret123") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "phone": "+573001112233",
            "notify_pref": "EMAIL",
            "password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login(client: TestClient, email="ana@example.com", password="secret123") -> str:
    resp = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_then_login_returns_token(client):
    _register(client)
    token = _login(client)
    assert token


def test_register_duplicate_email_conflicts(client):
    _register(client)
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ana@example.com",
            "phone": "+1",
            "notify_pref": "SMS",
            "password": "another123",
        },
    )
    assert resp.status_code == 409


def test_login_wrong_password_unauthorized(client):
    _register(client)
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "ana@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_protected_route_without_token_unauthorized(client):
    resp = client.get("/api/v1/funds")
    assert resp.status_code == 401


def test_protected_route_with_token_ok(client):
    _register(client)
    token = _login(client)
    resp = client.get("/api/v1/funds", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 5


def test_client_cannot_access_another_clients_data(client):
    body = _register(client)
    token = _login(client)
    # Same authenticated client trying to read someone else's transactions.
    resp = client.get(
        f"/api/v1/clients/{body['id']}-other/transactions", headers=_auth(token)
    )
    assert resp.status_code == 403


def test_admin_can_access_any_client(client, dynamodb_table):
    # Seed an ADMIN directly, then log in and access another (existing) client.
    from app.infrastructure.persistence.dynamodb.fund_manager_repository import (
        DynamoDbFundManagerRepository,
    )
    from scripts.seed_admin import seed_admin

    target = _register(client)  # a normal CLIENT
    seed_admin("admin@btg.com", "adminpass1", phone="+1")
    admin_token = _login(client, "admin@btg.com", "adminpass1")

    resp = client.get(
        f"/api/v1/clients/{target['id']}/transactions", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    # sanity: the admin really exists in the repo
    assert DynamoDbFundManagerRepository().get_client_by_email("admin@btg.com")


def test_password_is_hashed_in_storage(client, dynamodb_table):
    body = _register(client, password="plaintext-secret")
    # Read the raw profile item from the moto table.
    table = boto3.resource("dynamodb", region_name="us-east-1").Table("fund_manager")
    item = table.get_item(
        Key={"PK": f"CLIENT#{body['id']}", "SK": "PROFILE"}
    )["Item"]
    assert item["password_hash"] != "plaintext-secret"
    assert "plaintext-secret" not in item["password_hash"]


def test_token_contains_role_claim(client):
    _register(client)
    token = _login(client)
    settings = get_settings()
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert payload["role"] == "CLIENT"
    assert payload["sub"]
