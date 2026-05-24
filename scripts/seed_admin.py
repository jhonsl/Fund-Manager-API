"""Create an ADMIN client.

ADMINs are created out-of-band (never via public registration). Reads the
credentials from CLI args or the ADMIN_EMAIL / ADMIN_PASSWORD env vars.
Idempotent at the email level: a duplicate email is reported and skipped.

Run from the repo root (table must exist):

    python -m scripts.seed_admin --email admin@btg.com --password "<strong-pw>"
    # or: set ADMIN_EMAIL / ADMIN_PASSWORD and run with no args
"""

from __future__ import annotations

import argparse
import os

from app.application.use_cases._util import new_id
from app.domain.entities.client import Client
from app.domain.exceptions.errors import EmailAlreadyExistsError
from app.domain.value_objects.enums import NotificationPreference, Role
from app.domain.value_objects.money import Money
from app.infrastructure.persistence.dynamodb.fund_manager_repository import (
    DynamoDbFundManagerRepository,
)
from app.infrastructure.security.bcrypt_hasher import BcryptPasswordHasher


def seed_admin(email: str, password: str, phone: str = "") -> None:
    repo = DynamoDbFundManagerRepository()
    hasher = BcryptPasswordHasher()
    admin = Client(
        id=new_id(),
        email=email,
        phone=phone,
        balance=Money.of(0),  # an admin operates on others, not their own funds
        notify_pref=NotificationPreference.EMAIL,
        role=Role.ADMIN,
        password_hash=hasher.hash(password),
    )
    try:
        repo.save_client(admin)
        print(f"Admin '{email}' created.")
    except EmailAlreadyExistsError:
        print(f"Admin '{email}' already exists — skipping.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed an ADMIN client.")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"))
    parser.add_argument("--phone", default=os.getenv("ADMIN_PHONE", ""))
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if not args.email or not args.password:
        raise SystemExit(
            "Provide --email and --password (or ADMIN_EMAIL / ADMIN_PASSWORD env vars)."
        )
    seed_admin(args.email, args.password, args.phone)
