"""add plans table

Revision ID: 0002_add_plans_table
Revises: 0001_initial_tables
Create Date: 2026-10-17 23:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_add_plans_table'
down_revision: Union[str, None] = '0001_initial_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('inputs', sa.JSON(), nullable=False),
        sa.Column('plan', sa.JSON(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plans_id'), 'plans', ['id'], unique=False)
    op.create_index(op.f('ix_plans_user_id'), 'plans', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_plans_user_id'), table_name='plans')
    op.drop_index(op.f('ix_plans_id'), table_name='plans')
    op.drop_table('plans')
