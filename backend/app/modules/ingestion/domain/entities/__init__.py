"""Entidades de dominio para fuentes y corridas de ingesta."""

from .product_identity_review import ProductIdentityReview
from .scheduled_refresh_execution import ScheduledRefreshExecution
from .scraped_product import ScrapedProduct
from .scraping_run import ScrapingRun
from .scraping_schedule import ScrapingSchedule
from .scraping_source import ScrapingSource

__all__ = [
    "ProductIdentityReview",
    "ScheduledRefreshExecution",
    "ScrapedProduct",
    "ScrapingRun",
    "ScrapingSchedule",
    "ScrapingSource",
]
