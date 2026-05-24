"""Password hashing port.

The application depends on this abstraction; the concrete bcrypt implementation
lives in infrastructure so the domain/application stay free of hashing libraries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain: str) -> str:
        ...

    @abstractmethod
    def verify(self, plain: str, hashed: str) -> bool:
        ...
