"""add configurable scraping scheduler and execution history

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-24 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scraping_schedule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scraping_source_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("queries", sa.JSON(), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("retry_delay_minutes", sa.Integer(), nullable=False),
        sa.Column("result_limit", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "interval_minutes BETWEEN 1 AND 10080",
            name="ck_scraping_schedule_interval",
        ),
        sa.CheckConstraint(
            "retry_delay_minutes BETWEEN 1 AND 1440",
            name="ck_scraping_schedule_retry_delay",
        ),
        sa.CheckConstraint(
            "result_limit BETWEEN 1 AND 20",
            name="ck_scraping_schedule_result_limit",
        ),
        sa.CheckConstraint(
            "timeout_seconds BETWEEN 1 AND 300",
            name="ck_scraping_schedule_timeout",
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_scraping_schedule_failures_nonnegative",
        ),
        sa.ForeignKeyConstraint(["scraping_source_id"], ["scraping_source.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scraping_source_id", name="uq_scraping_schedule_source"),
    )
    op.create_index(
        "ix_scraping_schedule_enabled_next_run",
        "scraping_schedule",
        ["enabled", "next_run_at"],
    )
    op.create_index(
        "ix_scraping_schedule_locked_until",
        "scraping_schedule",
        ["locked_until"],
    )

    op.create_table(
        "scheduled_refresh_execution",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=False),
        sa.Column("scraping_run_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="running", nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_scheduled_refresh_execution_status",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_scheduled_refresh_execution_finished_after_start",
        ),
        sa.ForeignKeyConstraint(["schedule_id"], ["scraping_schedule.id"]),
        sa.ForeignKeyConstraint(["scraping_run_id"], ["scraping_run.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scraping_run_id", name="uq_scheduled_refresh_execution_run"),
    )
    op.create_index(
        "ix_scheduled_refresh_execution_schedule",
        "scheduled_refresh_execution",
        ["schedule_id"],
    )
    op.create_index(
        "ix_scheduled_refresh_execution_status",
        "scheduled_refresh_execution",
        ["status"],
    )
    op.create_index(
        "ix_scheduled_refresh_execution_started_at",
        "scheduled_refresh_execution",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduled_refresh_execution_started_at",
        table_name="scheduled_refresh_execution",
    )
    op.drop_index(
        "ix_scheduled_refresh_execution_status",
        table_name="scheduled_refresh_execution",
    )
    op.drop_index(
        "ix_scheduled_refresh_execution_schedule",
        table_name="scheduled_refresh_execution",
    )
    op.drop_table("scheduled_refresh_execution")
    op.drop_index("ix_scraping_schedule_locked_until", table_name="scraping_schedule")
    op.drop_index("ix_scraping_schedule_enabled_next_run", table_name="scraping_schedule")
    op.drop_table("scraping_schedule")
