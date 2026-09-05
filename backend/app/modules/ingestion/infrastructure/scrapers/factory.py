"""Builds configured scraper adapters without leaking source selection to callers."""

from app.modules.ingestion.domain.entities import ScrapingSource
from app.modules.ingestion.domain.ports import ScraperPort

from .carrefour_scraper import CarrefourScraper
from .changomas_scraper import ChangoMasScraper
from .coope_scraper import CoopeScraper
from .jumbo_scraper import JumboScraper
from .la_anonima_scraper import LaAnonimaScraper
from .maxiconsumo_scraper import MaxiconsumoScraper


def create_scraper_for_source(
    source: ScrapingSource,
    *,
    queries: list[str],
    city: str,
    result_limit: int,
) -> ScraperPort:
    """Returns the HTTP scraper registered for an active source configuration."""
    if source.scraper_key == "carrefour":
        return CarrefourScraper(
            queries,
            city=city,
            base_url=source.base_url,
            result_limit=result_limit,
        )
    if source.scraper_key == "changomas":
        return ChangoMasScraper(
            queries,
            city=city,
            base_url=source.base_url,
            result_limit=result_limit,
        )
    if source.scraper_key == "jumbo":
        return JumboScraper(queries, city=city, base_url=source.base_url, result_limit=result_limit)
    if source.scraper_key == "coope":
        return CoopeScraper(queries, city=city, base_url=source.base_url, result_limit=result_limit)
    if source.scraper_key == "la_anonima":
        return LaAnonimaScraper(
            queries,
            city=city,
            base_url=source.base_url,
            result_limit=result_limit,
        )
    if source.scraper_key == "maxiconsumo":
        return MaxiconsumoScraper(
            queries,
            city=city,
            base_url=source.base_url,
            result_limit=result_limit,
        )
    raise ValueError("Playwright scraper sources require a configured browser adapter.")
