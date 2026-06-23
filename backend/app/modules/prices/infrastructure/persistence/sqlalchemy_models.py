"""Modelo SQLAlchemy para el historial de precios relevados."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infrastructure.sqlalchemy_base import Base


class PriceModel(Base):
    """Mapea la tabla ``precio`` del DER."""

    __tablename__ = "precio"
    __table_args__ = (
        CheckConstraint("precio >= 0", name="ck_precio_valor_no_negativo"),
        CheckConstraint(
            "length(trim(moneda)) > 0",
            name="ck_precio_moneda_no_vacia",
        ),
        Index("ix_precio_producto_fuente_id", "producto_fuente_id"),
        Index("ix_precio_sucursal_id", "sucursal_id"),
        Index("ix_precio_fecha_relevamiento", "fecha_relevamiento"),
        Index("ix_precio_disponible", "disponible"),
        Index("ix_precio_promocion", "promocion"),
        Index(
            "ix_precio_producto_fuente_sucursal_fecha",
            "producto_fuente_id",
            "sucursal_id",
            "fecha_relevamiento",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    producto_fuente_id: Mapped[UUID] = mapped_column(
        ForeignKey("producto_fuente.id"),
        nullable=False,
    )
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursal.id"), nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(8), nullable=False, default="ARS", server_default="ARS")
    fecha_relevamiento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disponible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    promocion: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    product_source: Mapped["ProductSourceModel"] = relationship(
        "ProductSourceModel",
        back_populates="prices",
    )
    branch: Mapped["BranchModel"] = relationship("BranchModel", back_populates="prices")

    # El supermercado de producto_fuente debe coincidir con el de sucursal.
    # Esta regla se validará en un caso de uso o repositorio futuro.
