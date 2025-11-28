"""Drop legacy checked_in columns from registrations table

Revision ID: 4a8bfbc31f91
Revises: 9ff671f1f629
Create Date: 2025-11-28 05:50:28.146086

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4a8bfbc31f91"
down_revision = "9ff671f1f629"
branch_labels = None
depends_on = None


def upgrade():
    # Drop legacy check-in index first
    op.drop_index("ix_registrations_checked_in", table_name="registrations")

    # Drop legacy check-in columns from registrations table
    with op.batch_alter_table("registrations", schema=None) as batch_op:
        batch_op.drop_column("badge_printed")
        batch_op.drop_column("checked_in_by")
        batch_op.drop_column("checked_in_at")
        batch_op.drop_column("checked_in")


def downgrade():
    # Re-add legacy columns
    with op.batch_alter_table("registrations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("checked_in", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("checked_in_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("checked_in_by", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(sa.Column("badge_printed", sa.Boolean(), nullable=True))

    # Re-create index
    op.create_index(
        "ix_registrations_checked_in", "registrations", ["checked_in"], unique=False
    )
