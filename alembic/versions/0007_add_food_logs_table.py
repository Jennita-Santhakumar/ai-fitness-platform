"""Alembic migration: add food_logs table (Day 25)."""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "food_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fdc_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("grams", sa.Float(), nullable=False),
        sa.Column("calories", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("protein", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("carbs", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fat", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_food_logs_id", "food_logs", ["id"])
    op.create_index("ix_food_logs_user_id", "food_logs", ["user_id"])
    op.create_index("ix_food_logs_date", "food_logs", ["date"])
    op.create_index("ix_food_logs_fdc_id", "food_logs", ["fdc_id"])


def downgrade() -> None:
    op.drop_index("ix_food_logs_fdc_id", table_name="food_logs")
    op.drop_index("ix_food_logs_date", table_name="food_logs")
    op.drop_index("ix_food_logs_user_id", table_name="food_logs")
    op.drop_index("ix_food_logs_id", table_name="food_logs")
    op.drop_table("food_logs")
