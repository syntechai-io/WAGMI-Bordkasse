"""add_crew_groups_for_settlement

Revision ID: 952a360be11b
Revises: 7742d84602f2
Create Date: 2025-10-28 18:05:54.181976

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '952a360be11b'
down_revision: Union[str, Sequence[str], None] = '7742d84602f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create crew_groups table
    op.create_table(
        'crew_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('representative_member_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['representative_member_id'], ['crew_members.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trip_id', 'name', name='uq_crew_groups_trip_name')
    )
    op.create_index('ix_crew_groups_trip_id', 'crew_groups', ['trip_id'])
    op.create_index('ix_crew_groups_representative', 'crew_groups', ['representative_member_id'])
    
    # Create crew_group_members table
    op.create_table(
        'crew_group_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['crew_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['crew_members.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'member_id', name='uq_crew_group_members_group_member')
    )
    op.create_index('ix_crew_group_members_group_id', 'crew_group_members', ['group_id'])
    op.create_index('ix_crew_group_members_member_id', 'crew_group_members', ['member_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_crew_group_members_member_id', table_name='crew_group_members')
    op.drop_index('ix_crew_group_members_group_id', table_name='crew_group_members')
    op.drop_table('crew_group_members')
    
    op.drop_index('ix_crew_groups_representative', table_name='crew_groups')
    op.drop_index('ix_crew_groups_trip_id', table_name='crew_groups')
    op.drop_table('crew_groups')
