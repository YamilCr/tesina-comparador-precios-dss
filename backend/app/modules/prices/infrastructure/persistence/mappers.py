"""Conversores entre modelos SQLAlchemy y entidades de dominio de precios."""

from app.modules.prices.domain.entities import Price

from .sqlalchemy_models import PriceModel


def price_model_to_entity(model: PriceModel) -> Price:
    """Convierte un modelo de precio en una entidad de dominio."""
    return Price(
        id=model.id,
        product_source_id=model.producto_fuente_id,
        branch_id=model.sucursal_id,
        amount=model.precio,
        currency=model.moneda,
        observed_at=model.fecha_relevamiento,
        available=model.disponible,
        promotion=model.promocion,
        created_at=model.created_at,
    )


def price_entity_to_model(entity: Price) -> PriceModel:
    """Convierte una entidad de precio en un modelo SQLAlchemy nuevo."""
    model = PriceModel(
        id=entity.id,
        producto_fuente_id=entity.product_source_id,
        sucursal_id=entity.branch_id,
        precio=entity.amount,
        moneda=entity.currency,
        fecha_relevamiento=entity.observed_at,
        disponible=entity.available,
        promocion=entity.promotion,
    )
    if entity.created_at is not None:
        model.created_at = entity.created_at
    return model
