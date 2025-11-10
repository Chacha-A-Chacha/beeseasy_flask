"""update_professional_and_industry_categories_to_broad

Revision ID: 133655e65749
Revises: fc910f1ba60b
Create Date: 2025-11-10 15:55:08.056576

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "133655e65749"
down_revision = "fc910f1ba60b"
branch_labels = None
depends_on = None


def upgrade():
    """
    Update ProfessionalCategory and IndustryCategory enums to broad categories.
    PostgreSQL enums require special handling - we can't just ALTER them directly.
    """

    # ============================================
    # STEP 1: Update ProfessionalCategory Enum
    # ============================================

    # Add new enum values
    op.execute("ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'farmer'")
    op.execute(
        "ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'researcher_academic'"
    )
    op.execute(
        "ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'government_official'"
    )
    op.execute(
        "ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'ngo_nonprofit'"
    )
    op.execute(
        "ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'private_sector'"
    )
    op.execute("ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'entrepreneur'")
    op.execute(
        "ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'extension_officer'"
    )
    op.execute(
        "ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'cooperative_member'"
    )
    op.execute(
        "ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'media_journalist'"
    )
    op.execute("ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'policy_maker'")
    op.execute(
        "ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'conservationist'"
    )
    op.execute("ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'educator'")

    # Migrate existing data to new values
    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'farmer'
        WHERE professional_category IN ('beekeeper_hobbyist', 'beekeeper_commercial')
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'researcher_academic'
        WHERE professional_category = 'researcher'
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'government_official'
        WHERE professional_category = 'government'
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'ngo_nonprofit'
        WHERE professional_category = 'ngo'
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'private_sector'
        WHERE professional_category IN ('equipment_supplier', 'honey_processor')
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'media_journalist'
        WHERE professional_category = 'media'
    """)

    # ============================================
    # STEP 2: Update IndustryCategory Enum
    # ============================================

    # Add new enum values
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'agriculture_inputs'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'equipment_machinery'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'processing_packaging'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'technology_innovation'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'training_education'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'research_development'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'consulting_advisory'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'conservation_environment'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'certification_standards'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'logistics_supply_chain'"
    )
    op.execute("ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'marketing_trade'")
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'government_agency'"
    )
    op.execute("ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'ngo_development'")
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'media_communications'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'healthcare_nutrition'"
    )
    op.execute(
        "ALTER TYPE industrycategory ADD VALUE IF NOT EXISTS 'tourism_hospitality'"
    )

    # Migrate existing data to new values
    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'agriculture_inputs'
        WHERE industry_category = 'bee_products'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'equipment_machinery'
        WHERE industry_category IN ('beekeeping_equipment', 'processing_equipment')
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'processing_packaging'
        WHERE industry_category = 'packaging'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'technology_innovation'
        WHERE industry_category = 'technology'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'training_education'
        WHERE industry_category = 'training'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'research_development'
        WHERE industry_category = 'research'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'government_agency'
        WHERE industry_category = 'government'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'media_communications'
        WHERE industry_category = 'media'
    """)


def downgrade():
    """
    Revert to old enum values.
    Note: This is a lossy migration - we can't perfectly restore old mappings.
    """

    # Revert ProfessionalCategory mappings
    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'beekeeper_hobbyist'
        WHERE professional_category = 'farmer'
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'researcher'
        WHERE professional_category = 'researcher_academic'
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'government'
        WHERE professional_category = 'government_official'
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'ngo'
        WHERE professional_category = 'ngo_nonprofit'
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'equipment_supplier'
        WHERE professional_category = 'private_sector'
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'media'
        WHERE professional_category = 'media_journalist'
    """)

    op.execute("""
        UPDATE attendee_registrations
        SET professional_category = 'other'
        WHERE professional_category IN ('extension_officer', 'cooperative_member', 'policy_maker', 'conservationist', 'educator', 'entrepreneur')
    """)

    # Revert IndustryCategory mappings
    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'bee_products'
        WHERE industry_category = 'agriculture_inputs'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'beekeeping_equipment'
        WHERE industry_category = 'equipment_machinery'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'packaging'
        WHERE industry_category = 'processing_packaging'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'technology'
        WHERE industry_category = 'technology_innovation'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'training'
        WHERE industry_category = 'training_education'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'research'
        WHERE industry_category = 'research_development'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'government'
        WHERE industry_category = 'government_agency'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'media'
        WHERE industry_category = 'media_communications'
    """)

    op.execute("""
        UPDATE exhibitor_registrations
        SET industry_category = 'other'
        WHERE industry_category IN ('consulting_advisory', 'conservation_environment', 'certification_standards', 'logistics_supply_chain', 'marketing_trade', 'ngo_development', 'healthcare_nutrition', 'tourism_hospitality')
    """)
