"""Add DailyCheckIn model for multi-day event tracking

Revision ID: 9ff671f1f629
Revises: 1f5f8990687e
Create Date: 2025-11-28 05:45:33.102114

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9ff671f1f629"
down_revision = "1f5f8990687e"
branch_labels = None
depends_on = None


def upgrade():
    # Create daily_checkins table
    op.create_table(
        "daily_checkins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("registration_id", sa.Integer(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_day_number", sa.Integer(), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(), nullable=False),
        sa.Column("checked_in_by", sa.String(length=255), nullable=True),
        sa.Column("check_in_method", sa.String(length=50), nullable=True),
        sa.Column("session_name", sa.String(length=255), nullable=True),
        sa.Column("check_out_at", sa.DateTime(), nullable=True),
        sa.Column("badge_printed", sa.Boolean(), nullable=True),
        sa.Column("materials_given", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["registration_id"],
            ["registrations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "registration_id", "event_date", name="uq_registration_event_date"
        ),
    )

    # Create indexes
    op.create_index(
        "idx_event_date_checkin",
        "daily_checkins",
        ["event_date", "checked_in_at"],
        unique=False,
    )
    op.create_index(
        "idx_registration_date",
        "daily_checkins",
        ["registration_id", "event_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_checkins_event_date"),
        "daily_checkins",
        ["event_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_checkins_registration_id"),
        "daily_checkins",
        ["registration_id"],
        unique=False,
    )


def downgrade():
    # Drop indexes
    op.drop_index(
        op.f("ix_daily_checkins_registration_id"), table_name="daily_checkins"
    )
    op.drop_index(op.f("ix_daily_checkins_event_date"), table_name="daily_checkins")
    op.drop_index("idx_registration_date", table_name="daily_checkins")
    op.drop_index("idx_event_date_checkin", table_name="daily_checkins")

    # Drop table
    op.drop_table("daily_checkins")
