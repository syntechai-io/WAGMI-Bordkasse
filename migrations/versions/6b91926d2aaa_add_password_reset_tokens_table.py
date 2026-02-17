"""add_password_reset_tokens_table

Revision ID: 6b91926d2aaa
Revises: 0cbbd4ebb491
Create Date: 2026-02-17 17:33:06.961761

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6b91926d2aaa'
down_revision: Union[str, Sequence[str], None] = '0cbbd4ebb491'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('new_users.id'), nullable=False, index=True),
        sa.Column('token_hash', sa.String(128), nullable=False, unique=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('request_ip', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('password_reset_tokens')
