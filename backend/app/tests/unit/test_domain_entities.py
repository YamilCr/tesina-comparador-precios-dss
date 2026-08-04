from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.ingestion.domain.entities import ScrapingRun, ScrapingSource
from app.modules.prices.domain.entities import PriceSnapshot


def test_price_snapshot_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="amount"):
        PriceSnapshot(
            product_id=uuid4(),
            product_source_id=uuid4(),
            branch_id=uuid4(),
            amount=Decimal("-1"),
            observed_at=datetime.now(timezone.utc),
        )


def test_scraping_source_normalizes_required_text() -> None:
    source = ScrapingSource(
        id=uuid4(),
        supermarket_id=uuid4(),
        name=" Carrefour ",
        base_url=" https://example.com/catalog ",
    )

    assert source.name == "Carrefour"
    assert source.base_url == "https://example.com/catalog"
    assert source.active is True


def test_scraping_run_tracks_successful_execution() -> None:
    started_at = datetime.now(timezone.utc)
    finished_at = started_at + timedelta(minutes=3)
    run = ScrapingRun(id=uuid4(), scraping_source_id=uuid4(), started_at=started_at)

    run.mark_running()
    run.mark_succeeded(finished_at, items_scraped=25, items_loaded=20)

    assert run.status == "succeeded"
    assert run.finished_at == finished_at
    assert run.items_scraped == 25
    assert run.items_loaded == 20
    assert run.error_message is None


def test_scraping_run_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="Invalid scraping run status"):
        ScrapingRun(
            id=uuid4(),
            scraping_source_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            status="unknown",
        )
