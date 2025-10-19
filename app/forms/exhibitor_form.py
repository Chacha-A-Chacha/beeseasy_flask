"""
Enhanced Flask-WTF forms for BEEASY2025 Registration System
Comprehensive forms matching the optimized database models
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, EmailField, TelField, SelectField, TextAreaField,
    BooleanField, IntegerField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, Length, Optional, URL, NumberRange
)
from app.models import ExhibitorPackage, IndustryCategory


class ExhibitorRegistrationForm(FlaskForm):
    """Cleaned exhibitor registration form - essential fields only"""

    # ===== SECTION 1: Contact Person =====
    first_name = StringField(
        'Contact Person First Name',
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={'placeholder': 'Jane'}
    )

    last_name = StringField(
        'Contact Person Last Name',
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={'placeholder': 'Smith'}
    )

    email = EmailField(
        'Contact Email',
        validators=[DataRequired(), Email()],
        render_kw={'placeholder': 'jane.smith@company.com'}
    )

    phone_country_code = SelectField(
        'Country Code',
        choices=[
            ('+254', '+254 (Kenya)'),
            ('+255', '+255 (Tanzania)'),
            ('+256', '+256 (Uganda)'),
            ('+250', '+250 (Rwanda)'),
            ('+1', '+1 (USA/Canada)'),
            ('+44', '+44 (UK)'),
        ],
        default='+254',
        validators=[DataRequired()]
    )

    phone_number = TelField(
        'Phone Number',
        validators=[DataRequired(), Length(min=7, max=20)],
        render_kw={'placeholder': '712345678'}
    )

    job_title = StringField(
        'Job Title',
        validators=[Optional(), Length(max=150)],
        render_kw={'placeholder': 'e.g., Sales Manager, CEO'}
    )

    # ===== SECTION 2: Company Information =====
    company_legal_name = StringField(
        'Company Name',
        validators=[DataRequired(), Length(min=2, max=255)],
        render_kw={'placeholder': 'Company Inc.'}
    )

    company_country = StringField(
        'Country of Registration',
        validators=[DataRequired(), Length(max=100)],
        render_kw={'placeholder': 'Kenya'}
    )

    company_address = TextAreaField(
        'Company Address',
        validators=[DataRequired(), Length(max=500)],
        render_kw={'rows': 2, 'placeholder': 'Street address, city, postal code'}
    )

    company_website = StringField(
        'Company Website',
        validators=[Optional(), URL(), Length(max=255)],
        render_kw={'placeholder': 'https://www.yourcompany.com'}
    )

    # ===== SECTION 3: Alternate Contact (Single backup) =====
    alternate_contact_email = EmailField(
        'Alternate Contact Email (optional)',
        validators=[Optional(), Email()],
        render_kw={'placeholder': 'backup@company.com'}
    )

    # ===== SECTION 4: Company Profile =====
    industry_category = SelectField(
        'Industry Category',
        choices=[
            ('', 'Select category'),
            (IndustryCategory.BEEKEEPING_EQUIPMENT.value, 'Beekeeping Equipment'),
            (IndustryCategory.PROCESSING_EQUIPMENT.value, 'Processing Equipment'),
            (IndustryCategory.BEE_PRODUCTS.value, 'Bee Products (Honey, Wax, Propolis)'),
            (IndustryCategory.PACKAGING.value, 'Packaging Solutions'),
            (IndustryCategory.TECHNOLOGY.value, 'Technology/Software'),
            (IndustryCategory.TRAINING.value, 'Training/Consulting'),
            (IndustryCategory.FINANCIAL_SERVICES.value, 'Financial Services'),
            (IndustryCategory.RESEARCH.value, 'Research/Laboratory'),
            (IndustryCategory.GOVERNMENT.value, 'Government/Association'),
            (IndustryCategory.MEDIA.value, 'Media/Publishing'),
            (IndustryCategory.OTHER.value, 'Other'),
        ],
        validators=[DataRequired()]
    )

    company_description = TextAreaField(
        'Company Description',
        validators=[DataRequired(), Length(min=50, max=1000)],
        render_kw={
            'rows': 4,
            'placeholder': 'Describe your company, products, and services...'
        }
    )

    # ===== SECTION 5: Exhibition Details =====
    package_type = SelectField(
        'Exhibition Package',
        choices=[
            ('', 'Select package'),
            # (ExhibitorPackage.STANDARD.value, 'Standard Booth'),
            # (ExhibitorPackage.PREMIUM.value, 'Premium Booth'),
            (ExhibitorPackage.GOLD.value, 'Gold Package'),
            (ExhibitorPackage.PLATINUM.value, 'Platinum Package'),
        ],
        validators=[DataRequired()]
    )

    products_to_exhibit = TextAreaField(
        'Products/Services to Exhibit',
        validators=[DataRequired(), Length(max=1000)],
        render_kw={
            'rows': 3,
            'placeholder': 'List the main products or services you will showcase...'
        }
    )

    number_of_staff = IntegerField(
        'Number of Staff (for badges)',
        validators=[Optional(), NumberRange(min=1, max=20)],
        default=2,
        render_kw={'placeholder': '2'}
    )

    special_requirements = TextAreaField(
        'Special Requirements',
        validators=[Optional(), Length(max=1000)],
        render_kw={
            'rows': 3,
            'placeholder': 'Electricity needs, setup requirements, etc.'
        }
    )

    # ===== SECTION 6: Marketing & Consent =====
    referral_source = SelectField(
        'How did you hear about this exhibition opportunity?',
        choices=[
            ('', 'Select source'),
            ('website', 'Website'),
            ('email', 'Email Invitation'),
            ('partner', 'Partner Organization'),
            ('previous_exhibitor', 'Previous Exhibition'),
            ('social_media', 'Social Media'),
            ('colleague', 'Colleague'),
            ('advertisement', 'Advertisement'),
            ('other', 'Other'),
        ],
        validators=[Optional()]
    )

    newsletter_signup = BooleanField(
        'Subscribe to exhibitor updates',
        default=True
    )

    consent_photography = BooleanField(
        'Consent to photography/filming at our booth',
        default=True
    )

    consent_catalog = BooleanField(
        'Include our company in the event catalog',
        default=True
    )

    # ===== PROMO CODE =====
    promo_code = StringField(
        'Promo Code',
        validators=[Optional(), Length(max=50)],
        render_kw={'placeholder': 'Enter code if you have one'}
    )
