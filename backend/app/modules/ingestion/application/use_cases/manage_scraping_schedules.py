"""Use cases for persistent automatic scraping schedule administration."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.modules.ingestion.application.commands import (
    CreateScrapingScheduleCommand,
    UpdateScrapingScheduleCommand,
)
from app.modules.ingestion.application.dto import (
    ScheduledRefreshExecutionDTO,
    ScrapingScheduleDTO,
)
from app.modules.ingestion.domain.entities import ScrapingSchedule
from app.shared.application import UnitOfWorkPort


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Schedule timestamps must include a timezone.")
    return value.astimezone(timezone.utc)


class CreateScrapingScheduleUseCase:
    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        now_provider: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._now_provider = now_provider

    async def execute(self, command: CreateScrapingScheduleCommand) -> ScrapingScheduleDTO:
        now = _require_aware(self._now_provider())
        next_run_at = (
            now + timedelta(minutes=command.interval_minutes)
            if command.next_run_at is None
            else _require_aware(command.next_run_at)
        )
        async with self._unit_of_work as uow:
            source = await uow.ingestion.get_source_by_id(command.source_id)
            if source is None:
                raise ValueError("Scraping source not found.")
            if command.enabled and not source.active:
                raise ValueError("Cannot enable a schedule for an inactive source.")
            if await uow.ingestion.get_schedule_by_source_id(source.id) is not None:
                raise ValueError("Scraping source already has a schedule.")

            schedule = ScrapingSchedule(
                id=uuid4(),
                scraping_source_id=source.id,
                name=command.name,
                queries=command.queries,
                city=command.city,
                interval_minutes=command.interval_minutes,
                retry_delay_minutes=command.retry_delay_minutes,
                result_limit=command.result_limit,
                timeout_seconds=command.timeout_seconds,
                next_run_at=next_run_at,
                enabled=command.enabled,
                created_at=now,
                updated_at=now,
            )
            saved = await uow.ingestion.save_schedule(schedule)
            await uow.commit()
        return ScrapingScheduleDTO.from_entity(saved)


class UpdateScrapingScheduleUseCase:
    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        now_provider: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._now_provider = now_provider

    async def execute(self, command: UpdateScrapingScheduleCommand) -> ScrapingScheduleDTO:
        now = _require_aware(self._now_provider())
        async with self._unit_of_work as uow:
            schedule = await uow.ingestion.get_schedule_by_id(command.schedule_id)
            if schedule is None:
                raise ValueError("Scraping schedule not found.")
            source = await uow.ingestion.get_source_by_id(schedule.scraping_source_id)
            if source is None:
                raise ValueError("Scraping source not found.")
            if command.enabled is True and not source.active:
                raise ValueError("Cannot enable a schedule for an inactive source.")
            schedule.update_configuration(
                name=command.name,
                queries=command.queries,
                city=command.city,
                interval_minutes=command.interval_minutes,
                retry_delay_minutes=command.retry_delay_minutes,
                result_limit=command.result_limit,
                timeout_seconds=command.timeout_seconds,
                next_run_at=(
                    _require_aware(command.next_run_at)
                    if command.next_run_at is not None
                    else None
                ),
                enabled=command.enabled,
            )
            schedule.updated_at = now
            if command.enabled is False:
                schedule.locked_until = None
            saved = await uow.ingestion.save_schedule(schedule)
            await uow.commit()
        return ScrapingScheduleDTO.from_entity(saved)


class ListScrapingSchedulesUseCase:
    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, enabled_only: bool | None = None) -> list[ScrapingScheduleDTO]:
        async with self._unit_of_work as uow:
            schedules = await uow.ingestion.list_schedules(enabled_only=enabled_only)
        return [ScrapingScheduleDTO.from_entity(schedule) for schedule in schedules]


class ListScheduledRefreshExecutionsUseCase:
    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        schedule_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ScheduledRefreshExecutionDTO]:
        async with self._unit_of_work as uow:
            if (
                schedule_id is not None
                and await uow.ingestion.get_schedule_by_id(schedule_id) is None
            ):
                raise ValueError("Scraping schedule not found.")
            executions = await uow.ingestion.list_schedule_executions(
                schedule_id=schedule_id,
                limit=limit,
            )
        return [ScheduledRefreshExecutionDTO.from_entity(item) for item in executions]


class ClaimDueScrapingSchedulesUseCase:
    """Claims a bounded batch using database leases shared by all app workers."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        now: datetime,
        lease_seconds: int,
        limit: int,
    ) -> list[ScrapingScheduleDTO]:
        now = _require_aware(now)
        async with self._unit_of_work as uow:
            schedules = await uow.ingestion.claim_due_schedules(
                now=now,
                locked_until=now + timedelta(seconds=lease_seconds),
                limit=limit,
            )
            await uow.commit()
        return [ScrapingScheduleDTO.from_entity(schedule) for schedule in schedules]


class ClaimScrapingScheduleNowUseCase:
    """Claims one schedule for an explicit run-now request."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        schedule_id: UUID,
        *,
        now: datetime,
        lease_seconds: int,
    ) -> ScrapingScheduleDTO:
        now = _require_aware(now)
        async with self._unit_of_work as uow:
            current = await uow.ingestion.get_schedule_by_id(schedule_id)
            if current is None:
                raise ValueError("Scraping schedule not found.")
            if not current.enabled:
                raise ValueError("Scraping schedule is disabled.")
            claimed = await uow.ingestion.claim_schedule(
                schedule_id,
                now=now,
                locked_until=now + timedelta(seconds=lease_seconds),
            )
            if claimed is None:
                raise ValueError("Scraping schedule is already running.")
            await uow.commit()
        return ScrapingScheduleDTO.from_entity(claimed)

