"""
Attendee Registration Form
Cleaned and simplified for better UX
"""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    HiddenField,
    SelectField,
    SelectMultipleField,
    StringField,
    TelField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from app.models import AttendeeTicketType, ProfessionalCategory, TicketPrice

# ============================================
# ATTENDEE REGISTRATION FORM
# ============================================


class AttendeeRegistrationForm(FlaskForm):
    """Cleaned attendee registration form - essential fields only"""

    # ===== SECTION 1: Basic Information =====
    first_name = StringField(
        "First Name",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "John"},
    )

    last_name = StringField(
        "Last Name",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "Doe"},
    )

    email = EmailField(
        "Email Address",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "john.doe@example.com"},
    )

    # Enhanced international phone input (JavaScript-enabled users)
    phone_international = TelField(
        "Phone Number",
        validators=[Optional()],
        render_kw={
            "placeholder": "Enter phone number",
            "data-intl-tel-input": "true",
            "id": "phone_international",
        },
    )

    # Hidden fields (populated by JavaScript)
    phone_country_code = HiddenField()
    phone_number = HiddenField()

    # Fallback fields (for no-JavaScript users)
    phone_country_code_fallback = SelectField(
        "Country Code",
        choices=[
            ("+254", "+254 (Kenya)"),
            ("+255", "+255 (Tanzania)"),
            ("+256", "+256 (Uganda)"),
            ("+250", "+250 (Rwanda)"),
            ("+257", "+257 (Burundi)"),
            ("+1", "+1 (USA/Canada)"),
            ("+44", "+44 (UK)"),
        ],
        default="+254",
        validators=[Optional()],
    )

    phone_number_fallback = TelField(
        "Phone Number",
        validators=[Optional(), Length(min=7, max=20)],
        render_kw={"placeholder": "712345678"},
    )

    # ===== LOCATION INFORMATION =====
    country = SelectField(
        "Country",
        validators=[Optional(), Length(max=100)],
        choices=[
            ("", "Select your country"),
        ],
        render_kw={
            "id": "country_select",
            "placeholder": "Select your country",
        },
    )

    city = StringField(
        "City",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g., Nairobi, Dar es Salaam, Kampala"},
    )

    # ===== SECTION 2: Professional Information =====
    organization = StringField(
        "Organization",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Company/Organization Name"},
    )

    job_title = StringField(
        "Job Title",
        validators=[Optional(), Length(max=150)],
        render_kw={"placeholder": "e.g., Beekeeper, CEO, Researcher"},
    )

    professional_category = SelectField(
        "Professional Category",
        choices=[
            ("", "Select category"),
            (ProfessionalCategory.FARMER.value, "Farmer/Producer"),
            (ProfessionalCategory.RESEARCHER_ACADEMIC.value, "Researcher/Academic"),
            (ProfessionalCategory.STUDENT.value, "Student"),
            (ProfessionalCategory.GOVERNMENT_OFFICIAL.value, "Government Official"),
            (ProfessionalCategory.NGO_NONPROFIT.value, "NGO/Non-Profit"),
            (ProfessionalCategory.PRIVATE_SECTOR.value, "Private Sector"),
            (ProfessionalCategory.ENTREPRENEUR.value, "Entrepreneur"),
            (ProfessionalCategory.CONSULTANT.value, "Consultant"),
            (ProfessionalCategory.EXTENSION_OFFICER.value, "Extension Officer"),
            (ProfessionalCategory.COOPERATIVE_MEMBER.value, "Cooperative Member"),
            (ProfessionalCategory.INVESTOR.value, "Investor"),
            (ProfessionalCategory.MEDIA_JOURNALIST.value, "Media/Journalist"),
            (ProfessionalCategory.POLICY_MAKER.value, "Policy Maker"),
            (ProfessionalCategory.CONSERVATIONIST.value, "Conservationist"),
            (ProfessionalCategory.EDUCATOR.value, "Educator"),
            (ProfessionalCategory.OTHER.value, "Other"),
        ],
        validators=[Optional()],
    )

    # ===== SECTION 3: Ticket Selection =====
    ticket_type = SelectField(
        "Ticket Type",
        choices=[],  # Populated dynamically in route
        validators=[DataRequired()],
    )

    # ===== SECTION 4: Event Preferences (Consolidated to single multi-select) =====
    event_preferences = SelectMultipleField(
        "What are you interested in? (Select all that apply)",
        choices=[
            # Session interests
            ("pollinator_health", "Pollinator Health & Conservation"),
            ("food_security", "Food Security & Nutrition"),
            ("market_access", "Market Access & Trade"),
            ("innovation", "Innovation & Technology"),
            ("policy", "Policy & Regulations"),
            ("climate", "Climate Adaptation"),
            ("queen_breeding", "Queen Breeding"),
            ("disease_management", "Disease & Pest Management"),
            # Networking goals
            ("find_suppliers", "Finding Suppliers/Buyers"),
            ("research_collaboration", "Research Collaboration"),
            ("investment", "Investment Opportunities"),
            ("learning", "Learning Best Practices"),
            ("policy_advocacy", "Policy Advocacy"),
        ],
        validators=[Optional()],
        render_kw={"size": 8},
    )

    # ===== SECTION 5: Special Requirements =====
    dietary_requirement = SelectField(
        "Dietary Requirements",
        choices=[
            ("", "None"),
            ("vegetarian", "Vegetarian"),
            ("vegan", "Vegan"),
            ("halal", "Halal"),
            ("kosher", "Kosher"),
            ("gluten_free", "Gluten Free"),
            ("other", "Other (specify below)"),
        ],
        validators=[Optional()],
    )

    dietary_notes = TextAreaField(
        "Dietary Notes",
        validators=[Optional(), Length(max=500)],
        render_kw={
            "rows": 2,
            "placeholder": "Any allergies or additional dietary needs...",
        },
    )

    accessibility_needs = TextAreaField(
        "Accessibility Needs",
        validators=[Optional(), Length(max=500)],
        render_kw={
            "rows": 2,
            "placeholder": "Wheelchair access, sign language, visual/hearing assistance, etc.",
        },
    )

    special_requirements = TextAreaField(
        "Other Special Requirements",
        validators=[Optional(), Length(max=500)],
        render_kw={"rows": 2, "placeholder": "Any other needs we should know about..."},
    )

    # ===== SECTION 6: Travel Support =====
    needs_visa_letter = BooleanField("I need a visa support letter", default=False)

    # ===== SECTION 7: Marketing & Consent =====
    referral_source = SelectField(
        "How did you hear about us?",
        choices=[
            ("", "Select source"),
            ("website", "Website"),
            ("social_media", "Social Media"),
            ("email", "Email Newsletter"),
            ("colleague", "Colleague/Friend"),
            ("partner_org", "Partner Organization"),
            ("previous_event", "Previous Event"),
            ("advertisement", "Advertisement"),
            ("other", "Other"),
        ],
        validators=[Optional()],
    )

    newsletter_signup = BooleanField(
        "Subscribe to event updates and beekeeping news", default=True
    )

    consent_photography = BooleanField(
        "I consent to being photographed/filmed at the event", default=True
    )

    consent_networking = BooleanField(
        "I consent to my contact details being shared with other attendees for networking",
        default=True,
    )

    consent_data_sharing = BooleanField(
        "I consent to my data being shared with event sponsors", default=False
    )

    # ===== PROMO CODE =====
    promo_code = StringField(
        "Promo Code",
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "Enter code if you have one"},
    )

    def validate_dietary_notes(self, field):
        """Require dietary notes if 'other' is selected"""
        if self.dietary_requirement.data == "other" and not field.data:
            raise ValidationError("Please specify your dietary requirements")

    def validate_phone_number(self, field):
        """Validate phone number - handles both enhanced and fallback inputs"""
        import phonenumbers
        from phonenumbers import NumberParseException

        # Check if enhanced phone (JavaScript worked)
        if self.phone_international.data:
            try:
                parsed = phonenumbers.parse(self.phone_international.data, None)
                if not phonenumbers.is_valid_number(parsed):
                    raise ValidationError("Please enter a valid phone number")
            except NumberParseException:
                raise ValidationError("Please enter a valid phone number")
        # Check fallback phone (no JavaScript)
        elif self.phone_country_code_fallback.data and self.phone_number_fallback.data:
            try:
                full_number = (
                    self.phone_country_code_fallback.data
                    + self.phone_number_fallback.data
                )
                parsed = phonenumbers.parse(full_number, None)
                if not phonenumbers.is_valid_number(parsed):
                    raise ValidationError("Please enter a valid phone number")
            except NumberParseException:
                raise ValidationError("Please enter a valid phone number")
        else:
            raise ValidationError("Phone number is required")

    def populate_ticket_choices(self):
        """Dynamically populate ticket choices from database"""
        from app.extensions import db

        tickets = (
            TicketPrice.query.filter_by(is_active=True)
            .order_by(TicketPrice.price)
            .all()
        )
        self.ticket_type.choices = [
            (
                ticket.ticket_type.value,
                f"{ticket.name} - {ticket.currency} {ticket.get_current_price():,.0f}",
            )
            for ticket in tickets
        ]

    def process_phone_data(self):
        """Process phone data from either enhanced or fallback inputs"""
        import phonenumbers

        # Priority 1: Enhanced phone (JavaScript worked)
        if self.phone_international.data:
            try:
                parsed = phonenumbers.parse(self.phone_international.data, None)
                country_code = f"+{parsed.country_code}"
                national_number = str(parsed.national_number)
                return country_code, national_number
            except Exception:
                pass

        # Priority 2: Fallback phone (no JavaScript)
        if self.phone_country_code_fallback.data and self.phone_number_fallback.data:
            return (
                self.phone_country_code_fallback.data,
                self.phone_number_fallback.data,
            )

        # If hidden fields were populated directly (edge case)
        if self.phone_country_code.data and self.phone_number.data:
            return self.phone_country_code.data, self.phone_number.data

        return None, None
