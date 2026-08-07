"""Manual CLI for the limited supermarket extraction pilot."""

import argparse
import asyncio
import json
from dataclasses import asdict
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.modules.ingestion.application.use_cases import ExecuteScrapingRunUseCase
from app.modules.ingestion.domain.entities import ScrapingSource
from app.modules.ingestion.domain.ports import ScraperPort
from app.modules.ingestion.infrastructure.scrapers import CoopeScraper, JumboScraper
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a limited supermarket scraping pilot.")
    parser.add_argument("--source-id", required=True, type=UUID)
    parser.add_argument("--scraper", choices=("jumbo", "coope"), default="jumbo")
    parser.add_argument("--query", action="append", required=True, help="Product phrase; repeat to add more.")
    parser.add_argument("--city", default="Comodoro Rivadavia")
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    unit_of_work = SQLAlchemyUnitOfWork(async_session_factory)

    def create_scraper(source: ScrapingSource) -> ScraperPort:
        scraper_class = JumboScraper if args.scraper == "jumbo" else CoopeScraper
        return scraper_class(
            args.query,
            city=args.city,
            base_url=source.base_url,
            result_limit=args.limit,
        )

    try:
        result = await ExecuteScrapingRunUseCase(unit_of_work, create_scraper).execute(args.source_id)
    except OperationalError as error:
        if "no such table: scraping_source" not in str(error):
            raise
        raise SystemExit(
            "The configured database has not applied the ingestion migration. "
            "Run `uv run alembic upgrade head` and `uv run python scripts/seed_initial_data.py` "
            "from backend using the same DATABASE_URL."
        ) from error

    print(json.dumps(asdict(result), default=str, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
