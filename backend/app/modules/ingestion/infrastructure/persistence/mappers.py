"""Mappings between ingestion SQLAlchemy models and domain entities."""

from datetime import UTC, datetime

from app.modules.ingestion.domain.entities import ScrapingRun, ScrapingSource

from .sqlalchemy_models import ScrapingRunModel, ScrapingSourceModel


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
