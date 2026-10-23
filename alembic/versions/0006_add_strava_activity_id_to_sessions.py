"""Alembic migration: add strava_activity_id to workout_sessions table (Day 21)."""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("strava_activity_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_sessions_strava_activity_id",
        "sessions",
        ["strava_activity_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_sessions_strava_activity_id", table_name="sessions")
    op.drop_column("sessions", "strava_activity_id")
