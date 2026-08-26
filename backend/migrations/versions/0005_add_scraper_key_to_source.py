"""add scraper key to source

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-10 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scraping_source",
        sa.Column("scraper_key", sa.String(length=32), server_default="jumbo", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("scraping_source", "scraper_key")
