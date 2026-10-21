"""add briefings table

Revision ID: 0003_add_briefings_table
Revises: 0002_add_plans_table
Create Date: 2026-10-21 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0003_add_briefings_table'
down_revision: Union[str, None] = '0002_add_plans_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'briefings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_briefing_date')
    )
    op.create_index(op.f('ix_briefings_id'), 'briefings', ['id'], unique=False)
    op.create_index(op.f('ix_briefings_user_id'), 'briefings', ['user_id'], unique=False)
    op.create_index(op.f('ix_briefings_date'), 'briefings', ['date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_briefings_date'), table_name='briefings')
    op.drop_index(op.f('ix_briefings_user_id'), table_name='briefings')
    op.drop_index(op.f('ix_briefings_id'), table_name='briefings')
    op.drop_table('briefings')
