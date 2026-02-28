"""Standardize all enum values to lowercase.

Revision ID: fix_enum_lowercase
Revises: fix_enum_20251129
Create Date: 2026-02-28
"""

from alembic import op

revision = "fix_enum_lowercase"
down_revision = "876d495dc419"
branch_labels = None
depends_on = None


def upgrade():
    """Convert all uppercase enum values to lowercase across all tables."""

    # Users table - role
    op.execute("UPDATE users SET role = LOWER(role) WHERE role != LOWER(role)")

    # Registrations table - status
    op.execute("UPDATE registrations SET status = LOWER(status) WHERE status != LOWER(status)")

    # Attendee registrations - ticket_type
    op.execute("UPDATE attendee_registrations SET ticket_type = LOWER(ticket_type) WHERE ticket_type != LOWER(ticket_type)")

    # Exhibitor registrations - industry_category, package_type
    op.execute("UPDATE exhibitor_registrations SET industry_category = LOWER(industry_category) WHERE industry_category != LOWER(industry_category)")
    op.execute("UPDATE exhibitor_registrations SET package_type = LOWER(package_type) WHERE package_type != LOWER(package_type)")

    # Ticket prices - ticket_type
    op.execute("UPDATE ticket_prices SET ticket_type = LOWER(ticket_type) WHERE ticket_type != LOWER(ticket_type)")

    # Exhibitor package prices - package_type
    op.execute("UPDATE exhibitor_package_prices SET package_type = LOWER(package_type) WHERE package_type != LOWER(package_type)")

    # Payments - payment_type, payment_method, payment_status
    op.execute("UPDATE payments SET payment_type = LOWER(payment_type) WHERE payment_type != LOWER(payment_type)")
    op.execute("UPDATE payments SET payment_method = LOWER(payment_method) WHERE payment_method != LOWER(payment_method)")
    op.execute("UPDATE payments SET payment_status = LOWER(payment_status) WHERE payment_status != LOWER(payment_status)")


def downgrade():
    """Convert lowercase enum values back to uppercase."""

    op.execute("UPDATE users SET role = UPPER(role) WHERE role != UPPER(role)")
    op.execute("UPDATE registrations SET status = UPPER(status) WHERE status != UPPER(status)")
    op.execute("UPDATE attendee_registrations SET ticket_type = UPPER(ticket_type) WHERE ticket_type != UPPER(ticket_type)")
    op.execute("UPDATE exhibitor_registrations SET industry_category = UPPER(industry_category) WHERE industry_category != UPPER(industry_category)")
    op.execute("UPDATE exhibitor_registrations SET package_type = UPPER(package_type) WHERE package_type != UPPER(package_type)")
    op.execute("UPDATE ticket_prices SET ticket_type = UPPER(ticket_type) WHERE ticket_type != UPPER(ticket_type)")
    op.execute("UPDATE exhibitor_package_prices SET package_type = UPPER(package_type) WHERE package_type != UPPER(package_type)")
    op.execute("UPDATE payments SET payment_type = UPPER(payment_type) WHERE payment_type != UPPER(payment_type)")
    op.execute("UPDATE payments SET payment_method = UPPER(payment_method) WHERE payment_method != UPPER(payment_method)")
    op.execute("UPDATE payments SET payment_status = UPPER(payment_status) WHERE payment_status != UPPER(payment_status)")
