"""Modelos SQLAlchemy para auditoria de scraping e ingesta."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infrastructure.sqlalchemy_base import Base


class ScrapingSourceModel(Base):
    """Mapea la tabla ``scraping_source``."""

    __tablename__ = "scraping_source"
    __table_args__ = (
        UniqueConstraint(
            "supermercado_id",
            "nombre",
            name="uq_scraping_source_supermercado_nombre",
        ),
        Index("ix_scraping_source_supermercado_id", "supermercado_id"),
        Index("ix_scraping_source_nombre", "nombre"),
        Index("ix_scraping_source_activo", "activo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    supermercado_id: Mapped[UUID] = mapped_column(
        ForeignKey("supermercado.id"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    supermarket: Mapped["SupermarketModel"] = relationship(
        "SupermarketModel",
        back_populates="scraping_sources",
    )
    runs: Mapped[list["ScrapingRunModel"]] = relationship(back_populates="source")


class ScrapingRunModel(Base):
    """Mapea la tabla ``scraping_run``."""

    __tablename__ = "scraping_run"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('pending', 'running', 'succeeded', 'failed')",
            name="ck_scraping_run_estado_valido",
        ),
        CheckConstraint(
            "items_extraidos >= 0",
            name="ck_scraping_run_items_extraidos_no_negativo",
        ),
        CheckConstraint(
            "items_cargados >= 0",
            name="ck_scraping_run_items_cargados_no_negativo",
        ),
        CheckConstraint(
            "finalizado_en IS NULL OR finalizado_en >= iniciado_en",
            name="ck_scraping_run_finalizado_despues_inicio",
        ),
        Index("ix_scraping_run_source_id", "scraping_source_id"),
        Index("ix_scraping_run_estado", "estado"),
        Index("ix_scraping_run_iniciado_en", "iniciado_en"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    scraping_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("scraping_source.id"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    iniciado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_extraidos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    items_cargados: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    mensaje_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    source: Mapped[ScrapingSourceModel] = relationship(back_populates="runs")
