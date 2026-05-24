"""End-to-end API tests (FastAPI TestClient over a moto-backed DynamoDB).

These focus on the business endpoints. To avoid repeating login in every test,
``get_current_client`` is overridden to return whichever client was registered
(ownership checks still pass because the override returns that same client).
Real auth behavior (login, tokens, 401/403) is covered in test_auth.py.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.entities.client import Client
from app.domain.value_objects.enums import NotificationPreference, Role
from app.domain.value_objects.money import Money
from app.main import create_app
from app.presentation.api.dependencies.auth import get_current_client
from app.presentation.api.dependencies.providers import get_repository

# A generic authenticated principal used before any client is registered (e.g.
# for /funds which only needs *some* logged-in user).
_ANON = Client(
    id="anon",
    email="anon@example.com",
    phone="+0",
    balance=Money.of(0),
    notify_pref=NotificationPreference.EMAIL,
    role=Role.CLIENT,
    password_hash="x",
)


@pytest.fixture
def client(dynamodb_table) -> TestClient:
    # The app is created inside the moto context (dynamodb_table fixture), so the
    # repository built by the DI providers binds to the mocked table.
    app = create_app()

    # Auth bypass for business-endpoint tests: resolve the current client from
    # the repo by the id captured at registration; fall back to a generic
    # authenticated principal when no client has been registered yet.
    state: dict[str, str] = {}

    def _current_client():
        cid = state.get("client_id")
        if cid is None:
            return _ANON
        return get_repository().get_client(cid)

    app.dependency_overrides[get_current_client] = _current_client
    test_client = TestClient(app)
    test_client.state_holder = state  # type: ignore[attr-defined]
    return test_client


def _create_client(client: TestClient, notify_pref: str = "EMAIL") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ana@example.com",
            "phone": "+573001112233",
            "notify_pref": notify_pref,
            "password": "secret123",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # Make the overridden get_current_client resolve to this client.
    client.state_holder["client_id"] = body["id"]  # type: ignore[attr-defined]
    return body


def test_register_returns_initial_balance(client):
    body = _create_client(client)
    assert body["balance"] == 500000
    assert body["role"] == "CLIENT"
    assert body["id"]
    assert "password_hash" not in body  # never leak the hash


def test_list_funds_returns_five(client):
    resp = client.get("/api/v1/funds")
    assert resp.status_code == 200
    funds = resp.json()
    assert len(funds) == 5
    assert all(isinstance(f["min_amount"], int) for f in funds)


def test_subscribe_success_debits_balance(client):
    cid = _create_client(client)["id"]
    resp = client.post(f"/api/v1/clients/{cid}/subscriptions/3")  # DEUDAPRIVADA 50000
    assert resp.status_code == 201, resp.text
    assert resp.json()["balance"] == 450000


def test_subscribe_insufficient_balance_returns_exact_message(client):
    cid = _create_client(client)["id"]
    # Subscribe to fund 4 (250000) is fine, but drain first to force the failure:
    # subscribe 4 (250000) -> 250000 left; subscribe 2 (125000) -> 125000 left;
    # subscribe 5 (100000) -> 25000 left; now fund 1 (75000) must fail.
    for fid in ("4", "2", "5"):
        assert client.post(f"/api/v1/clients/{cid}/subscriptions/{fid}").status_code == 201
    resp = client.post(f"/api/v1/clients/{cid}/subscriptions/1")  # needs 75000, only 25000 left
    assert resp.status_code == 409
    assert resp.json() == {
        "detail": "No tiene saldo disponible para vincularse al fondo FPV_BTG_PACTUAL_RECAUDADORA"
    }


def test_subscribe_twice_conflicts(client):
    cid = _create_client(client)["id"]
    assert client.post(f"/api/v1/clients/{cid}/subscriptions/3").status_code == 201
    resp = client.post(f"/api/v1/clients/{cid}/subscriptions/3")
    assert resp.status_code == 409


def test_full_flow_history_and_cancel(client):
    cid = _create_client(client)["id"]
    client.post(f"/api/v1/clients/{cid}/subscriptions/3")

    # History shows the OPEN.
    hist = client.get(f"/api/v1/clients/{cid}/transactions").json()
    assert len(hist) == 1
    assert hist[0]["type"] == "OPEN"

    # Cancel returns the amount.
    cancel = client.delete(f"/api/v1/clients/{cid}/subscriptions/3")
    assert cancel.status_code == 200
    assert cancel.json()["balance"] == 500000

    # History now has CANCEL first (newest), then OPEN.
    hist2 = client.get(f"/api/v1/clients/{cid}/transactions").json()
    assert [t["type"] for t in hist2] == ["CANCEL", "OPEN"]


def test_cancel_when_not_subscribed_conflicts(client):
    cid = _create_client(client)["id"]
    resp = client.delete(f"/api/v1/clients/{cid}/subscriptions/3")
    assert resp.status_code == 409


def test_transaction_history_unknown_client_404(client):
    # An ADMIN may target any client_id, so we reach the use case (404) rather
    # than the ownership guard (403). Register a client, then promote the
    # override's principal to an ADMIN that requests a non-existent client.
    from app.domain.entities.client import Client
    from app.domain.value_objects.enums import NotificationPreference, Role
    from app.domain.value_objects.money import Money

    admin = Client(
        id="admin-1",
        email="admin@x.com",
        phone="+1",
        balance=Money.of(0),
        notify_pref=NotificationPreference.EMAIL,
        role=Role.ADMIN,
        password_hash="x",
    )
    client.app.dependency_overrides[get_current_client] = lambda: admin

    resp = client.get("/api/v1/clients/ghost/transactions")
    assert resp.status_code == 404


def test_unexpected_error_returns_clean_500(dynamodb_table):
    """An unexpected error yields a generic 500 without leaking internals."""
    from app.presentation.api.dependencies.providers import get_list_funds_use_case

    class Boom:
        def execute(self):
            raise RuntimeError("database exploded with secret connection string")

    app = create_app()
    app.dependency_overrides[get_list_funds_use_case] = lambda: Boom()
    # /funds is auth-protected; bypass auth so we reach the failing use case.
    app.dependency_overrides[get_current_client] = lambda: _ANON
    # Disable TestClient's re-raise so the registered handler runs (as in prod).
    test_client = TestClient(app, raise_server_exceptions=False)

    resp = test_client.get("/api/v1/funds")
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal server error"}
    # The internal message must NOT leak to the client.
    assert "secret connection string" not in resp.text


# --- Idempotency-Key ------------------------------------------------------


def test_subscribe_same_idempotency_key_processes_once(client):
    cid = _create_client(client)["id"]
    headers = {"Idempotency-Key": "k-subscribe-1"}

    first = client.post(f"/api/v1/clients/{cid}/subscriptions/3", headers=headers)
    second = client.post(f"/api/v1/clients/{cid}/subscriptions/3", headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    # Identical replayed body; balance debited only once.
    assert first.json() == second.json()
    assert first.json()["balance"] == 450000

    history = client.get(f"/api/v1/clients/{cid}/transactions").json()
    opens = [t for t in history if t["type"] == "OPEN"]
    assert len(opens) == 1


def test_cancel_same_idempotency_key_processes_once(client):
    cid = _create_client(client)["id"]
    client.post(f"/api/v1/clients/{cid}/subscriptions/3")
    headers = {"Idempotency-Key": "k-cancel-1"}

    first = client.delete(f"/api/v1/clients/{cid}/subscriptions/3", headers=headers)
    second = client.delete(f"/api/v1/clients/{cid}/subscriptions/3", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["balance"] == 500000

    history = client.get(f"/api/v1/clients/{cid}/transactions").json()
    cancels = [t for t in history if t["type"] == "CANCEL"]
    assert len(cancels) == 1


def test_different_idempotency_keys_are_independent(client):
    cid = _create_client(client)["id"]
    r1 = client.post(
        f"/api/v1/clients/{cid}/subscriptions/3", headers={"Idempotency-Key": "ka"}
    )
    r2 = client.post(
        f"/api/v1/clients/{cid}/subscriptions/5", headers={"Idempotency-Key": "kb"}
    )
    assert r1.status_code == 201 and r2.status_code == 201
    # 500k - 50k(fund3) - 100k(fund5) = 350k
    assert r2.json()["balance"] == 350000


def test_no_idempotency_key_still_conflicts_on_real_duplicate(client):
    cid = _create_client(client)["id"]
    assert client.post(f"/api/v1/clients/{cid}/subscriptions/3").status_code == 201
    # Without a key, a genuine second subscribe is a 409 conflict (unchanged).
    assert client.post(f"/api/v1/clients/{cid}/subscriptions/3").status_code == 409


def test_invalid_idempotency_key_rejected(client):
    cid = _create_client(client)["id"]
    resp = client.post(
        f"/api/v1/clients/{cid}/subscriptions/3", headers={"Idempotency-Key": "   "}
    )
    assert resp.status_code == 400
