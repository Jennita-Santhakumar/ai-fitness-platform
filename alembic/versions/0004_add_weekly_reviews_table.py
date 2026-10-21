"""add weekly reviews table

Revision ID: 0004_add_weekly_reviews_table
Revises: 0003_add_briefings_table
Create Date: 2026-10-21 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0004_add_weekly_reviews_table'
down_revision: Union[str, None] = '0003_add_briefings_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'weekly_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('total_sessions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_volume', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.Column('suggestions', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'start_date', 'end_date', name='uq_user_weekly_review_period')
    )
    op.create_index(op.f('ix_weekly_reviews_id'), 'weekly_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_weekly_reviews_user_id'), 'weekly_reviews', ['user_id'], unique=False)
    op.create_index(op.f('ix_weekly_reviews_end_date'), 'weekly_reviews', ['end_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_weekly_reviews_end_date'), table_name='weekly_reviews')
    op.drop_index(op.f('ix_weekly_reviews_user_id'), table_name='weekly_reviews')
    op.drop_index(op.f('ix_weekly_reviews_id'), table_name='weekly_reviews')
    op.drop_table('weekly_reviews')
