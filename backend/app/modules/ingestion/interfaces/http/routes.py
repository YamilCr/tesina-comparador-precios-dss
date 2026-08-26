"""HTTP routes for ingestion administration and refresh automation."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import SettingsDependency, get_unit_of_work
from app.modules.ingestion.application.commands import (
    CompleteScrapingRunCommand,
    CreateScrapingScheduleCommand,
    CreateScrapingSourceCommand,
    FailScrapingRunCommand,
    StartScrapingRunCommand,
    UpdateScrapingScheduleCommand,
    UpdateScrapingSourceCommand,
)
from app.modules.ingestion.application.dto import ScrapingRunDTO, ScrapingSourceDTO
from app.modules.ingestion.application.use_cases import (
    CompleteScrapingRunUseCase,
    ClaimScrapingScheduleNowUseCase,
    ConcurrentRefreshScrapingSourcesUseCase,
    CreateScrapingSourceUseCase,
    CreateScrapingScheduleUseCase,
    FailScrapingRunUseCase,
    ListScrapingRunsUseCase,
    ListScheduledRefreshExecutionsUseCase,
    ListScrapingSchedulesUseCase,
    ListScrapingSourcesUseCase,
    RefreshScrapingSourceUseCase,
    RunScrapingScheduleUseCase,
    StartScrapingRunUseCase,
    UpdateScrapingSourceUseCase,
    UpdateScrapingScheduleUseCase,
)
from app.modules.ingestion.domain.entities import ScrapingSource
from app.modules.ingestion.domain.ports import ScraperPort
from app.modules.ingestion.infrastructure.scrapers import create_scraper_for_source
from app.shared.application import UnitOfWorkPort
from app.shared.interfaces.http import collection_response

from .schemas import (
    CompleteScrapingRunRequest,
    ConcurrentRefreshScrapingSourcesRequest,
    ConcurrentScrapingRefreshResponse,
    ConcurrentScrapingSourceResultResponse,
    CreateScrapingSourceRequest,
    CreateScrapingScheduleRequest,
    EtlLoadResultResponse,
    FailScrapingRunRequest,
    RefreshScrapingSourceRequest,
    ScheduledRefreshExecutionResponse,
    ScrapingRefreshResponse,
    ScrapingRunResponse,
    ScrapingScheduleResponse,
    ScrapingSourceResponse,
    UpdateScrapingSourceRequest,
    UpdateScrapingScheduleRequest,
)


router = APIRouter(prefix="/ingestion", tags=["ingestion"])
UnitOfWorkDependency = Annotated[UnitOfWorkPort, Depends(get_unit_of_work)]


def _source_payload(source: ScrapingSourceDTO) -> dict:
    return ScrapingSourceResponse(
        id=source.id,
        supermarket_id=source.supermarket_id,
        name=source.name,
        base_url=source.base_url,
        scraper_key=source.scraper_key,
        branch_id=source.branch_id,
        active=source.active,
        created_at=source.created_at,
    ).model_dump(mode="json")


def _run_payload(run: ScrapingRunDTO) -> dict:
    return ScrapingRunResponse(
        id=run.id,
        scraping_source_id=run.scraping_source_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        items_scraped=run.items_scraped,
        items_loaded=run.items_loaded,
        error_message=run.error_message,
    ).model_dump(mode="json")


def _schedule_payload(schedule) -> dict:
    return ScrapingScheduleResponse(
        id=schedule.id,
        scraping_source_id=schedule.scraping_source_id,
        name=schedule.name,
        queries=list(schedule.queries),
        city=schedule.city,
        interval_minutes=schedule.interval_minutes,
        retry_delay_minutes=schedule.retry_delay_minutes,
        result_limit=schedule.result_limit,
        timeout_seconds=schedule.timeout_seconds,
        enabled=schedule.enabled,
        next_run_at=schedule.next_run_at,
        locked_until=schedule.locked_until,
        consecutive_failures=schedule.consecutive_failures,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    ).model_dump(mode="json")


def _schedule_execution_payload(execution) -> dict:
    return ScheduledRefreshExecutionResponse(
        id=execution.id,
        schedule_id=execution.schedule_id,
        scraping_run_id=execution.scraping_run_id,
        status=execution.status,
        scheduled_for=execution.scheduled_for,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        error_message=execution.error_message,
    ).model_dump(mode="json")


def _refresh_payload(refresh) -> dict:
    return ScrapingRefreshResponse(
        run=ScrapingRunResponse(**_run_payload(refresh.run)),
        load=EtlLoadResultResponse(
            run_id=refresh.load.run_id,
            processed=refresh.load.processed,
            loaded=refresh.load.loaded,
            rejected=refresh.load.rejected,
            duplicates=refresh.load.duplicates,
            unmatched=refresh.load.unmatched,
            created_products=refresh.load.created_products,
            created_prices=refresh.load.created_prices,
        ),
    ).model_dump(mode="json")


def _load_payload(load) -> EtlLoadResultResponse:
    return EtlLoadResultResponse(
        run_id=load.run_id,
        processed=load.processed,
        loaded=load.loaded,
        rejected=load.rejected,
        duplicates=load.duplicates,
        unmatched=load.unmatched,
        created_products=load.created_products,
        created_prices=load.created_prices,
    )


def _concurrent_refresh_payload(refresh) -> dict:
    return ConcurrentScrapingRefreshResponse(
        results=[
            ConcurrentScrapingSourceResultResponse(
                source_id=result.source_id,
                source_name=result.source_name,
                run=ScrapingRunResponse(**_run_payload(result.run)),
                duration_ms=result.duration_ms,
                load=_load_payload(result.load) if result.load else None,
                error_message=result.error_message,
            )
            for result in refresh.results
        ]
    ).model_dump(mode="json")


def _raise_ingestion_error(error: ValueError) -> None:
    message = str(error)
    if "not found" in message:
        status_code = status.HTTP_404_NOT_FOUND
    elif "already" in message or "open run" in message:
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    raise HTTPException(status_code=status_code, detail=message) from error


@router.get("/sources")
async def list_scraping_sources(
    uow: UnitOfWorkDependency,
    active_only: bool | None = Query(default=None),
) -> dict:
    sources = await ListScrapingSourcesUseCase(uow).execute(active_only=active_only)
    return collection_response([_source_payload(source) for source in sources])


@router.post("/sources", status_code=status.HTTP_201_CREATED)
async def create_scraping_source(
    request: CreateScrapingSourceRequest,
    uow: UnitOfWorkDependency,
) -> dict:
    try:
        source = await CreateScrapingSourceUseCase(uow).execute(
            CreateScrapingSourceCommand(
                supermarket_id=request.supermarket_id,
                name=request.name,
                base_url=request.base_url,
                scraper_key=request.scraper_key,
                branch_id=request.branch_id,
                active=request.active,
            )
        )
    except ValueError as error:
        _raise_ingestion_error(error)
    return _source_payload(source)


@router.patch("/sources/{source_id}")
async def update_scraping_source(
    source_id: UUID,
    request: UpdateScrapingSourceRequest,
    uow: UnitOfWorkDependency,
) -> dict:
    try:
        source = await UpdateScrapingSourceUseCase(uow).execute(
            UpdateScrapingSourceCommand(
                source_id=source_id,
                name=request.name,
                base_url=request.base_url,
                scraper_key=request.scraper_key,
                branch_id=request.branch_id,
                active=request.active,
            )
        )
    except ValueError as error:
        _raise_ingestion_error(error)
    return _source_payload(source)


@router.get("/schedules")
async def list_scraping_schedules(
    uow: UnitOfWorkDependency,
    enabled_only: bool | None = Query(default=None),
) -> dict:
    schedules = await ListScrapingSchedulesUseCase(uow).execute(enabled_only=enabled_only)
    return collection_response([_schedule_payload(schedule) for schedule in schedules])


@router.post("/schedules", status_code=status.HTTP_201_CREATED)
async def create_scraping_schedule(
    request: CreateScrapingScheduleRequest,
    uow: UnitOfWorkDependency,
) -> dict:
    try:
        schedule = await CreateScrapingScheduleUseCase(uow).execute(
            CreateScrapingScheduleCommand(
                source_id=request.source_id,
                name=request.name,
                queries=tuple(request.queries),
                city=request.city,
                interval_minutes=request.interval_minutes,
                retry_delay_minutes=request.retry_delay_minutes,
                result_limit=request.result_limit,
                timeout_seconds=request.timeout_seconds,
                next_run_at=request.next_run_at,
                enabled=request.enabled,
            )
        )
    except ValueError as error:
        _raise_ingestion_error(error)
    return _schedule_payload(schedule)


@router.patch("/schedules/{schedule_id}")
async def update_scraping_schedule(
    schedule_id: UUID,
    request: UpdateScrapingScheduleRequest,
    uow: UnitOfWorkDependency,
) -> dict:
    try:
        schedule = await UpdateScrapingScheduleUseCase(uow).execute(
            UpdateScrapingScheduleCommand(
                schedule_id=schedule_id,
                name=request.name,
                queries=tuple(request.queries) if request.queries is not None else None,
                city=request.city,
                interval_minutes=request.interval_minutes,
                retry_delay_minutes=request.retry_delay_minutes,
                result_limit=request.result_limit,
                timeout_seconds=request.timeout_seconds,
                next_run_at=request.next_run_at,
                enabled=request.enabled,
            )
        )
    except ValueError as error:
        _raise_ingestion_error(error)
    return _schedule_payload(schedule)


@router.get("/schedule-executions")
async def list_scheduled_refresh_executions(
    uow: UnitOfWorkDependency,
    schedule_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    try:
        executions = await ListScheduledRefreshExecutionsUseCase(uow).execute(
            schedule_id=schedule_id,
            limit=limit,
        )
    except ValueError as error:
        _raise_ingestion_error(error)
    return collection_response(
        [_schedule_execution_payload(execution) for execution in executions]
    )


@router.post("/schedules/{schedule_id}/run-now")
async def run_scraping_schedule_now(
    schedule_id: UUID,
    uow: UnitOfWorkDependency,
    settings: SettingsDependency,
) -> dict:
    now = datetime.now(timezone.utc)
    try:
        schedule = await ClaimScrapingScheduleNowUseCase(uow).execute(
            schedule_id,
            now=now,
            lease_seconds=settings.ingestion_scheduler_lease_seconds,
        )
        execution = await RunScrapingScheduleUseCase(
            uow,
            lambda source, plan: create_scraper_for_source(
                source,
                queries=list(plan.queries),
                city=plan.city,
                result_limit=plan.result_limit,
            ),
        ).execute(schedule.id, scheduled_for=now)
    except ValueError as error:
        _raise_ingestion_error(error)
    return _schedule_execution_payload(execution)


@router.get("/runs")
async def list_scraping_runs(
    uow: UnitOfWorkDependency,
    source_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    try:
        runs = await ListScrapingRunsUseCase(uow).execute(source_id=source_id, limit=limit)
    except ValueError as error:
        _raise_ingestion_error(error)
    return collection_response([_run_payload(run) for run in runs])


@router.post("/sources/{source_id}/runs", status_code=status.HTTP_201_CREATED)
async def start_scraping_run(source_id: UUID, uow: UnitOfWorkDependency) -> dict:
    try:
        run = await StartScrapingRunUseCase(uow).execute(
            StartScrapingRunCommand(source_id=source_id)
        )
    except ValueError as error:
        _raise_ingestion_error(error)
    return _run_payload(run)


@router.post("/sources/{source_id}/refresh")
async def refresh_scraping_source(
    source_id: UUID,
    request: RefreshScrapingSourceRequest,
    uow: UnitOfWorkDependency,
) -> dict:
    """Runs a bounded external extraction and loads its validated price history."""

    def create_scraper(source: ScrapingSource) -> ScraperPort:
        return create_scraper_for_source(
            source,
            queries=request.queries,
            city=request.city,
            result_limit=request.limit,
        )

    try:
        refresh = await RefreshScrapingSourceUseCase(uow, create_scraper).execute(source_id)
    except ValueError as error:
        _raise_ingestion_error(error)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Scraper failed: {error}",
        ) from error
    return _refresh_payload(refresh)


@router.post("/sources/refresh-concurrently")
async def refresh_scraping_sources_concurrently(
    request: ConcurrentRefreshScrapingSourcesRequest,
    uow: UnitOfWorkDependency,
) -> dict:
    """Extracts several configured sources concurrently and persists each ETL result serially."""

    def create_scraper(source: ScrapingSource) -> ScraperPort:
        return create_scraper_for_source(
            source,
            queries=request.queries,
            city=request.city,
            result_limit=request.limit,
        )

    try:
        refresh = await ConcurrentRefreshScrapingSourcesUseCase(
            uow,
            create_scraper,
            max_concurrency=request.max_concurrency,
            timeout_seconds=request.timeout_seconds,
        ).execute(request.source_ids)
    except ValueError as error:
        _raise_ingestion_error(error)
    return _concurrent_refresh_payload(refresh)


@router.post("/runs/{run_id}/succeed")
async def complete_scraping_run(
    run_id: UUID,
    request: CompleteScrapingRunRequest,
    uow: UnitOfWorkDependency,
) -> dict:
    try:
        run = await CompleteScrapingRunUseCase(uow).execute(
            CompleteScrapingRunCommand(
                run_id=run_id,
                items_scraped=request.items_scraped,
                items_loaded=request.items_loaded,
            )
        )
    except ValueError as error:
        _raise_ingestion_error(error)
    return _run_payload(run)


@router.post("/runs/{run_id}/fail")
async def fail_scraping_run(
    run_id: UUID,
    request: FailScrapingRunRequest,
    uow: UnitOfWorkDependency,
) -> dict:
    try:
        run = await FailScrapingRunUseCase(uow).execute(
            FailScrapingRunCommand(run_id=run_id, error_message=request.error_message)
        )
    except ValueError as error:
        _raise_ingestion_error(error)
    return _run_payload(run)
