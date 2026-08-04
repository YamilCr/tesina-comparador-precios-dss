"""Query object de compatibilidad para listar productos activos."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductListQuery:
    """Parámetros de paginación para listar productos activos."""

    limit: int = 100
    offset: int = 0

    def __post_init__(self) -> None:
        """Valida parámetros de paginación simples."""
        if self.limit <= 0:
            raise ValueError("Product list limit must be greater than 0.")
        if self.limit > 500:
            raise ValueError("Product list limit must be less than or equal to 500.")
        if self.offset < 0:
            raise ValueError("Product list offset must be greater than or equal to 0.")
