"""Contrato de escritura para los resultados del pipeline de ingesta."""

from abc import ABC, abstractmethod

from app.modules.catalog.domain.entities.product_source import ProductSource
from app.modules.prices.domain.entities.price import Price


class IngestionWriterPort(ABC):
    """Define cómo la ingesta guarda productos fuente y precios normalizados."""

    @abstractmethod
    async def save_product_sources(
        self,
        product_sources: list[ProductSource],
    ) -> list[ProductSource]:
        """Guarda productos fuente procesados por el pipeline de ingesta."""

    @abstractmethod
    async def save_prices(self, prices: list[Price]) -> list[Price]:
        """Guarda precios procesados por el pipeline de ingesta."""
