"""Schemas HTTP para el motor de decisión DSS."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.basket.interfaces.http.schemas import BasketLineRequest


class RankingWeightsRequest(BaseModel):
    """Pesos configurables para el ranking multicriterio."""

    price: Decimal = Decimal("0.6")
    distance: Decimal = Decimal("0.3")
    saving: Decimal = Decimal("0.1")

    @model_validator(mode="after")
    def validate_weights(self) -> "RankingWeightsRequest":
        """Valida que los pesos sean no negativos y sumen uno."""
        weights = (self.price, self.distance, self.saving)
        if any(weight < Decimal("0") for weight in weights):
            raise ValueError("Los pesos no pueden ser negativos.")
        if sum(weights, Decimal("0")) != Decimal("1"):
            raise ValueError("Los pesos deben sumar exactamente 1.")
        return self


class RankingRequest(BaseModel):
    """Solicitud HTTP para calcular un ranking DSS."""

    items: list[BasketLineRequest] = Field(min_length=1, max_length=100)
    origin_latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    origin_longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    city_id: UUID | None = None
    branch_ids: list[UUID] | None = None
    weights: RankingWeightsRequest = Field(default_factory=RankingWeightsRequest)

    @model_validator(mode="after")
    def validate_request(self) -> "RankingRequest":
        """Valida origen geográfico y productos duplicados."""
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Cada producto debe aparecer una sola vez en la canasta.")

        has_coordinates = self.origin_latitude is not None or self.origin_longitude is not None
        if has_coordinates and (self.origin_latitude is None or self.origin_longitude is None):
            raise ValueError("Debe enviar origin_latitude y origin_longitude juntas.")
        if not has_coordinates and self.city_id is None:
            raise ValueError("Debe enviar coordenadas de origen o city_id.")
        return self
