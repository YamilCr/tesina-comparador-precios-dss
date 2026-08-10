"""add scraping source branch target

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("scraping_source") as batch_op:
        batch_op.add_column(sa.Column("sucursal_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_scraping_source_sucursal_id",
            "sucursal",
            ["sucursal_id"],
            ["id"],
        )
        batch_op.create_index("ix_scraping_source_sucursal_id", ["sucursal_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("scraping_source") as batch_op:
        batch_op.drop_index("ix_scraping_source_sucursal_id")
        batch_op.drop_constraint("fk_scraping_source_sucursal_id", type_="foreignkey")
        batch_op.drop_column("sucursal_id")
