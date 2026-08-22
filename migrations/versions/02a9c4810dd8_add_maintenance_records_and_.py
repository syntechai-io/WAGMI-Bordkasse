"""add_maintenance_records_and_maintenance_attachments

Revision ID: 02a9c4810dd8
Revises: e12b50c47685
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '02a9c4810dd8'
down_revision: Union[str, Sequence[str], None] = 'e12b50c47685'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name):
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :t)"
    ), {"t": table_name})
    return result.scalar()


def upgrade() -> None:
    if not table_exists('maintenance_records'):
        op.create_table(
            'maintenance_records',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('account_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('category', sa.String(length=20), nullable=False, server_default='service'),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='resolved'),
            sa.Column('performed_at', sa.Date(), nullable=False),
            sa.Column('engine_hours_at', sa.Float(), nullable=True),
            sa.Column('nm_at', sa.Float(), nullable=True),
            sa.Column('vendor', sa.String(length=150), nullable=True),
            sa.Column('cost_amount', sa.Float(), nullable=True),
            # Reuses the existing 'currency' Postgres enum type (created by
            # be5598531949) rather than creating a second one — this must
            # stay in sync with models.py's cost_currency = Column(SQLEnum(Currency)).
            sa.Column('cost_currency', sa.Enum('EUR', 'DKK', 'SEK', 'GBP', name='currency', create_type=False), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('next_due_date', sa.Date(), nullable=True),
            sa.Column('next_due_engine_hours', sa.Float(), nullable=True),
            sa.Column('next_due_nm', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_maintenance_records_account_id'), 'maintenance_records', ['account_id'], unique=False)
        op.create_index(op.f('ix_maintenance_records_id'), 'maintenance_records', ['id'], unique=False)

    if not table_exists('maintenance_attachments'):
        op.create_table(
            'maintenance_attachments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('record_id', sa.Integer(), nullable=False),
            sa.Column('stored_filename', sa.String(length=100), nullable=False),
            sa.Column('original_name', sa.String(length=200), nullable=False),
            sa.Column('content_type', sa.String(length=50), nullable=False),
            sa.Column('size_bytes', sa.Integer(), nullable=False),
            sa.Column('uploaded_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['record_id'], ['maintenance_records.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_maintenance_attachments_record_id'), 'maintenance_attachments', ['record_id'], unique=False)
        op.create_index(op.f('ix_maintenance_attachments_id'), 'maintenance_attachments', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_maintenance_attachments_id'), table_name='maintenance_attachments')
    op.drop_index(op.f('ix_maintenance_attachments_record_id'), table_name='maintenance_attachments')
    op.drop_table('maintenance_attachments')

    op.drop_index(op.f('ix_maintenance_records_id'), table_name='maintenance_records')
    op.drop_index(op.f('ix_maintenance_records_account_id'), table_name='maintenance_records')
    op.drop_table('maintenance_records')
