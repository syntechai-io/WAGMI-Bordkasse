"""remove_user_role_column

Revision ID: 047267bd2c49
Revises: 952a360be11b
Create Date: 2025-10-31 22:05:12.597231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '047267bd2c49'
down_revision: Union[str, Sequence[str], None] = '952a360be11b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - drop role column from users table."""
    # Drop role column from users table if it exists (no longer needed, roles are trip-specific)
    # Use raw SQL to check if column exists before dropping
    connection = op.get_bind()
    result = connection.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='role'"
    ))
    if result.fetchone():
        op.drop_column('users', 'role')


def downgrade() -> None:
    """Downgrade schema - re-add role column to users table."""
    # Re-add role column if we need to rollback
    # Note: This will add the column back but not restore the original values
    op.add_column('users', sa.Column('role', sa.String(20), nullable=True))
