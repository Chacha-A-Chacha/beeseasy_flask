-- Direct SQL fix for professional_category enum
-- Run this if Alembic migration doesn't work properly

-- Add all missing professional_category enum values
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'farmer';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'researcher_academic';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'student';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'government_official';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'ngo_nonprofit';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'private_sector';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'entrepreneur';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'consultant';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'extension_officer';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'cooperative_member';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'investor';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'media_journalist';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'policy_maker';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'conservationist';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'educator';
ALTER TYPE professionalcategory ADD VALUE IF NOT EXISTS 'other';

-- Verify the enum type has all values
-- Run this to check: SELECT enum_range(NULL::professionalcategory);
