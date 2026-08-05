"""enable rls on all tables

Revision ID: f42b47f536d3
Revises: a4970af3b658
Create Date: 2026-08-05 05:47:57.966937

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f42b47f536d3'
down_revision: Union[str, Sequence[str], None] = 'a4970af3b658'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("datasets", "analysis_runs", "agent_outputs", "insights")


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # postgres is the role the backend connects as (DATABASE_URL) — the
        # only role that ever touches these tables. No policy is created
        # for anon/public, so Supabase's client-side API/anon key gets zero
        # access; that's the actual fix, this policy just keeps the
        # backend working.
        op.execute(
            f"""
            CREATE POLICY {table}_postgres_full_access ON {table}
            FOR ALL
            TO postgres
            USING (true)
            WITH CHECK (true)
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_postgres_full_access ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
