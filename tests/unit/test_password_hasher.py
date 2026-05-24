"""Unit tests for the real bcrypt password hasher."""

from __future__ import annotations

from app.infrastructure.security.bcrypt_hasher import BcryptPasswordHasher


def test_hash_differs_from_plain_and_verifies():
    hasher = BcryptPasswordHasher()
    hashed = hasher.hash("super-secret")

    assert hashed != "super-secret"
    assert hasher.verify("super-secret", hashed) is True


def test_verify_rejects_wrong_password():
    hasher = BcryptPasswordHasher()
    hashed = hasher.hash("super-secret")

    assert hasher.verify("wrong", hashed) is False


def test_verify_rejects_empty_hash():
    hasher = BcryptPasswordHasher()
    assert hasher.verify("anything", "") is False
