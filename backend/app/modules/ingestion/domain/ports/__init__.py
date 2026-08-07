"""Puertos para extracción externa y escritura de resultados de ingesta."""

from .ingestion_writer_port import IngestionWriterPort
from .ingestion_repository_port import IngestionRepositoryPort
from .scraper_port import ScraperPort

__all__ = ["IngestionRepositoryPort", "IngestionWriterPort", "ScraperPort"]
