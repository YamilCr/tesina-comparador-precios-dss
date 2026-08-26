"""add product identity review queue

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "revision_identidad_producto",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("producto_origen_id", sa.Uuid(), nullable=False),
        sa.Column("producto_destino_id", sa.Uuid(), nullable=False),
        sa.Column("valor_evidencia", sa.String(length=500), nullable=False),
        sa.Column("confianza", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("justificacion", sa.String(length=1000), nullable=False),
        sa.Column("estado", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("nota_decision", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "tipo IN ('gtin_conflict', 'semantic_alias')",
            name="ck_revision_identidad_tipo",
        ),
        sa.CheckConstraint(
            "estado IN ('pending', 'approved', 'rejected')",
            name="ck_revision_identidad_estado",
        ),
        sa.CheckConstraint(
            "confianza BETWEEN 0 AND 1",
            name="ck_revision_identidad_confianza",
        ),
        sa.ForeignKeyConstraint(["producto_destino_id"], ["producto.id"]),
        sa.ForeignKeyConstraint(["producto_origen_id"], ["producto.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tipo",
            "producto_origen_id",
            "producto_destino_id",
            "valor_evidencia",
            name="uq_revision_identidad_propuesta",
        ),
    )
    op.create_index(
        "ix_revision_identidad_estado",
        "revision_identidad_producto",
        ["estado"],
    )
    op.create_index(
        "ix_revision_identidad_origen",
        "revision_identidad_producto",
        ["producto_origen_id"],
    )
    op.create_index(
        "ix_revision_identidad_destino",
        "revision_identidad_producto",
        ["producto_destino_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_revision_identidad_destino", table_name="revision_identidad_producto")
    op.drop_index("ix_revision_identidad_origen", table_name="revision_identidad_producto")
    op.drop_index("ix_revision_identidad_estado", table_name="revision_identidad_producto")
    op.drop_table("revision_identidad_producto")
