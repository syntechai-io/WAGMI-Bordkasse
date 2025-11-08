"""Add logbook Phase A fields - navigation, weather, engine, sails, events, append-only

Revision ID: 1bd70c249026
Revises: f74443d46c75
Create Date: 2025-11-08 19:08:55.303448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1bd70c249026'
down_revision: Union[str, Sequence[str], None] = 'f74443d46c75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Only add new logbook columns - preserve existing tables
    op.add_column('logbook_entries', sa.Column('cog_deg', sa.Integer(), nullable=True))
    op.add_column('logbook_entries', sa.Column('sog_kn', sa.Float(), nullable=True))
    op.add_column('logbook_entries', sa.Column('log_kn', sa.Float(), nullable=True))
    op.add_column('logbook_entries', sa.Column('dist_day_nm', sa.Float(), nullable=True))
    op.add_column('logbook_entries', sa.Column('pressure_hpa', sa.Integer(), nullable=True))
    op.add_column('logbook_entries', sa.Column('pressure_trend', sa.String(length=20), nullable=True))
    op.add_column('logbook_entries', sa.Column('weather_source', sa.String(length=100), nullable=True))
    op.add_column('logbook_entries', sa.Column('engine_on', sa.Boolean(), nullable=True))
    op.add_column('logbook_entries', sa.Column('engine_on_time', sa.DateTime(), nullable=True))
    op.add_column('logbook_entries', sa.Column('engine_off_time', sa.DateTime(), nullable=True))
    op.add_column('logbook_entries', sa.Column('eng_hours_total', sa.Float(), nullable=True))
    op.add_column('logbook_entries', sa.Column('fuel_level_l', sa.Float(), nullable=True))
    op.add_column('logbook_entries', sa.Column('main_furl_pct', sa.Integer(), nullable=True))
    op.add_column('logbook_entries', sa.Column('headsail', sa.String(length=100), nullable=True))
    op.add_column('logbook_entries', sa.Column('sail_action', sa.String(length=200), nullable=True))
    op.add_column('logbook_entries', sa.Column('event_category', sa.String(length=100), nullable=True))
    op.add_column('logbook_entries', sa.Column('event_details', sa.Text(), nullable=True))
    op.add_column('logbook_entries', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.add_column('logbook_entries', sa.Column('is_superseded', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('logbook_entries', sa.Column('change_note', sa.Text(), nullable=True))
    op.create_index(op.f('ix_logbook_entries_parent_id'), 'logbook_entries', ['parent_id'], unique=False)
    op.create_foreign_key('fk_logbook_entries_parent', 'logbook_entries', 'logbook_entries', ['parent_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove logbook Phase A columns
    op.drop_constraint('fk_logbook_entries_parent', 'logbook_entries', type_='foreignkey')
    op.drop_index(op.f('ix_logbook_entries_parent_id'), table_name='logbook_entries')
    op.drop_column('logbook_entries', 'change_note')
    op.drop_column('logbook_entries', 'is_superseded')
    op.drop_column('logbook_entries', 'parent_id')
    op.drop_column('logbook_entries', 'event_details')
    op.drop_column('logbook_entries', 'event_category')
    op.drop_column('logbook_entries', 'sail_action')
    op.drop_column('logbook_entries', 'headsail')
    op.drop_column('logbook_entries', 'main_furl_pct')
    op.drop_column('logbook_entries', 'fuel_level_l')
    op.drop_column('logbook_entries', 'eng_hours_total')
    op.drop_column('logbook_entries', 'engine_off_time')
    op.drop_column('logbook_entries', 'engine_on_time')
    op.drop_column('logbook_entries', 'engine_on')
    op.drop_column('logbook_entries', 'weather_source')
    op.drop_column('logbook_entries', 'pressure_trend')
    op.drop_column('logbook_entries', 'pressure_hpa')
    op.drop_column('logbook_entries', 'dist_day_nm')
    op.drop_column('logbook_entries', 'log_kn')
    op.drop_column('logbook_entries', 'sog_kn')
    op.drop_column('logbook_entries', 'cog_deg')
