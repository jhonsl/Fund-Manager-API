"""Bcrypt password hasher.

Uses the ``bcrypt`` library directly (passlib's bcrypt backend is broken against
bcrypt >= 4). bcrypt only considers the first 72 bytes of the input, so we hash
the UTF-8 bytes and let the library enforce that limit consistently.
"""

from __future__ import annotations

import bcrypt

from app.application.services.password_hasher import PasswordHasher

# bcrypt ignores bytes beyond 72; truncate explicitly so verify matches hash.
_MAX_BYTES = 72


def _encode(plain: str) -> bytes:
    return plain.encode("utf-8")[:_MAX_BYTES]


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return bcrypt.hashpw(_encode(plain), bcrypt.gensalt()).decode("utf-8")

    def verify(self, plain: str, hashed: str) -> bool:
        if not hashed:
            return False
        try:
            return bcrypt.checkpw(_encode(plain), hashed.encode("utf-8"))
        except ValueError:
            return False
