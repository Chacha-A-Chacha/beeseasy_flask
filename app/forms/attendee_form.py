"""
Attendee Registration Form
Cleaned and simplified for better UX
"""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    HiddenField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    TelField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

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

    group_size = IntegerField(
        "Number of Persons in Group",
        validators=[
            Optional(),
            NumberRange(
                min=5, max=10, message="Group size must be between 5 and 10 persons"
            ),
        ],
        render_kw={
            "placeholder": "Enter number of persons (5-10)",
            "min": "5",
            "max": "10",
            "style": "display: none;",  # Hidden by default, shown via JavaScript when GROUP selected
        },
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

    def validate_group_size(self, field):
        """Require group size for GROUP ticket type"""
        if self.ticket_type.data == AttendeeTicketType.GROUP.value:
            if not field.data:
                raise ValidationError("Group size is required for Group Delegate Pass")
            if not (5 <= field.data <= 10):
                raise ValidationError("Group size must be between 5 and 10 persons")
        elif field.data:
            # Group size provided but not GROUP ticket
            raise ValidationError(
                "Group size can only be specified for Group Delegate Pass"
            )

    def validate(self, extra_validators=None):
        """Custom form-level validation for phone number"""
        import phonenumbers
        from phonenumbers import NumberParseException

        # Call parent validation first
        if not super().validate(extra_validators):
            return False

        # Phone validation logic
        phone_valid = False
        phone_error_msg = "Please enter a valid phone number"

        # Check if enhanced phone (JavaScript worked)
        if self.phone_international.data:
            try:
                parsed = phonenumbers.parse(self.phone_international.data, None)
                if phonenumbers.is_valid_number(parsed):
                    phone_valid = True
                else:
                    self.phone_international.errors.append(phone_error_msg)
            except NumberParseException:
                self.phone_international.errors.append(phone_error_msg)
        # Check fallback phone (no JavaScript)
        elif self.phone_country_code_fallback.data and self.phone_number_fallback.data:
            try:
                full_number = (
                    self.phone_country_code_fallback.data
                    + self.phone_number_fallback.data
                )
                parsed = phonenumbers.parse(full_number, None)
                if phonenumbers.is_valid_number(parsed):
                    phone_valid = True
                else:
                    self.phone_number_fallback.errors.append(phone_error_msg)
            except NumberParseException:
                self.phone_number_fallback.errors.append(phone_error_msg)
        else:
            # No phone data provided at all
            self.phone_international.errors.append("Phone number is required")
            phone_valid = False

        return phone_valid

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

    def populate_country_choices(self):
        """Populate country field with all countries"""
        countries = [
            "Afghanistan",
            "Albania",
            "Algeria",
            "Andorra",
            "Angola",
            "Antigua and Barbuda",
            "Argentina",
            "Armenia",
            "Australia",
            "Austria",
            "Azerbaijan",
            "Bahamas",
            "Bahrain",
            "Bangladesh",
            "Barbados",
            "Belarus",
            "Belgium",
            "Belize",
            "Benin",
            "Bhutan",
            "Bolivia",
            "Bosnia and Herzegovina",
            "Botswana",
            "Brazil",
            "Brunei",
            "Bulgaria",
            "Burkina Faso",
            "Burundi",
            "Cabo Verde",
            "Cambodia",
            "Cameroon",
            "Canada",
            "Central African Republic",
            "Chad",
            "Chile",
            "China",
            "Colombia",
            "Comoros",
            "Congo",
            "Costa Rica",
            "Croatia",
            "Cuba",
            "Cyprus",
            "Czech Republic",
            "Denmark",
            "Djibouti",
            "Dominica",
            "Dominican Republic",
            "DR Congo",
            "Ecuador",
            "Egypt",
            "El Salvador",
            "Equatorial Guinea",
            "Eritrea",
            "Estonia",
            "Eswatini",
            "Ethiopia",
            "Fiji",
            "Finland",
            "France",
            "Gabon",
            "Gambia",
            "Georgia",
            "Germany",
            "Ghana",
            "Greece",
            "Grenada",
            "Guatemala",
            "Guinea",
            "Guinea-Bissau",
            "Guyana",
            "Haiti",
            "Honduras",
            "Hungary",
            "Iceland",
            "India",
            "Indonesia",
            "Iran",
            "Iraq",
            "Ireland",
            "Israel",
            "Italy",
            "Ivory Coast",
            "Jamaica",
            "Japan",
            "Jordan",
            "Kazakhstan",
            "Kenya",
            "Kiribati",
            "Kosovo",
            "Kuwait",
            "Kyrgyzstan",
            "Laos",
            "Latvia",
            "Lebanon",
            "Lesotho",
            "Liberia",
            "Libya",
            "Liechtenstein",
            "Lithuania",
            "Luxembourg",
            "Madagascar",
            "Malawi",
            "Malaysia",
            "Maldives",
            "Mali",
            "Malta",
            "Marshall Islands",
            "Mauritania",
            "Mauritius",
            "Mexico",
            "Micronesia",
            "Moldova",
            "Monaco",
            "Mongolia",
            "Montenegro",
            "Morocco",
            "Mozambique",
            "Myanmar",
            "Namibia",
            "Nauru",
            "Nepal",
            "Netherlands",
            "New Zealand",
            "Nicaragua",
            "Niger",
            "Nigeria",
            "North Korea",
            "North Macedonia",
            "Norway",
            "Oman",
            "Pakistan",
            "Palau",
            "Palestine",
            "Panama",
            "Papua New Guinea",
            "Paraguay",
            "Peru",
            "Philippines",
            "Poland",
            "Portugal",
            "Qatar",
            "Romania",
            "Russia",
            "Rwanda",
            "Saint Kitts and Nevis",
            "Saint Lucia",
            "Saint Vincent and the Grenadines",
            "Samoa",
            "San Marino",
            "Sao Tome and Principe",
            "Saudi Arabia",
            "Senegal",
            "Serbia",
            "Seychelles",
            "Sierra Leone",
            "Singapore",
            "Slovakia",
            "Slovenia",
            "Solomon Islands",
            "Somalia",
            "South Africa",
            "South Korea",
            "South Sudan",
            "Spain",
            "Sri Lanka",
            "Sudan",
            "Suriname",
            "Sweden",
            "Switzerland",
            "Syria",
            "Taiwan",
            "Tajikistan",
            "Tanzania",
            "Thailand",
            "Timor-Leste",
            "Togo",
            "Tonga",
            "Trinidad and Tobago",
            "Tunisia",
            "Turkey",
            "Turkmenistan",
            "Tuvalu",
            "Uganda",
            "Ukraine",
            "United Arab Emirates",
            "United Kingdom",
            "United States",
            "Uruguay",
            "Uzbekistan",
            "Vanuatu",
            "Vatican City",
            "Venezuela",
            "Vietnam",
            "Yemen",
            "Zambia",
            "Zimbabwe",
        ]

        self.country.choices = [("", "Select your country")] + [
            (c, c) for c in countries
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
