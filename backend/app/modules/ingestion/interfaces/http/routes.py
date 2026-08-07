"""HTTP routes for ingestion administration without external scraping."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_unit_of_work
from app.modules.ingestion.application.commands import (
    CompleteScrapingRunCommand,
    CreateScrapingSourceCommand,
    FailScrapingRunCommand,
    StartScrapingRunCommand,
    UpdateScrapingSourceCommand,
)
from app.modules.ingestion.application.dto import ScrapingRunDTO, ScrapingSourceDTO
from app.modules.ingestion.application.use_cases import (
    CompleteScrapingRunUseCase,
    CreateScrapingSourceUseCase,
    FailScrapingRunUseCase,
    ListScrapingRunsUseCase,
    ListScrapingSourcesUseCase,
    StartScrapingRunUseCase,
    UpdateScrapingSourceUseCase,
)
from app.shared.application import UnitOfWorkPort
from app.shared.interfaces.http import collection_response

from .schemas import (
    CompleteScrapingRunRequest,
    CreateScrapingSourceRequest,
    FailScrapingRunRequest,
    ScrapingRunResponse,
    ScrapingSourceResponse,
    UpdateScrapingSourceRequest,
)


router = APIRouter(prefix="/ingestion", tags=["ingestion"])
UnitOfWorkDependency = Annotated[UnitOfWorkPort, Depends(get_unit_of_work)]


def _source_payload(source: ScrapingSourceDTO) -> dict:
    return ScrapingSourceResponse(
        id=source.id,
        supermarket_id=source.supermarket_id,
        name=source.name,
        base_url=source.base_url,
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
                active=request.active,
            )
        )
    except ValueError as error:
        _raise_ingestion_error(error)
    return _source_payload(source)


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
