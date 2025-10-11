"""add_logbook_tables

Revision ID: 215ebd043f3c
Revises: f8d029a73997
Create Date: 2025-10-11 20:49:20.932675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '215ebd043f3c'
down_revision: Union[str, Sequence[str], None] = 'f8d029a73997'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create sea_state enum using raw SQL to handle existing enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE seastateenum AS ENUM ('calm', 'slight', 'moderate', 'rough', 'very_rough', 'high');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create logbook_entries table
    op.create_table(
        'logbook_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('entry_date', sa.DateTime(), nullable=False),
        sa.Column('entry_date_utc', sa.DateTime(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('wind_direction', sa.String(length=20), nullable=True),
        sa.Column('wind_strength', sa.String(length=50), nullable=True),
        sa.Column('visibility', sa.String(length=50), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('sail_plan', sa.String(length=200), nullable=True),
        sa.Column('engine_hours', sa.Float(), nullable=True),
        sa.Column('departure', sa.String(length=100), nullable=True),
        sa.Column('destination', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('safety_checks_completed', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Add sea_state column separately
    op.execute("""
        ALTER TABLE logbook_entries 
        ADD COLUMN sea_state seastateenum;
    """)
    op.create_index(op.f('ix_logbook_entries_entry_date'), 'logbook_entries', ['entry_date'], unique=False)
    op.create_index(op.f('ix_logbook_entries_id'), 'logbook_entries', ['id'], unique=False)
    op.create_index(op.f('ix_logbook_entries_trip_id'), 'logbook_entries', ['trip_id'], unique=False)
    
    # Create logbook_photos table
    op.create_table(
        'logbook_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('stored_filename', sa.String(length=100), nullable=False),
        sa.Column('original_name', sa.String(length=200), nullable=False),
        sa.Column('caption', sa.String(length=500), nullable=True),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['entry_id'], ['logbook_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_logbook_photos_entry_id'), 'logbook_photos', ['entry_id'], unique=False)
    op.create_index(op.f('ix_logbook_photos_id'), 'logbook_photos', ['id'], unique=False)
    
    # Create crew_on_watch table
    op.create_table(
        'crew_on_watch',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['entry_id'], ['logbook_entries.id'], ),
        sa.ForeignKeyConstraint(['member_id'], ['crew_members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crew_on_watch_entry_id'), 'crew_on_watch', ['entry_id'], unique=False)
    op.create_index(op.f('ix_crew_on_watch_id'), 'crew_on_watch', ['id'], unique=False)
    op.create_index(op.f('ix_crew_on_watch_member_id'), 'crew_on_watch', ['member_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_crew_on_watch_member_id'), table_name='crew_on_watch')
    op.drop_index(op.f('ix_crew_on_watch_id'), table_name='crew_on_watch')
    op.drop_index(op.f('ix_crew_on_watch_entry_id'), table_name='crew_on_watch')
    op.drop_table('crew_on_watch')
    
    op.drop_index(op.f('ix_logbook_photos_id'), table_name='logbook_photos')
    op.drop_index(op.f('ix_logbook_photos_entry_id'), table_name='logbook_photos')
    op.drop_table('logbook_photos')
    
    op.drop_index(op.f('ix_logbook_entries_trip_id'), table_name='logbook_entries')
    op.drop_index(op.f('ix_logbook_entries_id'), table_name='logbook_entries')
    op.drop_index(op.f('ix_logbook_entries_entry_date'), table_name='logbook_entries')
    op.drop_table('logbook_entries')
    
    sa.Enum('calm', 'slight', 'moderate', 'rough', 'very_rough', 'high', 
            name='seastateenum').drop(op.get_bind())
