"""enable rls on alembic_version

Revision ID: 84cd0f925b74
Revises: f42b47f536d3
Create Date: 2026-08-05 05:57:33.989603

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '84cd0f925b74'
down_revision: Union[str, Sequence[str], None] = 'f42b47f536d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "alembic_version"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {TABLE}_postgres_full_access ON {TABLE}
        FOR ALL
        TO postgres
        USING (true)
        WITH CHECK (true)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_postgres_full_access ON {TABLE}")
    op.execute(f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY")
