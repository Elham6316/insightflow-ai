"""create initial tables

Revision ID: a4970af3b658
Revises:
Create Date: 2026-07-24 03:18:29.902687

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a4970af3b658'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')

    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text()),
        sa.Column("row_count", sa.Integer()),
        sa.Column("col_count", sa.Integer()),
        sa.Column("status", sa.Text(), server_default="uploaded"),
        sa.Column("uploaded_at", sa.TIMESTAMP(), server_default=sa.text("now()")),
    )

    op.create_table(
        "analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE")),
        sa.Column("status", sa.Text(), server_default="pending"),
        sa.Column("current_agent", sa.Text()),
        sa.Column("started_at", sa.TIMESTAMP(), server_default=sa.text("now()")),
        sa.Column("finished_at", sa.TIMESTAMP()),
    )

    op.create_table(
        "agent_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE")),
        sa.Column("agent_name", sa.Text(), nullable=False),
        sa.Column("output", postgresql.JSONB()),
        sa.Column("status", sa.Text()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()")),
    )

    op.create_table(
        "insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE")),
        sa.Column("title", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("severity", sa.Text()),
        sa.Column("chart_ref", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("insights")
    op.drop_table("agent_outputs")
    op.drop_table("analysis_runs")
    op.drop_table("datasets")
