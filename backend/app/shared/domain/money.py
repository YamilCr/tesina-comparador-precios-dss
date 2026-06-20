"""Objeto de valor monetario reutilizable y libre de dependencias externas."""

from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.value_objects import ValueObject


@dataclass(frozen=True)
class Money(ValueObject):
    """Representa una cantidad monetaria sin incluir operaciones de negocio."""

    amount: Decimal
    currency: str
