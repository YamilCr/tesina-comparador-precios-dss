"""Entidad de dominio no persistida para un resultado de ranking."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class RankingResult:
    """Representa una alternativa ordenada por su puntaje multicriterio."""

    position: int
    branch_id: UUID
    supermarket_name: str
    branch_name: str
    total_cost: Decimal
    distance_km: Decimal
    saving: Decimal
    score: Decimal
    missing_products_count: int = 0

    def __post_init__(self) -> None:
        """Valida la posición y el rango del puntaje del resultado."""
        if self.position <= 0:
            raise ValueError("Ranking result position must be greater than 0.")
        if not Decimal("0") <= self.score <= Decimal("1"):
            raise ValueError("Ranking result score must be between 0 and 1.")
