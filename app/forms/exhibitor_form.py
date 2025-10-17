"""
Enhanced Flask-WTF forms for BEEASY2025 Registration System
Comprehensive forms matching the optimized database models
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, EmailField, TelField, SelectField, TextAreaField,
    BooleanField, DateField, TimeField, IntegerField, DecimalField,
    SelectMultipleField, HiddenField, FieldList, FormField
)
from wtforms.validators import (
    DataRequired, Email, Length, Optional, URL,
    NumberRange, ValidationError, Regexp
)
from app.extensions import db
from app.models import (
    Registration, AttendeeTicketType, ExhibitorPackage,
    ProfessionalCategory, IndustryCategory
)


class ExhibitorRegistrationForm(FlaskForm):
    """Enhanced exhibitor registration form"""

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
        'Company Legal Name',
        validators=[DataRequired(), Length(min=2, max=255)],
        render_kw={'placeholder': 'Company Inc.'}
    )

    company_trading_name = StringField(
        'Trading Name (if different)',
        validators=[Optional(), Length(max=255)],
        render_kw={'placeholder': 'Brand Name'}
    )

    company_registration_number = StringField(
        'Company Registration Number',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'REG-2024-12345'}
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

    company_email = EmailField(
        'Company Email',
        validators=[Optional(), Email()],
        render_kw={'placeholder': 'info@company.com'}
    )

    company_phone = TelField(
        'Company Phone',
        validators=[Optional(), Length(max=50)],
        render_kw={'placeholder': '+254 700 000000'}
    )

    # ===== SECTION 3: Company Profile =====
    industry_category = SelectField(
        'Industry Category',
        choices=[
            ('', 'Select category'),
            ('beekeeping_equipment', 'Beekeeping Equipment'),
            ('processing_equipment', 'Processing Equipment'),
            ('bee_products', 'Bee Products (Honey, Wax, Propolis)'),
            ('packaging', 'Packaging Solutions'),
            ('technology', 'Technology/Software'),
            ('training', 'Training/Consulting'),
            ('financial_services', 'Financial Services'),
            ('research', 'Research/Laboratory'),
            ('government', 'Government/Association'),
            ('media', 'Media/Publishing'),
            ('other', 'Other'),
        ],
        validators=[DataRequired()]
    )

    company_description = TextAreaField(
        'Company Description (for event catalog)',
        validators=[DataRequired(), Length(min=100, max=500)],
        render_kw={'rows': 4, 'placeholder': 'Describe your company and products/services...'}
    )

    years_in_business = SelectField(
        'Years in Business',
        choices=[
            ('', 'Select range'),
            ('<1', 'Less than 1 year'),
            ('1-3', '1-3 years'),
            ('3-5', '3-5 years'),
            ('5-10', '5-10 years'),
            ('10+', '10+ years'),
        ],
        validators=[Optional()]
    )

    employee_count = SelectField(
        'Number of Employees',
        choices=[
            ('', 'Select range'),
            ('1-10', '1-10'),
            ('11-50', '11-50'),
            ('51-200', '51-200'),
            ('201-500', '201-500'),
            ('500+', '500+'),
        ],
        validators=[Optional()]
    )

    # ===== SECTION 4: Package Selection =====
    package_type = SelectField(
        'Exhibition Package',
        choices=[
            ('bronze', 'Bronze Package - $500'),
            ('silver', 'Silver Package - $1,000'),
            ('gold', 'Gold Package - $2,500'),
            ('platinum', 'Platinum Package - $5,000'),
            ('custom', 'Custom Package (Contact Us)'),
        ],
        validators=[DataRequired()],
        render_kw={'class': 'package-selector'}
    )

    # ===== SECTION 5: Booth Preferences =====
    booth_preference_corner = BooleanField(
        'Corner Booth (+$200)',
        default=False
    )

    booth_preference_entrance = BooleanField(
        'Near Entrance (+$150)',
        default=False
    )

    booth_preference_area = StringField(
        'Preferred Area/Location',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'e.g., Main hall, near entrance'}
    )

    booth_preference_notes = TextAreaField(
        'Special Booth Requests',
        validators=[Optional(), Length(max=500)],
        render_kw={'rows': 2, 'placeholder': 'Any specific requirements...'}
    )

    # ===== SECTION 6: Booth Requirements =====
    number_of_staff = IntegerField(
        'Number of Staff Attending',
        validators=[Optional(), NumberRange(min=1, max=50)],
        default=2,
        render_kw={'placeholder': '2'}
    )

    exhibitor_badges_needed = IntegerField(
        'Exhibitor Badges Needed',
        validators=[Optional(), NumberRange(min=1, max=50)],
        default=2,
        render_kw={'placeholder': '2'}
    )

    electricity_required = BooleanField(
        'Electricity Required',
        default=False
    )

    electricity_watts = IntegerField(
        'Power Requirement (Watts)',
        validators=[Optional(), NumberRange(min=0, max=10000)],
        render_kw={'placeholder': 'e.g., 1000'}
    )

    water_connection_required = BooleanField(
        'Water Connection Required',
        default=False
    )

    internet_required = BooleanField(
        'Internet Connection Required',
        default=False
    )

    special_requirements = TextAreaField(
        'Special Requirements',
        validators=[Optional(), Length(max=1000)],
        render_kw={'rows': 3, 'placeholder': 'Any special equipment or setup needs...'}
    )

    # ===== SECTION 7: Secondary Contact =====
    secondary_contact_name = StringField(
        'Secondary Contact Name',
        validators=[Optional(), Length(max=200)],
        render_kw={'placeholder': 'Backup contact person'}
    )

    secondary_contact_email = EmailField(
        'Secondary Contact Email',
        validators=[Optional(), Email()],
        render_kw={'placeholder': 'backup@company.com'}
    )

    secondary_contact_phone = TelField(
        'Secondary Contact Phone',
        validators=[Optional(), Length(max=50)],
        render_kw={'placeholder': '+254 700 000001'}
    )

    # ===== SECTION 8: Billing Information =====
    billing_address = TextAreaField(
        'Billing Address (if different from company address)',
        validators=[Optional(), Length(max=500)],
        render_kw={'rows': 2, 'placeholder': 'Leave blank if same as company address'}
    )

    billing_contact_name = StringField(
        'Billing Contact Name',
        validators=[Optional(), Length(max=200)],
        render_kw={'placeholder': 'Finance person'}
    )

    billing_contact_email = EmailField(
        'Billing Contact Email',
        validators=[Optional(), Email()],
        render_kw={'placeholder': 'finance@company.com'}
    )

    tax_id = StringField(
        'Tax ID / VAT Number',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'P051234567X'}
    )

    purchase_order_number = StringField(
        'Purchase Order Number',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'PO-2024-001 (if applicable)'}
    )

    payment_terms = SelectField(
        'Payment Terms',
        choices=[
            ('immediate', 'Pay Now'),
            ('net_30', 'Net 30 (Invoice)'),
            ('net_60', 'Net 60 (Invoice)'),
        ],
        default='immediate',
        validators=[Optional()]
    )

    # ===== SECTION 9: Social Media & Marketing =====
    linkedin_url = StringField(
        'LinkedIn Company Page',
        validators=[Optional(), URL(), Length(max=255)],
        render_kw={'placeholder': 'https://linkedin.com/company/yourcompany'}
    )

    facebook_url = StringField(
        'Facebook Page',
        validators=[Optional(), URL(), Length(max=255)],
        render_kw={'placeholder': 'https://facebook.com/yourcompany'}
    )

    twitter_handle = StringField(
        'Twitter Handle',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': '@yourcompany'}
    )

    instagram_handle = StringField(
        'Instagram Handle',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': '@yourcompany'}
    )

    # ===== SECTION 10: Legal & Compliance =====
    has_liability_insurance = BooleanField(
        'We have liability insurance',
        default=False
    )

    insurance_policy_number = StringField(
        'Insurance Policy Number',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'INS-2024-12345'}
    )

    products_comply_regulations = BooleanField(
        'All products comply with local regulations',
        default=False
    )

    # ===== SECTION 11: Marketing & Promo =====
    referral_source = SelectField(
        'How did you hear about this exhibition opportunity?',
        choices=[
            ('', 'Select source'),
            ('previous_exhibitor', 'Previous Exhibitor'),
            ('industry_partner', 'Industry Partner'),
            ('email', 'Email Invitation'),
            ('website', 'Website'),
            ('social_media', 'Social Media'),
            ('other', 'Other'),
        ],
        validators=[Optional()]
    )

    promo_code = StringField(
        'Promo Code',
        validators=[Optional(), Length(max=50)],
        render_kw={'placeholder': 'Enter promo code if you have one'}
    )

    # ===== SECTION 12: Consent =====
    consent_photography = BooleanField(
        'We consent to event photography/videography',
        default=True
    )

    consent_catalog = BooleanField(
        'Include our company in the event catalog',
        default=True
    )

    newsletter_signup = BooleanField(
        'Subscribe to exhibitor updates',
        default=True
    )

    terms_accepted = BooleanField(
        'I accept the exhibitor terms and conditions',
        validators=[DataRequired(message='You must accept the terms and conditions')]
    )

    def validate_email(self, field):
        """Check for duplicate email"""
        existing = Registration.query.filter(
            db.func.lower(Registration.email) == field.data.lower(),
            Registration.registration_type == 'exhibitor',
            Registration.is_deleted == False
        ).first()

        if existing:
            raise ValidationError('This email is already registered as an exhibitor.')
        