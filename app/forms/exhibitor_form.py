"""
Enhanced Flask-WTF forms for BEEASY2025 Registration System
Comprehensive forms matching the optimized database models
"""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    TelField,
    TextAreaField,
)
from wtforms.validators import (
    URL,
    DataRequired,
    Email,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from app.models import ExhibitorPackage, ExhibitorPackagePrice, IndustryCategory


class ExhibitorRegistrationForm(FlaskForm):
    """Cleaned exhibitor registration form - essential fields only"""

    # ===== SECTION 1: Contact Person =====
    first_name = StringField(
        "Contact Person First Name",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "Jane"},
    )

    last_name = StringField(
        "Contact Person Last Name",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "Smith"},
    )

    email = EmailField(
        "Contact Email",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "jane.smith@company.com"},
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

    job_title = StringField(
        "Job Title",
        validators=[Optional(), Length(max=150)],
        render_kw={"placeholder": "e.g., Sales Manager, CEO"},
    )

    # ===== SECTION 2: Company Information =====
    company_legal_name = StringField(
        "Company Name",
        validators=[DataRequired(), Length(min=2, max=255)],
        render_kw={"placeholder": "Company Inc."},
    )

    company_country = StringField(
        "Country of Registration",
        validators=[DataRequired(), Length(max=100)],
        render_kw={"placeholder": "Kenya"},
    )

    company_address = TextAreaField(
        "Company Address",
        validators=[DataRequired(), Length(max=500)],
        render_kw={"rows": 2, "placeholder": "Street address, city, postal code"},
    )

    company_website = StringField(
        "Company Website",
        validators=[Optional(), URL(), Length(max=255)],
        render_kw={"placeholder": "https://www.yourcompany.com"},
    )

    # ===== SECTION 3: Alternate Contact (Single backup) =====
    alternate_contact_email = EmailField(
        "Alternate Contact Email (optional)",
        validators=[Optional(), Email()],
        render_kw={"placeholder": "backup@company.com"},
    )

    # ===== SECTION 4: Company Profile =====
    industry_category = SelectField(
        "Industry Category",
        choices=[
            ("", "Select category"),
            (IndustryCategory.AGRICULTURE_INPUTS.value, "Agriculture Inputs"),
            (IndustryCategory.EQUIPMENT_MACHINERY.value, "Equipment & Machinery"),
            (IndustryCategory.PROCESSING_PACKAGING.value, "Processing & Packaging"),
            (IndustryCategory.TECHNOLOGY_INNOVATION.value, "Technology & Innovation"),
            (IndustryCategory.FINANCIAL_SERVICES.value, "Financial Services"),
            (IndustryCategory.TRAINING_EDUCATION.value, "Training & Education"),
            (IndustryCategory.RESEARCH_DEVELOPMENT.value, "Research & Development"),
            (IndustryCategory.CONSULTING_ADVISORY.value, "Consulting & Advisory"),
            (
                IndustryCategory.CONSERVATION_ENVIRONMENT.value,
                "Conservation & Environment",
            ),
            (
                IndustryCategory.CERTIFICATION_STANDARDS.value,
                "Certification & Standards",
            ),
            (IndustryCategory.LOGISTICS_SUPPLY_CHAIN.value, "Logistics & Supply Chain"),
            (IndustryCategory.MARKETING_TRADE.value, "Marketing & Trade"),
            (IndustryCategory.GOVERNMENT_AGENCY.value, "Government Agency"),
            (IndustryCategory.NGO_DEVELOPMENT.value, "NGO/Development"),
            (IndustryCategory.MEDIA_COMMUNICATIONS.value, "Media & Communications"),
            (IndustryCategory.HEALTHCARE_NUTRITION.value, "Healthcare & Nutrition"),
            (IndustryCategory.TOURISM_HOSPITALITY.value, "Tourism & Hospitality"),
            (IndustryCategory.OTHER.value, "Other"),
        ],
        validators=[DataRequired()],
    )

    company_description = TextAreaField(
        "Company Description",
        validators=[DataRequired(), Length(min=50, max=1000)],
        render_kw={
            "rows": 4,
            "placeholder": "Describe your company, products, and services...",
        },
    )

    # ===== SECTION 5: Exhibition Details =====
    package_type = SelectField(
        "Exhibition Package",
        choices=[],  # Populated dynamically in route
        validators=[DataRequired()],
    )

    products_to_exhibit = TextAreaField(
        "Products/Services to Exhibit",
        validators=[DataRequired(), Length(max=1000)],
        render_kw={
            "rows": 3,
            "placeholder": "List the main products or services you will showcase...",
        },
    )

    number_of_staff = IntegerField(
        "Number of Staff (for badges)",
        validators=[Optional(), NumberRange(min=1, max=20)],
        default=2,
        render_kw={"placeholder": "2"},
    )

    special_requirements = TextAreaField(
        "Special Requirements",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "rows": 3,
            "placeholder": "Electricity needs, setup requirements, etc.",
        },
    )

    # ===== SECTION 6: Marketing & Consent =====
    referral_source = SelectField(
        "How did you hear about this exhibition opportunity?",
        choices=[
            ("", "Select source"),
            ("website", "Website"),
            ("email", "Email Invitation"),
            ("partner", "Partner Organization"),
            ("previous_exhibitor", "Previous Exhibition"),
            ("social_media", "Social Media"),
            ("colleague", "Colleague"),
            ("advertisement", "Advertisement"),
            ("other", "Other"),
        ],
        validators=[Optional()],
    )

    newsletter_signup = BooleanField("Subscribe to exhibitor updates", default=True)

    consent_photography = BooleanField(
        "Consent to photography/filming at our booth", default=True
    )

    consent_catalog = BooleanField(
        "Include our company in the event catalog", default=True
    )

    # ===== PROMO CODE =====
    promo_code = StringField(
        "Promo Code",
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "Enter code if you have one"},
    )

    def populate_package_choices(self):
        """Dynamically populate package choices from database"""
        from app.extensions import db

        packages = (
            ExhibitorPackagePrice.query.filter_by(is_active=True)
            .order_by(ExhibitorPackagePrice.price)
            .all()
        )
        self.package_type.choices = [("", "Select package")] + [
            (
                package.package_type.value,
                f"{package.name} - {package.currency} {package.price:,.0f}",
            )
            for package in packages
        ]

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
