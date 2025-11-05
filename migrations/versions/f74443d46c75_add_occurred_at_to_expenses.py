"""add_occurred_at_to_expenses

Revision ID: f74443d46c75
Revises: 5f2f957bc1a8
Create Date: 2025-11-05 11:40:01.769970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f74443d46c75'
down_revision: Union[str, Sequence[str], None] = '5f2f957bc1a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add occurred_at column to expenses table."""
    # Add occurred_at column as nullable first
    op.add_column('expenses', sa.Column('occurred_at', sa.DateTime(), nullable=True))
    
    # Populate occurred_at with created_at for existing rows
    op.execute('UPDATE expenses SET occurred_at = created_at WHERE occurred_at IS NULL')
    
    # Make occurred_at non-nullable and add index
    op.alter_column('expenses', 'occurred_at', nullable=False)
    op.create_index(op.f('ix_expenses_occurred_at'), 'expenses', ['occurred_at'], unique=False)


def downgrade() -> None:
    """Remove occurred_at column from expenses table."""
    op.drop_index(op.f('ix_expenses_occurred_at'), table_name='expenses')
    op.drop_column('expenses', 'occurred_at')
