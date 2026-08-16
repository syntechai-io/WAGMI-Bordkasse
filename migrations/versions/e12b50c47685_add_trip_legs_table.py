"""add_trip_legs_table

Revision ID: e12b50c47685
Revises: 6b91926d2aaa
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e12b50c47685'
down_revision: Union[str, Sequence[str], None] = '6b91926d2aaa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'trip_legs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=True),
        sa.Column('departure_port', sa.String(length=100), nullable=True),
        sa.Column('destination_port', sa.String(length=100), nullable=True),
        sa.Column('planned_start', sa.Date(), nullable=True),
        sa.Column('planned_end', sa.Date(), nullable=True),
        sa.Column('actual_start', sa.DateTime(), nullable=True),
        sa.Column('actual_end', sa.DateTime(), nullable=True),
        sa.Column('distance_planned_nm', sa.Float(), nullable=True),
        sa.Column('distance_actual_nm', sa.Float(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trip_legs_trip_id', 'trip_legs', ['trip_id'])
    op.create_index(op.f('ix_trip_legs_id'), 'trip_legs', ['id'], unique=False)

    op.add_column('logbook_entries', sa.Column('leg_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_logbook_entries_leg_id'), 'logbook_entries', ['leg_id'], unique=False)
    op.create_foreign_key('fk_logbook_entries_leg_id_trip_legs', 'logbook_entries', 'trip_legs', ['leg_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_logbook_entries_leg_id_trip_legs', 'logbook_entries', type_='foreignkey')
    op.drop_index(op.f('ix_logbook_entries_leg_id'), table_name='logbook_entries')
    op.drop_column('logbook_entries', 'leg_id')

    op.drop_index(op.f('ix_trip_legs_id'), table_name='trip_legs')
    op.drop_index('ix_trip_legs_trip_id', table_name='trip_legs')
    op.drop_table('trip_legs')
