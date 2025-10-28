"""make_expense_payer_id_nullable_for_external_charges

Revision ID: 7742d84602f2
Revises: 12a376fa962e
Create Date: 2025-10-28 16:35:26.416307

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7742d84602f2'
down_revision: Union[str, Sequence[str], None] = '12a376fa962e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make payer_id nullable to support external charges
    op.alter_column('expenses', 'payer_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert payer_id to NOT NULL
    # Note: This will fail if there are any expenses with NULL payer_id
    op.alter_column('expenses', 'payer_id',
                    existing_type=sa.Integer(),
                    nullable=False)
