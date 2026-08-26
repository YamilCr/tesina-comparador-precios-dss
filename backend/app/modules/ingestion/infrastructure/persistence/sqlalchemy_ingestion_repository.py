"""Async SQLAlchemy adapter for ingestion administration."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.domain.entities import (
    ProductIdentityReview,
    ScheduledRefreshExecution,
    ScrapedProduct,
    ScrapingRun,
    ScrapingSchedule,
    ScrapingSource,
)
from app.modules.ingestion.domain.ports import IngestionRepositoryPort

from .mappers import (
    product_identity_review_entity_to_model,
    product_identity_review_model_to_entity,
    scheduled_execution_entity_to_model,
    scheduled_execution_model_to_entity,
    scraping_run_entity_to_model,
    scraping_run_model_to_entity,
    scraping_schedule_entity_to_model,
    scraping_schedule_model_to_entity,
    scraped_product_entity_to_model,
    scraped_product_model_to_entity,
    scraping_source_entity_to_model,
    scraping_source_model_to_entity,
)
from .sqlalchemy_models import (
    ProductIdentityReviewModel,
    ScheduledRefreshExecutionModel,
    ScrapedProductModel,
    ScrapingRunModel,
    ScrapingScheduleModel,
    ScrapingSourceModel,
)


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
            model.scraper_key = source.scraper_key
            model.sucursal_id = source.branch_id
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

    async def get_schedule_by_id(self, schedule_id: UUID) -> ScrapingSchedule | None:
        model = await self._session.get(ScrapingScheduleModel, schedule_id)
        return scraping_schedule_model_to_entity(model) if model is not None else None

    async def get_schedule_by_source_id(self, source_id: UUID) -> ScrapingSchedule | None:
        model = await self._session.scalar(
            select(ScrapingScheduleModel).where(
                ScrapingScheduleModel.scraping_source_id == source_id
            )
        )
        return scraping_schedule_model_to_entity(model) if model is not None else None

    async def list_schedules(
        self,
        enabled_only: bool | None = None,
    ) -> list[ScrapingSchedule]:
        statement = select(ScrapingScheduleModel).order_by(
            ScrapingScheduleModel.next_run_at,
            ScrapingScheduleModel.name,
            ScrapingScheduleModel.id,
        )
        if enabled_only is not None:
            statement = statement.where(ScrapingScheduleModel.enabled.is_(enabled_only))
        models = await self._session.scalars(statement)
        return [scraping_schedule_model_to_entity(model) for model in models.all()]

    async def save_schedule(self, schedule: ScrapingSchedule) -> ScrapingSchedule:
        model = await self._session.get(ScrapingScheduleModel, schedule.id)
        if model is None:
            model = scraping_schedule_entity_to_model(schedule)
            self._session.add(model)
        else:
            model.scraping_source_id = schedule.scraping_source_id
            model.name = schedule.name
            model.queries = list(schedule.queries)
            model.city = schedule.city
            model.interval_minutes = schedule.interval_minutes
            model.retry_delay_minutes = schedule.retry_delay_minutes
            model.result_limit = schedule.result_limit
            model.timeout_seconds = schedule.timeout_seconds
            model.enabled = schedule.enabled
            model.next_run_at = schedule.next_run_at
            model.locked_until = schedule.locked_until
            model.consecutive_failures = schedule.consecutive_failures
            if schedule.updated_at is not None:
                model.updated_at = schedule.updated_at
        await self._session.flush()
        return scraping_schedule_model_to_entity(model)

    async def claim_due_schedules(
        self,
        now: datetime,
        locked_until: datetime,
        limit: int,
    ) -> list[ScrapingSchedule]:
        candidate_ids = await self._session.scalars(
            select(ScrapingScheduleModel.id)
            .where(
                ScrapingScheduleModel.enabled.is_(True),
                ScrapingScheduleModel.next_run_at <= now,
                or_(
                    ScrapingScheduleModel.locked_until.is_(None),
                    ScrapingScheduleModel.locked_until <= now,
                ),
            )
            .order_by(ScrapingScheduleModel.next_run_at, ScrapingScheduleModel.id)
            .limit(limit)
        )
        claimed: list[ScrapingSchedule] = []
        for schedule_id in candidate_ids.all():
            result = await self._session.execute(
                update(ScrapingScheduleModel)
                .where(
                    ScrapingScheduleModel.id == schedule_id,
                    ScrapingScheduleModel.enabled.is_(True),
                    ScrapingScheduleModel.next_run_at <= now,
                    or_(
                        ScrapingScheduleModel.locked_until.is_(None),
                        ScrapingScheduleModel.locked_until <= now,
                    ),
                )
                .values(locked_until=locked_until, updated_at=now)
            )
            if result.rowcount != 1:
                continue
            model = await self._session.get(ScrapingScheduleModel, schedule_id)
            if model is not None:
                claimed.append(scraping_schedule_model_to_entity(model))
        return claimed

    async def claim_schedule(
        self,
        schedule_id: UUID,
        now: datetime,
        locked_until: datetime,
    ) -> ScrapingSchedule | None:
        result = await self._session.execute(
            update(ScrapingScheduleModel)
            .where(
                ScrapingScheduleModel.id == schedule_id,
                ScrapingScheduleModel.enabled.is_(True),
                or_(
                    ScrapingScheduleModel.locked_until.is_(None),
                    ScrapingScheduleModel.locked_until <= now,
                ),
            )
            .values(locked_until=locked_until, updated_at=now)
        )
        if result.rowcount != 1:
            return None
        model = await self._session.get(ScrapingScheduleModel, schedule_id)
        return scraping_schedule_model_to_entity(model) if model is not None else None

    async def get_schedule_execution(
        self,
        execution_id: UUID,
    ) -> ScheduledRefreshExecution | None:
        model = await self._session.get(ScheduledRefreshExecutionModel, execution_id)
        return scheduled_execution_model_to_entity(model) if model is not None else None

    async def list_schedule_executions(
        self,
        schedule_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ScheduledRefreshExecution]:
        statement = select(ScheduledRefreshExecutionModel).order_by(
            ScheduledRefreshExecutionModel.started_at.desc(),
            ScheduledRefreshExecutionModel.id.desc(),
        ).limit(limit)
        if schedule_id is not None:
            statement = statement.where(
                ScheduledRefreshExecutionModel.schedule_id == schedule_id
            )
        models = await self._session.scalars(statement)
        return [scheduled_execution_model_to_entity(model) for model in models.all()]

    async def save_schedule_execution(
        self,
        execution: ScheduledRefreshExecution,
    ) -> ScheduledRefreshExecution:
        model = await self._session.get(ScheduledRefreshExecutionModel, execution.id)
        if model is None:
            model = scheduled_execution_entity_to_model(execution)
            self._session.add(model)
        else:
            model.schedule_id = execution.schedule_id
            model.scraping_run_id = execution.scraping_run_id
            model.status = execution.status
            model.scheduled_for = execution.scheduled_for
            model.started_at = execution.started_at
            model.finished_at = execution.finished_at
            model.error_message = execution.error_message
        await self._session.flush()
        return scheduled_execution_model_to_entity(model)

    async def save_scraped_products(
        self,
        products: list[ScrapedProduct],
    ) -> list[ScrapedProduct]:
        """Persists raw records and any later quality outcome without committing."""
        saved_products: list[ScrapedProduct] = []
        for product in products:
            model = await self._session.get(ScrapedProductModel, product.id)
            if model is None:
                model = scraped_product_entity_to_model(product)
                self._session.add(model)
            else:
                model.scraping_run_id = product.scraping_run_id
                model.codigo_externo = product.external_code
                model.ean = product.ean
                model.nombre = product.name
                model.marca = product.brand
                model.precio = product.amount
                model.presentacion = product.presentation
                model.url_producto = product.product_url
                model.payload_crudo = product.raw_payload
                model.estado = product.status
                model.mensaje_calidad = product.quality_message
                model.producto_fuente_id = product.product_source_id
                model.precio_id = product.price_id
                model.procesado_en = product.processed_at
            await self._session.flush()
            saved_products.append(scraped_product_model_to_entity(model))
        return saved_products

    async def list_scraped_products(
        self,
        run_id: UUID,
        statuses: set[str] | None = None,
    ) -> list[ScrapedProduct]:
        """Lists staged records deterministically for ETL processing."""
        statement = (
            select(ScrapedProductModel)
            .where(ScrapedProductModel.scraping_run_id == run_id)
            .order_by(ScrapedProductModel.created_at, ScrapedProductModel.id)
        )
        if statuses is not None:
            statement = statement.where(ScrapedProductModel.estado.in_(statuses))
        models = await self._session.scalars(statement)
        return [scraped_product_model_to_entity(model) for model in models.all()]

    async def list_loaded_scraped_products(self) -> list[ScrapedProduct]:
        """Lists loaded evidence used by administrative catalog enrichment."""
        models = await self._session.scalars(
            select(ScrapedProductModel)
            .where(
                ScrapedProductModel.estado == "loaded",
                ScrapedProductModel.producto_fuente_id.is_not(None),
            )
            .order_by(ScrapedProductModel.created_at, ScrapedProductModel.id)
        )
        return [scraped_product_model_to_entity(model) for model in models.all()]

    async def get_identity_review(self, review_id: UUID) -> ProductIdentityReview | None:
        model = await self._session.get(ProductIdentityReviewModel, review_id)
        return product_identity_review_model_to_entity(model) if model is not None else None

    async def list_identity_reviews(
        self,
        status: str | None = None,
    ) -> list[ProductIdentityReview]:
        statement = select(ProductIdentityReviewModel).order_by(
            ProductIdentityReviewModel.created_at,
            ProductIdentityReviewModel.id,
        )
        if status is not None:
            statement = statement.where(ProductIdentityReviewModel.estado == status)
        models = await self._session.scalars(statement)
        return [product_identity_review_model_to_entity(model) for model in models.all()]

    async def save_identity_review(
        self,
        review: ProductIdentityReview,
    ) -> ProductIdentityReview:
        model = await self._session.get(ProductIdentityReviewModel, review.id)
        if model is None:
            model = product_identity_review_entity_to_model(review)
            self._session.add(model)
        else:
            model.tipo = review.review_type
            model.producto_origen_id = review.source_product_id
            model.producto_destino_id = review.target_product_id
            model.valor_evidencia = review.evidence_value
            model.confianza = review.confidence
            model.justificacion = review.rationale
            model.estado = review.status
            model.nota_decision = review.decision_note
            model.decided_at = review.decided_at
        await self._session.flush()
        return product_identity_review_model_to_entity(model)
