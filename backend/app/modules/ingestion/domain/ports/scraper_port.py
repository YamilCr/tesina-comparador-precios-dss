"""Contrato común para futuros adaptadores de extracción de supermercados."""

from abc import ABC, abstractmethod


class ScraperPort(ABC):
    """Define la operación mínima que debe ofrecer un scraper externo."""

    @abstractmethod
    async def scrape(self) -> list[dict]:
        """Extrae datos crudos desde una fuente externa sin definir su tecnología."""
