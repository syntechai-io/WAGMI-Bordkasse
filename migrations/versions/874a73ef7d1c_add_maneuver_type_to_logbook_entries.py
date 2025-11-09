"""Add maneuver_type to logbook_entries

Revision ID: 874a73ef7d1c
Revises: a753fc13a619
Create Date: 2025-11-09 08:25:51.617810

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '874a73ef7d1c'
down_revision: Union[str, Sequence[str], None] = 'a753fc13a619'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('logbook_entries', sa.Column('maneuver_type', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('logbook_entries', 'maneuver_type')
