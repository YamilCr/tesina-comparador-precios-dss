"""Async SQLAlchemy adapter for ingestion administration."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.domain.entities import ScrapingRun, ScrapingSource
from app.modules.ingestion.domain.ports import IngestionRepositoryPort

from .mappers import (
    scraping_run_entity_to_model,
    scraping_run_model_to_entity,
    scraping_source_entity_to_model,
    scraping_source_model_to_entity,
)
from .sqlalchemy_models import ScrapingRunModel, ScrapingSourceModel


class SQLAlchemyIngestionRepository(IngestionRepositoryPort):
    """Persists source configuration and scraping audit records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_source_by_id(self, source_id: UUID) -> ScrapingSource | None:
        model = await self._session.get(ScrapingSourceModel, source_id)
        return scraping_source_model_to_entity(model) if model is not None else None

    async def get_source_by_supermarket_and_name(
        self,
        supermarket_id: UUID,
        name: str,
    ) -> ScrapingSource | None:
        model = await self._session.scalar(
            select(ScrapingSourceModel).where(
                ScrapingSourceModel.supermercado_id == supermarket_id,
                ScrapingSourceModel.nombre == name,
            )
        )
        return scraping_source_model_to_entity(model) if model is not None else None

    async def list_sources(self, active_only: bool | None = None) -> list[ScrapingSource]:
        statement = select(ScrapingSourceModel).order_by(
            ScrapingSourceModel.nombre,
            ScrapingSourceModel.id,
        )
        if active_only is not None:
            statement = statement.where(ScrapingSourceModel.activo.is_(active_only))
        models = await self._session.scalars(statement)
        return [scraping_source_model_to_entity(model) for model in models.all()]

    async def save_source(self, source: ScrapingSource) -> ScrapingSource:
        model = await self._session.get(ScrapingSourceModel, source.id)
        if model is None:
            model = scraping_source_entity_to_model(source)
            self._session.add(model)
        else:
            model.supermercado_id = source.supermarket_id
            model.nombre = source.name
            model.base_url = source.base_url
            model.activo = source.active
        await self._session.flush()
        return scraping_source_model_to_entity(model)

    async def get_run_by_id(self, run_id: UUID) -> ScrapingRun | None:
        model = await self._session.get(ScrapingRunModel, run_id)
        return scraping_run_model_to_entity(model) if model is not None else None

    async def list_runs(
        self,
        source_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ScrapingRun]:
        statement = select(ScrapingRunModel).order_by(
            ScrapingRunModel.iniciado_en.desc(),
            ScrapingRunModel.id.desc(),
        ).limit(limit)
        if source_id is not None:
            statement = statement.where(ScrapingRunModel.scraping_source_id == source_id)
        models = await self._session.scalars(statement)
        return [scraping_run_model_to_entity(model) for model in models.all()]

    async def find_open_run(self, source_id: UUID) -> ScrapingRun | None:
        model = await self._session.scalar(
            select(ScrapingRunModel)
            .where(
                ScrapingRunModel.scraping_source_id == source_id,
                ScrapingRunModel.estado.in_(("pending", "running")),
            )
            .order_by(ScrapingRunModel.iniciado_en.desc())
        )
        return scraping_run_model_to_entity(model) if model is not None else None

    async def save_run(self, run: ScrapingRun) -> ScrapingRun:
        model = await self._session.get(ScrapingRunModel, run.id)
        if model is None:
            model = scraping_run_entity_to_model(run)
            self._session.add(model)
        else:
            model.scraping_source_id = run.scraping_source_id
            model.estado = run.status
            model.iniciado_en = run.started_at
            model.finalizado_en = run.finished_at
            model.items_extraidos = run.items_scraped
            model.items_cargados = run.items_loaded
            model.mensaje_error = run.error_message
        await self._session.flush()
        return scraping_run_model_to_entity(model)
