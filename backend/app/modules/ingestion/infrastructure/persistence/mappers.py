"""Mappings between ingestion SQLAlchemy models and domain entities."""

from datetime import UTC, datetime

from app.modules.ingestion.domain.entities import ScrapedProduct, ScrapingRun, ScrapingSource

from .sqlalchemy_models import ScrapedProductModel, ScrapingRunModel, ScrapingSourceModel


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
