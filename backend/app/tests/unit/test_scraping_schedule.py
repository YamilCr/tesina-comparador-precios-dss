"""Unit tests for scheduler configuration and retry behavior."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.modules.ingestion.domain.entities import ScrapingSchedule


def _schedule(now: datetime) -> ScrapingSchedule:
    return ScrapingSchedule(
        id=uuid4(),
        scraping_source_id=uuid4(),
        name="  Actualizacion diaria  ",
        queries=(" leche ", "leche", "coca cola"),
        city=" Comodoro Rivadavia ",
        interval_minutes=60,
        retry_delay_minutes=5,
        result_limit=10,
        timeout_seconds=30,
        next_run_at=now,
    )


def test_schedule_normalizes_configuration_and_resets_after_success() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    schedule = _schedule(now)

    assert schedule.name == "Actualizacion diaria"
    assert schedule.city == "Comodoro Rivadavia"
    assert schedule.queries == ("leche", "coca cola")

    schedule.mark_failed(now)
    assert schedule.consecutive_failures == 1
    assert schedule.next_run_at == now + timedelta(minutes=5)

    schedule.mark_succeeded(now)
    assert schedule.consecutive_failures == 0
    assert schedule.next_run_at == now + timedelta(minutes=60)


def test_schedule_applies_bounded_exponential_failure_backoff() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    schedule = _schedule(now)

    expected_delays = (5, 10, 20, 40, 40)
    for expected_delay in expected_delays:
        schedule.mark_failed(now)
        assert schedule.next_run_at == now + timedelta(minutes=expected_delay)

