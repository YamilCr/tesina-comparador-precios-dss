"""Query object para buscar productos normalizados."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchProductsQuery:
    """Parámetros de búsqueda de productos."""

    query: str
    limit: int = 20

    def __post_init__(self) -> None:
        """Valida búsqueda no vacía y límite razonable."""
        normalized_query = self.query.strip()
        if not normalized_query:
            raise ValueError("Search products query cannot be empty.")
        if self.limit <= 0:
            raise ValueError("Search products limit must be greater than 0.")
        if self.limit > 100:
            raise ValueError("Search products limit must be less than or equal to 100.")
        object.__setattr__(self, "query", normalized_query)
