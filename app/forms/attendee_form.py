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


# ============================================
# ATTENDEE REGISTRATION FORM
# ============================================

class AttendeeRegistrationForm(FlaskForm):
    """Enhanced attendee registration form"""

    # ===== SECTION 1: Basic Information =====
    first_name = StringField(
        'First Name',
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={'placeholder': 'John'}
    )

    last_name = StringField(
        'Last Name',
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={'placeholder': 'Doe'}
    )

    email = EmailField(
        'Email Address',
        validators=[DataRequired(), Email()],
        render_kw={'placeholder': 'john.doe@example.com'}
    )

    phone_country_code = SelectField(
        'Country Code',
        choices=[
            ('+254', '+254 (Kenya)'),
            ('+255', '+255 (Tanzania)'),
            ('+256', '+256 (Uganda)'),
            ('+250', '+250 (Rwanda)'),
            ('+257', '+257 (Burundi)'),
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

    # ===== SECTION 2: Ticket Selection =====
    ticket_type = SelectField(
        'Ticket Type',
        choices=[
            ('free', 'Free Pass - $0'),
            ('standard', 'Standard Pass - $50'),
            ('vip', 'VIP Pass - $150'),
            ('student', 'Student Pass - $25'),
            ('early_bird', 'Early Bird Pass - $30'),
        ],
        validators=[DataRequired()],
        render_kw={'class': 'ticket-selector'}
    )

    # ===== SECTION 3: Professional Information =====
    organization = StringField(
        'Organization/Company',
        validators=[Optional(), Length(max=255)],
        render_kw={'placeholder': 'Your organization (optional)'}
    )

    job_title = StringField(
        'Job Title',
        validators=[Optional(), Length(max=150)],
        render_kw={'placeholder': 'e.g., Beekeeper, Manager, Researcher'}
    )

    professional_category = SelectField(
        'Professional Category',
        choices=[
            ('', 'Select your category'),
            ('beekeeper_hobbyist', 'Beekeeper (Hobbyist)'),
            ('beekeeper_commercial', 'Beekeeper (Commercial)'),
            ('researcher', 'Researcher/Academic'),
            ('government', 'Government/Policy'),
            ('equipment_supplier', 'Equipment Supplier'),
            ('honey_processor', 'Honey Processor/Trader'),
            ('ngo', 'NGO/Development Worker'),
            ('student', 'Student'),
            ('consultant', 'Consultant'),
            ('investor', 'Investor'),
            ('media', 'Media'),
            ('other', 'Other'),
        ],
        validators=[Optional()]
    )

    industry_sector = StringField(
        'Industry/Sector',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'e.g., Commercial Beekeeping'}
    )

    years_in_beekeeping = SelectField(
        'Years in Beekeeping',
        choices=[
            ('', 'Select experience'),
            ('<1', 'Less than 1 year'),
            ('1-3', '1-3 years'),
            ('3-5', '3-5 years'),
            ('5-10', '5-10 years'),
            ('10+', '10+ years'),
        ],
        validators=[Optional()]
    )

    company_size = SelectField(
        'Company Size',
        choices=[
            ('', 'Select size'),
            ('1-10', '1-10 employees'),
            ('11-50', '11-50 employees'),
            ('51-200', '51-200 employees'),
            ('201-500', '201-500 employees'),
            ('500+', '500+ employees'),
        ],
        validators=[Optional()]
    )

    # ===== SECTION 4: Event Preferences =====
    session_interests = SelectMultipleField(
        'Session Interests (Select all that apply)',
        choices=[
            ('pollinator_health', 'Pollinator Health & Conservation'),
            ('food_security', 'Food Security & Nutrition'),
            ('market_access', 'Market Access & Trade'),
            ('innovation', 'Innovation & Technology'),
            ('policy', 'Policy & Regulations'),
            ('climate', 'Climate Adaptation'),
            ('queen_breeding', 'Queen Breeding'),
            ('disease_management', 'Disease & Pest Management'),
        ],
        validators=[Optional()]
    )

    networking_goals = SelectMultipleField(
        'Networking Goals',
        choices=[
            ('find_suppliers', 'Find Suppliers/Buyers'),
            ('research_collaboration', 'Research Collaboration'),
            ('investment', 'Investment Opportunities'),
            ('learning', 'Learning Best Practices'),
            ('policy_advocacy', 'Policy Advocacy'),
        ],
        validators=[Optional()]
    )

    attendance_objectives = TextAreaField(
        'What are your main objectives for attending?',
        validators=[Optional(), Length(max=500)],
        render_kw={'rows': 3, 'placeholder': 'Tell us what you hope to achieve...'}
    )

    accessibility_needs = TextAreaField(
        'Accessibility Needs',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'rows': 2,
            'placeholder': 'Wheelchair access, sign language, visual/hearing assistance, etc.'
        }
    )

    tshirt_size = SelectField(
        'T-Shirt Size',
        choices=[
            ('', 'Select size'),
            ('XS', 'XS'),
            ('S', 'S'),
            ('M', 'M'),
            ('L', 'L'),
            ('XL', 'XL'),
            ('XXL', 'XXL'),
            ('XXXL', 'XXXL'),
        ],
        validators=[Optional()]
    )

    # ===== SECTION 6: Travel & Accommodation =====
    country = StringField(
        'Country',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'Kenya'}
    )

    city = StringField(
        'City',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'Nairobi'}
    )

    needs_visa_letter = BooleanField(
        'I need a visa support letter',
        default=False
    )

    needs_accommodation = BooleanField(
        'I need accommodation assistance',
        default=False
    )

    arrival_date = DateField(
        'Arrival Date',
        validators=[Optional()],
        format='%Y-%m-%d'
    )

    departure_date = DateField(
        'Departure Date',
        validators=[Optional()],
        format='%Y-%m-%d'
    )

    # ===== SECTION 7: Networking Profile =====
    linkedin_url = StringField(
        'LinkedIn Profile',
        validators=[Optional(), URL(), Length(max=255)],
        render_kw={'placeholder': 'https://linkedin.com/in/yourprofile'}
    )

    twitter_handle = StringField(
        'Twitter Handle',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': '@yourusername'}
    )

    bio = TextAreaField(
        'Short Bio (for networking)',
        validators=[Optional(), Length(max=500)],
        render_kw={'rows': 3, 'placeholder': 'Tell other attendees about yourself...'}
    )

    # ===== SECTION 8: Marketing & Promo =====
    referral_source = SelectField(
        'How did you hear about us?',
        choices=[
            ('', 'Select source'),
            ('social_media', 'Social Media'),
            ('colleague', 'Colleague/Friend'),
            ('email', 'Email Newsletter'),
            ('association', 'Professional Association'),
            ('previous_event', 'Previous BEEASY Event'),
            ('web_search', 'Web Search'),
            ('other', 'Other'),
        ],
        validators=[Optional()]
    )

    promo_code = StringField(
        'Promo Code',
        validators=[Optional(), Length(max=50)],
        render_kw={'placeholder': 'Enter promo code if you have one'}
    )

    # ===== SECTION 9: Consent =====
    consent_photography = BooleanField(
        'I consent to event photography/videography',
        default=True
    )

    consent_networking = BooleanField(
        'Share my profile with other attendees for networking',
        default=True
    )

    consent_data_sharing = BooleanField(
        'Share my contact info with exhibitors (for follow-up)',
        default=False
    )

    newsletter_signup = BooleanField(
        'Subscribe to BEEASY community newsletter',
        default=True
    )

    def validate_email(self, field):
        """Check for duplicate email"""
        existing = Registration.query.filter(
            db.func.lower(Registration.email) == field.data.lower(),
            Registration.registration_type == 'attendee',
            Registration.is_deleted == False
        ).first()

        if existing:
            raise ValidationError('This email is already registered as an attendee.')


# ============================================
# EXHIBITOR REGISTRATION FORM
# ============================================




# ============================================
# PAYMENT FORM
# ============================================

