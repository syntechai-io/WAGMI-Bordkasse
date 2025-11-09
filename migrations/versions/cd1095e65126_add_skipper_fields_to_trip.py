"""add_skipper_fields_to_trip

Revision ID: cd1095e65126
Revises: 874a73ef7d1c
Create Date: 2025-11-09 16:16:09.231243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd1095e65126'
down_revision: Union[str, Sequence[str], None] = '874a73ef7d1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('trips', sa.Column('skipper_name', sa.String(length=100), nullable=True))
    op.add_column('trips', sa.Column('skipper_code', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('trips', 'skipper_code')
    op.drop_column('trips', 'skipper_name')
