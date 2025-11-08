"""add_watch_leader_to_logbook

Revision ID: a753fc13a619
Revises: 1bd70c249026
Create Date: 2025-11-08 19:35:28.956715

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a753fc13a619'
down_revision: Union[str, Sequence[str], None] = '1bd70c249026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('logbook_entries', sa.Column('watch_leader_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_logbook_entries_watch_leader_id'), 'logbook_entries', ['watch_leader_id'], unique=False)
    op.create_foreign_key('fk_logbook_entries_watch_leader_id_crew_members', 'logbook_entries', 'crew_members', ['watch_leader_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_logbook_entries_watch_leader_id_crew_members', 'logbook_entries', type_='foreignkey')
    op.drop_index(op.f('ix_logbook_entries_watch_leader_id'), table_name='logbook_entries')
    op.drop_column('logbook_entries', 'watch_leader_id')
