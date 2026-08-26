"""Mappings between ingestion SQLAlchemy models and domain entities."""

from datetime import UTC, datetime

from app.modules.ingestion.domain.entities import (
    ProductIdentityReview,
    ScheduledRefreshExecution,
    ScrapedProduct,
    ScrapingRun,
    ScrapingSchedule,
    ScrapingSource,
)

from .sqlalchemy_models import (
    ProductIdentityReviewModel,
    ScheduledRefreshExecutionModel,
    ScrapedProductModel,
    ScrapingRunModel,
    ScrapingScheduleModel,
    ScrapingSourceModel,
)


def _as_utc(value: datetime) -> datetime:
    """Normalizes SQLite naive timestamps to UTC-aware domain values."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def scraping_source_model_to_entity(model: ScrapingSourceModel) -> ScrapingSource:
    """Maps a configured source model to the domain."""
    return ScrapingSource(
        id=model.id,
        supermarket_id=model.supermercado_id,
        name=model.nombre,
        base_url=model.base_url,
        scraper_key=model.scraper_key,
        branch_id=model.sucursal_id,
        active=model.activo,
        created_at=_as_utc(model.created_at),
    )


def scraping_source_entity_to_model(entity: ScrapingSource) -> ScrapingSourceModel:
    """Maps a new source entity to its SQLAlchemy model."""
    return ScrapingSourceModel(
        id=entity.id,
        supermercado_id=entity.supermarket_id,
        nombre=entity.name,
        base_url=entity.base_url,
        scraper_key=entity.scraper_key,
        sucursal_id=entity.branch_id,
        activo=entity.active,
    )


def scraping_run_model_to_entity(model: ScrapingRunModel) -> ScrapingRun:
    """Maps an audit run model to the domain."""
    return ScrapingRun(
        id=model.id,
        scraping_source_id=model.scraping_source_id,
        status=model.estado,
        started_at=_as_utc(model.iniciado_en),
        finished_at=(
            _as_utc(model.finalizado_en) if model.finalizado_en is not None else None
        ),
        items_scraped=model.items_extraidos,
        items_loaded=model.items_cargados,
        error_message=model.mensaje_error,
    )


def scraping_run_entity_to_model(entity: ScrapingRun) -> ScrapingRunModel:
    """Maps a new audit run entity to its SQLAlchemy model."""
    return ScrapingRunModel(
        id=entity.id,
        scraping_source_id=entity.scraping_source_id,
        estado=entity.status,
        iniciado_en=entity.started_at,
        finalizado_en=entity.finished_at,
        items_extraidos=entity.items_scraped,
        items_cargados=entity.items_loaded,
        mensaje_error=entity.error_message,
    )


def scraping_schedule_model_to_entity(model: ScrapingScheduleModel) -> ScrapingSchedule:
    """Maps an automatic refresh configuration to the domain."""
    return ScrapingSchedule(
        id=model.id,
        scraping_source_id=model.scraping_source_id,
        name=model.name,
        queries=tuple(model.queries),
        city=model.city,
        interval_minutes=model.interval_minutes,
        retry_delay_minutes=model.retry_delay_minutes,
        result_limit=model.result_limit,
        timeout_seconds=model.timeout_seconds,
        enabled=model.enabled,
        next_run_at=_as_utc(model.next_run_at),
        locked_until=_as_utc(model.locked_until) if model.locked_until is not None else None,
        consecutive_failures=model.consecutive_failures,
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
    )


def scraping_schedule_entity_to_model(entity: ScrapingSchedule) -> ScrapingScheduleModel:
    """Maps a new automatic refresh configuration to SQLAlchemy."""
    return ScrapingScheduleModel(
        id=entity.id,
        scraping_source_id=entity.scraping_source_id,
        name=entity.name,
        queries=list(entity.queries),
        city=entity.city,
        interval_minutes=entity.interval_minutes,
        retry_delay_minutes=entity.retry_delay_minutes,
        result_limit=entity.result_limit,
        timeout_seconds=entity.timeout_seconds,
        enabled=entity.enabled,
        next_run_at=entity.next_run_at,
        locked_until=entity.locked_until,
        consecutive_failures=entity.consecutive_failures,
    )


def scheduled_execution_model_to_entity(
    model: ScheduledRefreshExecutionModel,
) -> ScheduledRefreshExecution:
    """Maps one scheduler history row to the domain."""
    return ScheduledRefreshExecution(
        id=model.id,
        schedule_id=model.schedule_id,
        scraping_run_id=model.scraping_run_id,
        status=model.status,
        scheduled_for=_as_utc(model.scheduled_for),
        started_at=_as_utc(model.started_at),
        finished_at=_as_utc(model.finished_at) if model.finished_at is not None else None,
        error_message=model.error_message,
    )


def scheduled_execution_entity_to_model(
    entity: ScheduledRefreshExecution,
) -> ScheduledRefreshExecutionModel:
    """Maps a new scheduler history entity to SQLAlchemy."""
    return ScheduledRefreshExecutionModel(
        id=entity.id,
        schedule_id=entity.schedule_id,
        scraping_run_id=entity.scraping_run_id,
        status=entity.status,
        scheduled_for=entity.scheduled_for,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
        error_message=entity.error_message,
    )


def scraped_product_model_to_entity(model: ScrapedProductModel) -> ScrapedProduct:
    """Maps one staged extracted product to the domain."""
    return ScrapedProduct(
        id=model.id,
        scraping_run_id=model.scraping_run_id,
        raw_payload=model.payload_crudo,
        external_code=model.codigo_externo,
        ean=model.ean,
        name=model.nombre,
        brand=model.marca,
        amount=model.precio,
        presentation=model.presentacion,
        product_url=model.url_producto,
        status=model.estado,
        quality_message=model.mensaje_calidad,
        product_source_id=model.producto_fuente_id,
        price_id=model.precio_id,
        processed_at=_as_utc(model.procesado_en) if model.procesado_en is not None else None,
        created_at=_as_utc(model.created_at),
    )


def scraped_product_entity_to_model(entity: ScrapedProduct) -> ScrapedProductModel:
    """Maps one new staged extracted product to SQLAlchemy."""
    return ScrapedProductModel(
        id=entity.id,
        scraping_run_id=entity.scraping_run_id,
        codigo_externo=entity.external_code,
        ean=entity.ean,
        nombre=entity.name,
        marca=entity.brand,
        precio=entity.amount,
        presentacion=entity.presentation,
        url_producto=entity.product_url,
        payload_crudo=entity.raw_payload,
        estado=entity.status,
        mensaje_calidad=entity.quality_message,
        producto_fuente_id=entity.product_source_id,
        precio_id=entity.price_id,
        procesado_en=entity.processed_at,
    )


def product_identity_review_model_to_entity(
    model: ProductIdentityReviewModel,
) -> ProductIdentityReview:
    return ProductIdentityReview(
        id=model.id,
        review_type=model.tipo,
        source_product_id=model.producto_origen_id,
        target_product_id=model.producto_destino_id,
        evidence_value=model.valor_evidencia,
        confidence=model.confianza,
        rationale=model.justificacion,
        status=model.estado,
        decision_note=model.nota_decision,
        created_at=_as_utc(model.created_at),
        decided_at=_as_utc(model.decided_at) if model.decided_at is not None else None,
    )


def product_identity_review_entity_to_model(
    entity: ProductIdentityReview,
) -> ProductIdentityReviewModel:
    return ProductIdentityReviewModel(
        id=entity.id,
        tipo=entity.review_type,
        producto_origen_id=entity.source_product_id,
        producto_destino_id=entity.target_product_id,
        valor_evidencia=entity.evidence_value,
        confianza=entity.confidence,
        justificacion=entity.rationale,
        estado=entity.status,
        nota_decision=entity.decision_note,
        decided_at=entity.decided_at,
    )
