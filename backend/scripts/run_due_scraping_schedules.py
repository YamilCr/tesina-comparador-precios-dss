"""Run every due scraping schedule once, then exit for a cloud cron service."""

import asyncio
import json
from dataclasses import asdict

from app.config import get_settings
from app.dependencies import get_product_search_index
from app.modules.ingestion.infrastructure.scheduler import ScrapingScheduler
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_engine, async_session_factory


async def main() -> None:
    """Claims due plans, refreshes them, and leaves future execution to the platform cron."""
    settings = get_settings()
    if not settings.ingestion_scheduler_enabled:
        raise SystemExit("INGESTION_SCHEDULER_ENABLED must be true for the cron worker.")

    scheduler = ScrapingScheduler(
        lambda: SQLAlchemyUnitOfWork(async_session_factory),
        poll_seconds=settings.ingestion_scheduler_poll_seconds,
        batch_size=settings.ingestion_scheduler_batch_size,
        max_concurrency=settings.ingestion_scheduler_max_concurrency,
        lease_seconds=settings.ingestion_scheduler_lease_seconds,
        product_search_index_factory=get_product_search_index,
    )
    try:
        results = await scheduler.run_due_once()
        print(json.dumps([asdict(result) for result in results], default=str, ensure_ascii=True))
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
