"""add scraped product staging

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "producto_extraido",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scraping_run_id", sa.Uuid(), nullable=False),
        sa.Column("codigo_externo", sa.String(length=255), nullable=True),
        sa.Column("ean", sa.String(length=255), nullable=True),
        sa.Column("nombre", sa.String(length=500), nullable=True),
        sa.Column("marca", sa.String(length=255), nullable=True),
        sa.Column("precio", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("presentacion", sa.String(length=255), nullable=True),
        sa.Column("url_producto", sa.String(length=2048), nullable=True),
        sa.Column("payload_crudo", sa.JSON(), nullable=False),
        sa.Column("estado", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("mensaje_calidad", sa.String(length=1000), nullable=True),
        sa.Column("producto_fuente_id", sa.Uuid(), nullable=True),
        sa.Column("precio_id", sa.Uuid(), nullable=True),
        sa.Column("procesado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado IN ('pending', 'loaded', 'rejected', 'duplicate', 'unmatched')",
            name="ck_producto_extraido_estado_valido",
        ),
        sa.ForeignKeyConstraint(["precio_id"], ["precio.id"]),
        sa.ForeignKeyConstraint(["producto_fuente_id"], ["producto_fuente.id"]),
        sa.ForeignKeyConstraint(["scraping_run_id"], ["scraping_run.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_producto_extraido_run_id", "producto_extraido", ["scraping_run_id"])
    op.create_index("ix_producto_extraido_estado", "producto_extraido", ["estado"])
    op.create_index("ix_producto_extraido_codigo_externo", "producto_extraido", ["codigo_externo"])


def downgrade() -> None:
    op.drop_index("ix_producto_extraido_codigo_externo", table_name="producto_extraido")
    op.drop_index("ix_producto_extraido_estado", table_name="producto_extraido")
    op.drop_index("ix_producto_extraido_run_id", table_name="producto_extraido")
    op.drop_table("producto_extraido")
