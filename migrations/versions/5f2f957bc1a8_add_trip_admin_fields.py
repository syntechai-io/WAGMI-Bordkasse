"""add_trip_admin_fields

Revision ID: 5f2f957bc1a8
Revises: 952a360be11b
Create Date: 2025-11-01 14:18:56.008529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f2f957bc1a8'
down_revision: Union[str, Sequence[str], None] = '952a360be11b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add trip admin password fields to trips table
    op.add_column('trips', sa.Column('trip_admin_password_hash', sa.String(length=200), nullable=True))
    op.add_column('trips', sa.Column('crew_password_hash', sa.String(length=200), nullable=True))
    
    # Add is_trip_admin flag to crew_members table
    op.add_column('crew_members', sa.Column('is_trip_admin', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns in reverse order
    op.drop_column('crew_members', 'is_trip_admin')
    op.drop_column('trips', 'crew_password_hash')
    op.drop_column('trips', 'trip_admin_password_hash')
