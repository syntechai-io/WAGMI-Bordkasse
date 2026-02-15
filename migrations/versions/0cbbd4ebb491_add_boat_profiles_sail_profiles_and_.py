"""add_boat_profiles_sail_profiles_and_sail_change_columns

Revision ID: 0cbbd4ebb491
Revises: 1350e71f86fe
Create Date: 2026-02-15 19:22:10.236585

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0cbbd4ebb491'
down_revision: Union[str, Sequence[str], None] = '1350e71f86fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name):
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :t)"
    ), {"t": table_name})
    return result.scalar()


def column_exists(table_name, column_name):
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c)"
    ), {"t": table_name, "c": column_name})
    return result.scalar()


def upgrade() -> None:
    if not table_exists('boat_profiles'):
        op.create_table('boat_profiles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('account_id', sa.Integer(), nullable=False),
            sa.Column('boat_name', sa.String(length=100), nullable=False, server_default='My Boat'),
            sa.Column('boat_name_is_default', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('home_port_name', sa.String(length=100), nullable=True),
            sa.Column('home_port_lat', sa.Float(), nullable=True),
            sa.Column('home_port_lon', sa.Float(), nullable=True),
            sa.Column('boat_make', sa.String(length=100), nullable=True),
            sa.Column('boat_model', sa.String(length=100), nullable=True),
            sa.Column('boat_year', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('account_id')
        )
        op.create_index(op.f('ix_boat_profiles_account_id'), 'boat_profiles', ['account_id'], unique=True)
        op.create_index(op.f('ix_boat_profiles_id'), 'boat_profiles', ['id'], unique=False)

    if not table_exists('sail_profiles'):
        op.create_table('sail_profiles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('boat_profile_id', sa.Integer(), nullable=False),
            sa.Column('main_type', sa.String(length=20), nullable=False, server_default='FURLING'),
            sa.Column('main_reef_levels', sa.Integer(), nullable=False, server_default=sa.text('2')),
            sa.Column('headsail_genoa', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('headsail_jib', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('headsail_furling', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('has_code0', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('has_gennaker', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('has_spinnaker', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['boat_profile_id'], ['boat_profiles.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('boat_profile_id')
        )
        op.create_index(op.f('ix_sail_profiles_boat_profile_id'), 'sail_profiles', ['boat_profile_id'], unique=True)
        op.create_index(op.f('ix_sail_profiles_id'), 'sail_profiles', ['id'], unique=False)

    for col_name, col_type in [
        ('main_reef_level', sa.Integer()),
        ('headsail_type', sa.String(length=10)),
        ('headsail_furl_percent', sa.Integer()),
        ('extra_sail', sa.String(length=10)),
    ]:
        if not column_exists('logbook_entries', col_name):
            op.add_column('logbook_entries', sa.Column(col_name, col_type, nullable=True))

    op.execute("""
        INSERT INTO boat_profiles (account_id, boat_name, boat_name_is_default, home_port_name, created_at, updated_at)
        VALUES (1, 'WAGMI', false, 'Fredericia', now(), now())
        ON CONFLICT (account_id) DO NOTHING
    """)
    op.execute("""
        INSERT INTO sail_profiles (boat_profile_id, main_type, main_reef_levels, headsail_genoa, headsail_jib, headsail_furling, has_code0, has_gennaker, has_spinnaker, created_at, updated_at)
        SELECT id, 'FURLING', 2, true, false, true, false, false, false, now(), now()
        FROM boat_profiles WHERE account_id = 1
        ON CONFLICT (boat_profile_id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_column('logbook_entries', 'extra_sail')
    op.drop_column('logbook_entries', 'headsail_furl_percent')
    op.drop_column('logbook_entries', 'headsail_type')
    op.drop_column('logbook_entries', 'main_reef_level')
    op.drop_index(op.f('ix_sail_profiles_id'), table_name='sail_profiles')
    op.drop_index(op.f('ix_sail_profiles_boat_profile_id'), table_name='sail_profiles')
    op.drop_table('sail_profiles')
    op.drop_index(op.f('ix_boat_profiles_id'), table_name='boat_profiles')
    op.drop_index(op.f('ix_boat_profiles_account_id'), table_name='boat_profiles')
    op.drop_table('boat_profiles')
