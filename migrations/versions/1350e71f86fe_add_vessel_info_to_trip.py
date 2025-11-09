"""add_vessel_info_to_trip

Revision ID: 1350e71f86fe
Revises: cd1095e65126
Create Date: 2025-11-09 17:29:30.062692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1350e71f86fe'
down_revision: Union[str, Sequence[str], None] = 'cd1095e65126'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('trips', sa.Column('home_port', sa.String(length=100), nullable=True))
    op.add_column('trips', sa.Column('call_sign', sa.String(length=50), nullable=True))
    op.add_column('trips', sa.Column('imo_mmsi', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('trips', 'imo_mmsi')
    op.drop_column('trips', 'call_sign')
    op.drop_column('trips', 'home_port')
