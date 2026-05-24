"""Domain enumerations.

All enums are ``StrEnum`` so their values serialize naturally (e.g. to JSON or
DynamoDB string attributes) and compare directly against stored strings.
"""

from enum import StrEnum


class FundCategory(StrEnum):
    """Investment fund category."""

    FPV = "FPV"  # Fondo de Pensiones Voluntarias
    FIC = "FIC"  # Fondo de Inversión Colectiva


class TransactionType(StrEnum):
    """Type of fund transaction recorded in the history."""

    OPEN = "OPEN"  # apertura / subscription
    CANCEL = "CANCEL"  # cancelación / unsubscription


class NotificationPreference(StrEnum):
    """How a client wants to be notified on subscription."""

    EMAIL = "EMAIL"
    SMS = "SMS"


class Role(StrEnum):
    """Authorization role for a client account."""

    CLIENT = "CLIENT"
    ADMIN = "ADMIN"
