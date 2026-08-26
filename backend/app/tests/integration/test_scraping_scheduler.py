"""Integration tests for persistent scheduler plans, leases, and failure isolation."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.ingestion.application.commands import (
    CreateScrapingScheduleCommand,
    CreateScrapingSourceCommand,
)
from app.modules.ingestion.application.use_cases import (
    CreateScrapingScheduleUseCase,
    CreateScrapingSourceUseCase,
)
from app.modules.ingestion.domain.ports import ScraperPort
from app.modules.ingestion.infrastructure.scheduler import ScrapingScheduler
from app.shared.infrastructure import SQLAlchemyUnitOfWork

from .conftest import ASGIResponse, IntegrationSeedData


@dataclass
class SchedulerConcurrencyTracker:
    active: int = 0
    maximum: int = 0


class ScheduledStubScraper(ScraperPort):
    def __init__(
        self,
        tracker: SchedulerConcurrencyTracker,
        *,
        external_id: str,
        fails: bool = False,
    ) -> None:
        self._tracker = tracker
        self._external_id = external_id
        self._fails = fails

    async def scrape(self) -> list[dict]:
        self._tracker.active += 1
        self._tracker.maximum = max(self._tracker.maximum, self._tracker.active)
        try:
            await asyncio.sleep(0.03)
            if self._fails:
                raise RuntimeError("Scheduled source unavailable")
            return [
                {
                    "external_id": self._external_id,
                    "name": "Coca Cola Sabor Original 2.25 L",
                    "price": "3200",
                    "presentation": "2.25 L",
                    "url": f"https://example.test/{self._external_id}",
                }
            ]
        finally:
            self._tracker.active -= 1


@pytest.mark.asyncio
async def test_scheduler_isolates_failures_and_does_not_reclaim_finished_plans(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)
    create_source = CreateScrapingSourceUseCase(uow)
    successful_source = await create_source.execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Scheduled La Anonima",
            base_url="https://example.test/la",
            branch_id=seed_data.la_branch_id,
        )
    )
    failing_source = await create_source.execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.carrefour_id,
            name="Scheduled Carrefour",
            base_url="https://example.test/carrefour",
            branch_id=seed_data.carrefour_branch_id,
        )
    )
    due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    create_schedule = CreateScrapingScheduleUseCase(uow)
    successful_schedule = await create_schedule.execute(
        CreateScrapingScheduleCommand(
            source_id=successful_source.id,
            name="La Anonima cada hora",
            queries=("coca cola",),
            city="Comodoro Rivadavia",
            interval_minutes=60,
            next_run_at=due_at,
        )
    )
    failing_schedule = await create_schedule.execute(
        CreateScrapingScheduleCommand(
            source_id=failing_source.id,
            name="Carrefour cada hora",
            queries=("coca cola",),
            city="Comodoro Rivadavia",
            interval_minutes=60,
            retry_delay_minutes=5,
            next_run_at=due_at,
        )
    )

    tracker = SchedulerConcurrencyTracker()
    scrapers = {
        successful_source.id: ScheduledStubScraper(
            tracker,
            external_id="LA-COCA-225",
        ),
        failing_source.id: ScheduledStubScraper(
            tracker,
            external_id="CAR-COCA-225",
            fails=True,
        ),
    }
    scheduler = ScrapingScheduler(
        lambda: SQLAlchemyUnitOfWork(sqlite_session_factory),
        poll_seconds=60,
        batch_size=10,
        max_concurrency=2,
        lease_seconds=120,
        scraper_factory=lambda source, schedule: scrapers[source.id],
    )

    executions = await scheduler.run_due_once()

    assert tracker.maximum == 2
    assert {execution.status for execution in executions} == {"succeeded", "failed"}
    assert all(execution.scraping_run_id is not None for execution in executions)
    async with SQLAlchemyUnitOfWork(sqlite_session_factory) as check_uow:
        successful = await check_uow.ingestion.get_schedule_by_id(successful_schedule.id)
        failing = await check_uow.ingestion.get_schedule_by_id(failing_schedule.id)
        history = await check_uow.ingestion.list_schedule_executions(limit=10)
    assert successful is not None
    assert successful.consecutive_failures == 0
    assert successful.locked_until is None
    assert failing is not None
    assert failing.consecutive_failures == 1
    assert failing.locked_until is None
    assert len(history) == 2
    assert await scheduler.run_due_once() == []


@pytest.mark.asyncio
async def test_schedule_administration_api_is_persistent_and_validated(
    sqlite_uow_override: None,
    asgi_request,
    seed_data: IntegrationSeedData,
) -> None:
    source_response: ASGIResponse = await asgi_request(
        "POST",
        "/api/v1/ingestion/sources",
        json_body={
            "supermarket_id": str(seed_data.la_anonima_id),
            "name": "Scheduled API source",
            "base_url": "https://example.test/scheduled",
            "branch_id": str(seed_data.la_branch_id),
        },
    )
    source_id = source_response.json()["id"]
    schedule_response: ASGIResponse = await asgi_request(
        "POST",
        "/api/v1/ingestion/schedules",
        json_body={
            "source_id": source_id,
            "name": "Actualizacion API",
            "queries": ["leche", "coca cola"],
            "city": "Comodoro Rivadavia",
            "interval_minutes": 120,
            "retry_delay_minutes": 10,
            "next_run_at": "2026-09-01T12:00:00Z",
        },
    )
    assert schedule_response.status_code == 201
    schedule = schedule_response.json()
    assert schedule["queries"] == ["leche", "coca cola"]
    assert schedule["consecutive_failures"] == 0

    duplicate_response: ASGIResponse = await asgi_request(
        "POST",
        "/api/v1/ingestion/schedules",
        json_body={
            "source_id": source_id,
            "name": "Duplicada",
            "queries": ["leche"],
            "city": "Comodoro Rivadavia",
            "interval_minutes": 60,
        },
    )
    assert duplicate_response.status_code == 409

    update_response: ASGIResponse = await asgi_request(
        "PATCH",
        f"/api/v1/ingestion/schedules/{schedule['id']}",
        json_body={"enabled": False, "interval_minutes": 60},
    )
    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is False
    assert update_response.json()["interval_minutes"] == 60

    list_response: ASGIResponse = await asgi_request(
        "GET",
        "/api/v1/ingestion/schedules",
    )
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1

    run_now_response: ASGIResponse = await asgi_request(
        "POST",
        f"/api/v1/ingestion/schedules/{schedule['id']}/run-now",
    )
    assert run_now_response.status_code == 422

    history_response: ASGIResponse = await asgi_request(
        "GET",
        "/api/v1/ingestion/schedule-executions",
        query={"schedule_id": schedule["id"]},
    )
    assert history_response.status_code == 200
    assert history_response.json()["count"] == 0
