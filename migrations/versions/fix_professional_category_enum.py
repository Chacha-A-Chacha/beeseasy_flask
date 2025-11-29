"""Fix professional_category enum type to include all values.

Revision ID: fix_enum_20251129
Revises:
Create Date: 2025-11-29 02:25:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_enum_20251129"
down_revision = "4a8bfbc31f91"
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix the professional_category enum type by ensuring all values exist.
    This uses PostgreSQL ALTER TYPE ADD VALUE which is the safest approach.
    """

    # List of all professional category values that should exist
    enum_values = [
        "farmer",
        "researcher_academic",
        "student",
        "government_official",
        "ngo_nonprofit",
        "private_sector",
        "entrepreneur",
        "consultant",
        "extension_officer",
        "cooperative_member",
        "investor",
        "media_journalist",
        "policy_maker",
        "conservationist",
        "educator",
        "other",
    ]

    # Add each value if it doesn't exist
    # Using IF NOT EXISTS to make the migration idempotent
    for value in enum_values:
        op.execute(f"ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS '{value}'")


def downgrade():
    """
    Downgrade is not easily reversible for enum types in PostgreSQL.
    Enum values cannot be removed once added.
    This migration is essentially one-way.
    """
    pass
