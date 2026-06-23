"""Puertos para extracción externa y escritura de resultados de ingesta."""

from .ingestion_writer_port import IngestionWriterPort
from .scraper_port import ScraperPort

__all__ = ["IngestionWriterPort", "ScraperPort"]
