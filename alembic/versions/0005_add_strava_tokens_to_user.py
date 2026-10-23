"""add strava tokens to user

Revision ID: 0005_add_strava_tokens_to_user
Revises: 0004_add_weekly_reviews_table
Create Date: 2026-10-22 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_add_strava_tokens_to_user'
down_revision: Union[str, None] = '0004_add_weekly_reviews_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('strava_athlete_id', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('strava_access_token', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('strava_refresh_token', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('strava_expires_at', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('strava_scope', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'strava_scope')
    op.drop_column('users', 'strava_expires_at')
    op.drop_column('users', 'strava_refresh_token')
    op.drop_column('users', 'strava_access_token')
    op.drop_column('users', 'strava_athlete_id')
