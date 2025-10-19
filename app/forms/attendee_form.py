"""
Enhanced Flask-WTF forms for BEEASY2025 Registration System
Comprehensive forms matching the optimized database models
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, EmailField, TelField, SelectField, TextAreaField,
    BooleanField, SelectMultipleField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, Length, Optional, ValidationError
)
from app.models import AttendeeTicketType, ProfessionalCategory


# ============================================
# ATTENDEE REGISTRATION FORM
# ============================================

class AttendeeRegistrationForm(FlaskForm):
    """Cleaned attendee registration form - essential fields only"""

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

    # ===== SECTION 2: Professional Information =====
    organization = StringField(
        'Organization',
        validators=[Optional(), Length(max=255)],
        render_kw={'placeholder': 'Company/Organization Name'}
    )

    job_title = StringField(
        'Job Title',
        validators=[Optional(), Length(max=150)],
        render_kw={'placeholder': 'e.g., Beekeeper, CEO, Researcher'}
    )

    professional_category = SelectField(
        'Professional Category',
        choices=[
            ('', 'Select category'),
            (ProfessionalCategory.BEEKEEPER.value, 'Beekeeper/Producer'),
            (ProfessionalCategory.COMMERCIAL.value, 'Commercial Beekeeper'),
            (ProfessionalCategory.RESEARCHER.value, 'Researcher/Academic'),
            (ProfessionalCategory.GOVERNMENT.value, 'Government Official'),
            (ProfessionalCategory.EQUIPMENT_SUPPLIER.value, 'Equipment Supplier'),
            (ProfessionalCategory.HONEY_PROCESSOR.value, 'Honey Processor/Packer'),
            (ProfessionalCategory.NGO.value, 'NGO/Development Worker'),
            (ProfessionalCategory.STUDENT.value, 'Student'),
            (ProfessionalCategory.CONSULTANT.value, 'Consultant'),
            (ProfessionalCategory.INVESTOR.value, 'Investor'),
            (ProfessionalCategory.MEDIA.value, 'Media'),
            (ProfessionalCategory.OTHER.value, 'Other'),
        ],
        validators=[Optional()]
    )

    # ===== SECTION 3: Ticket Selection =====
    ticket_type = SelectField(
        'Ticket Type',
        choices=[
            (AttendeeTicketType.FREE.value, 'Free Ticket'),
            (AttendeeTicketType.EARLY_BIRD.value, 'Early Bird'),
            (AttendeeTicketType.REGULAR.value, 'Regular'),
            (AttendeeTicketType.VIP.value, 'VIP'),
        ],
        validators=[DataRequired()]
    )

    # ===== SECTION 4: Event Preferences (Consolidated to single multi-select) =====
    event_preferences = SelectMultipleField(
        'What are you interested in? (Select all that apply)',
        choices=[
            # Session interests
            ('pollinator_health', 'Pollinator Health & Conservation'),
            ('food_security', 'Food Security & Nutrition'),
            ('market_access', 'Market Access & Trade'),
            ('innovation', 'Innovation & Technology'),
            ('policy', 'Policy & Regulations'),
            ('climate', 'Climate Adaptation'),
            ('queen_breeding', 'Queen Breeding'),
            ('disease_management', 'Disease & Pest Management'),
            # Networking goals
            ('find_suppliers', 'Finding Suppliers/Buyers'),
            ('research_collaboration', 'Research Collaboration'),
            ('investment', 'Investment Opportunities'),
            ('learning', 'Learning Best Practices'),
            ('policy_advocacy', 'Policy Advocacy'),
        ],
        validators=[Optional()],
        render_kw={'size': 8}
    )

    # ===== SECTION 5: Special Requirements =====
    dietary_requirement = SelectField(
        'Dietary Requirements',
        choices=[
            ('', 'None'),
            ('vegetarian', 'Vegetarian'),
            ('vegan', 'Vegan'),
            ('halal', 'Halal'),
            ('kosher', 'Kosher'),
            ('gluten_free', 'Gluten Free'),
            ('other', 'Other (specify below)'),
        ],
        validators=[Optional()]
    )

    dietary_notes = TextAreaField(
        'Dietary Notes',
        validators=[Optional(), Length(max=500)],
        render_kw={'rows': 2, 'placeholder': 'Any allergies or additional dietary needs...'}
    )

    accessibility_needs = TextAreaField(
        'Accessibility Needs',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'rows': 2,
            'placeholder': 'Wheelchair access, sign language, visual/hearing assistance, etc.'
        }
    )

    special_requirements = TextAreaField(
        'Other Special Requirements',
        validators=[Optional(), Length(max=500)],
        render_kw={'rows': 2, 'placeholder': 'Any other needs we should know about...'}
    )

    # ===== SECTION 6: Travel Support =====
    needs_visa_letter = BooleanField(
        'I need a visa support letter',
        default=False
    )

    # ===== SECTION 7: Marketing & Consent =====
    referral_source = SelectField(
        'How did you hear about us?',
        choices=[
            ('', 'Select source'),
            ('website', 'Website'),
            ('social_media', 'Social Media'),
            ('email', 'Email Newsletter'),
            ('colleague', 'Colleague/Friend'),
            ('partner_org', 'Partner Organization'),
            ('previous_event', 'Previous Event'),
            ('advertisement', 'Advertisement'),
            ('other', 'Other'),
        ],
        validators=[Optional()]
    )

    newsletter_signup = BooleanField(
        'Subscribe to event updates and beekeeping news',
        default=True
    )

    consent_photography = BooleanField(
        'I consent to being photographed/filmed at the event',
        default=True
    )

    consent_networking = BooleanField(
        'I consent to my contact details being shared with other attendees for networking',
        default=True
    )

    consent_data_sharing = BooleanField(
        'I consent to my data being shared with event sponsors',
        default=False
    )

    # ===== PROMO CODE =====
    promo_code = StringField(
        'Promo Code',
        validators=[Optional(), Length(max=50)],
        render_kw={'placeholder': 'Enter code if you have one'}
    )

    def validate_dietary_notes(self, field):
        """Require dietary notes if 'other' is selected"""
        if self.dietary_requirement.data == 'other' and not field.data:
            raise ValidationError('Please specify your dietary requirements')
        