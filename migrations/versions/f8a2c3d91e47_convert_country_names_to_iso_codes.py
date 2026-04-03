"""Convert country names to ISO codes

Revision ID: f8a2c3d91e47
Revises: a53412520dbf
Create Date: 2026-03-12 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f8a2c3d91e47"
down_revision = "a53412520dbf"
branch_labels = None
depends_on = None


def _get_country_code(name):
    """Inline lookup to avoid importing app code in migration."""
    from app.utils.countries import get_country_code

    return get_country_code(name)


def _get_country_name(code):
    """Inline lookup to avoid importing app code in migration."""
    from app.utils.countries import get_country_name

    return get_country_name(code)


def upgrade():
    conn = op.get_bind()

    # Convert registrations.country (attendee country)
    rows = conn.execute(
        sa.text("SELECT id, country FROM registrations WHERE country IS NOT NULL")
    ).fetchall()
    for row in rows:
        code = _get_country_code(row[1])
        if code and code != row[1]:
            conn.execute(
                sa.text("UPDATE registrations SET country = :code WHERE id = :id"),
                {"code": code, "id": row[0]},
            )

    # Convert exhibitor_registrations.company_country
    rows = conn.execute(
        sa.text(
            "SELECT id, company_country FROM exhibitor_registrations WHERE company_country IS NOT NULL"
        )
    ).fetchall()
    for row in rows:
        code = _get_country_code(row[1])
        if code and code != row[1]:
            conn.execute(
                sa.text(
                    "UPDATE exhibitor_registrations SET company_country = :code WHERE id = :id"
                ),
                {"code": code, "id": row[0]},
            )


def downgrade():
    conn = op.get_bind()

    # Convert registrations.country back to names
    rows = conn.execute(
        sa.text("SELECT id, country FROM registrations WHERE country IS NOT NULL")
    ).fetchall()
    for row in rows:
        # Only convert 2-letter codes back
        if row[1] and len(row[1]) == 2:
            name = _get_country_name(row[1])
            if name != row[1]:
                conn.execute(
                    sa.text(
                        "UPDATE registrations SET country = :name WHERE id = :id"
                    ),
                    {"name": name, "id": row[0]},
                )

    # Convert exhibitor_registrations.company_country back to names
    rows = conn.execute(
        sa.text(
            "SELECT id, company_country FROM exhibitor_registrations WHERE company_country IS NOT NULL"
        )
    ).fetchall()
    for row in rows:
        if row[1] and len(row[1]) == 2:
            name = _get_country_name(row[1])
            if name != row[1]:
                conn.execute(
                    sa.text(
                        "UPDATE exhibitor_registrations SET company_country = :name WHERE id = :id"
                    ),
                    {"name": name, "id": row[0]},
                )
