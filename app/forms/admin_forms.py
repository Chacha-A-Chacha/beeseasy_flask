"""
Admin forms for BEEASY2025 management system
Handles forms for admin operations including user management, payments, tickets, etc.
"""

from datetime import datetime
from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DateTimeField,
    DecimalField,
    FieldList,
    FormField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
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

# ============================================
# USER MANAGEMENT FORMS
# ============================================


class UserForm(FlaskForm):
    """Form for creating/editing admin users"""

    name = StringField(
        "Full Name",
        validators=[DataRequired(), Length(min=2, max=120)],
        render_kw={"placeholder": "Enter full name", "class": "form-input"},
    )

    email = StringField(
        "Email Address",
        validators=[DataRequired(), Email()],
        render_kw={
            "placeholder": "user@example.com",
            "class": "form-input",
            "type": "email",
        },
    )

    role = SelectField(
        "Role",
        choices=[
            ("admin", "Administrator"),
            ("staff", "Staff Member"),
            ("organizer", "Organizer"),
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    password = StringField(
        "Password",
        validators=[Optional(), Length(min=8)],
        render_kw={
            "placeholder": "Leave blank to keep current password",
            "class": "form-input",
            "type": "password",
        },
    )

    is_active = BooleanField(
        "Active", default=True, render_kw={"class": "form-checkbox"}
    )

    submit = SubmitField("Save User", render_kw={"class": "btn btn-primary"})


# ============================================
# TICKET MANAGEMENT FORMS
# ============================================


class TicketPriceForm(FlaskForm):
    """Form for managing ticket types and pricing"""

    ticket_type = SelectField(
        "Ticket Type",
        choices=[
            ("free", "Free"),
            ("standard", "Standard"),
            ("vip", "VIP"),
            ("student", "Student"),
            ("group", "Group"),
            ("early_bird", "Early Bird"),
            ("speaker", "Speaker"),
            ("volunteer", "Volunteer"),
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    name = StringField(
        "Ticket Name",
        validators=[DataRequired(), Length(max=100)],
        render_kw={
            "placeholder": "e.g., Standard Attendee Ticket",
            "class": "form-input",
        },
    )

    description = TextAreaField(
        "Description",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Describe what this ticket includes",
            "class": "form-textarea",
        },
    )

    price = DecimalField(
        "Price",
        validators=[DataRequired(), NumberRange(min=0)],
        render_kw={"placeholder": "0.00", "class": "form-input", "step": "0.01"},
    )

    currency = SelectField(
        "Currency",
        choices=[
            ("TZS", "TZS"),
            ("USD", "USD"),
            ("KES", "KES"),
            ("UGX", "UGX"),
            ("EUR", "EUR"),
            ("GBP", "GBP"),
        ],
        default="TZS",
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    early_bird_price = DecimalField(
        "Early Bird Price",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={
            "placeholder": "Optional early bird price",
            "class": "form-input",
            "step": "0.01",
        },
    )

    early_bird_deadline = DateTimeField(
        "Early Bird Deadline",
        validators=[Optional()],
        format="%Y-%m-%dT%H:%M",
        render_kw={"class": "form-input", "type": "datetime-local"},
    )

    max_quantity = IntegerField(
        "Maximum Quantity",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={"placeholder": "Leave blank for unlimited", "class": "form-input"},
    )

    is_active = BooleanField(
        "Active", default=True, render_kw={"class": "form-checkbox"}
    )

    includes_lunch = BooleanField(
        "Includes Lunch", default=False, render_kw={"class": "form-checkbox"}
    )
    includes_materials = BooleanField(
        "Includes Materials", default=False, render_kw={"class": "form-checkbox"}
    )
    includes_certificate = BooleanField(
        "Includes Certificate", default=False, render_kw={"class": "form-checkbox"}
    )
    includes_networking = BooleanField(
        "Includes Networking", default=True, render_kw={"class": "form-checkbox"}
    )

    submit = SubmitField("Save Ticket", render_kw={"class": "btn btn-primary"})


# ============================================
# EXHIBITOR PACKAGE FORMS
# ============================================


class ExhibitorPackageForm(FlaskForm):
    """Form for managing exhibitor packages"""

    package_type = SelectField(
        "Package Type",
        choices=[
            ("bronze", "Bronze"),
            ("silver", "Silver"),
            ("gold", "Gold"),
            ("platinum", "Platinum"),
            ("custom", "Custom"),
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    name = StringField(
        "Package Name",
        validators=[DataRequired(), Length(max=100)],
        render_kw={
            "placeholder": "e.g., Gold Exhibitor Package",
            "class": "form-input",
        },
    )

    description = TextAreaField(
        "Description",
        validators=[Optional()],
        render_kw={"rows": 3, "class": "form-textarea"},
    )

    price = DecimalField(
        "Price",
        validators=[DataRequired(), NumberRange(min=0)],
        render_kw={"placeholder": "0.00", "class": "form-input", "step": "0.01"},
    )

    currency = SelectField(
        "Currency",
        choices=[
            ("TZS", "TZS"),
            ("USD", "USD"),
            ("KES", "KES"),
            ("UGX", "UGX"),
            ("EUR", "EUR"),
            ("GBP", "GBP"),
        ],
        default="TZS",
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    booth_size = StringField(
        "Booth Size",
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "e.g., 3m x 3m", "class": "form-input"},
    )

    included_passes = IntegerField(
        "Included Passes",
        validators=[Optional(), NumberRange(min=0)],
        default=2,
        render_kw={"class": "form-input"},
    )

    max_quantity = IntegerField(
        "Maximum Quantity",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={"placeholder": "Leave blank for unlimited", "class": "form-input"},
    )

    is_active = BooleanField(
        "Active", default=True, render_kw={"class": "form-checkbox"}
    )
    includes_electricity = BooleanField(
        "Includes Electricity", default=False, render_kw={"class": "form-checkbox"}
    )
    includes_wifi = BooleanField(
        "Includes WiFi", default=False, render_kw={"class": "form-checkbox"}
    )
    includes_furniture = BooleanField(
        "Includes Furniture", default=True, render_kw={"class": "form-checkbox"}
    )
    includes_catalog_listing = BooleanField(
        "Includes Catalog Listing", default=True, render_kw={"class": "form-checkbox"}
    )
    includes_social_media = BooleanField(
        "Includes Social Media", default=False, render_kw={"class": "form-checkbox"}
    )
    includes_speaking_slot = BooleanField(
        "Includes Speaking Slot", default=False, render_kw={"class": "form-checkbox"}
    )
    includes_workshop = BooleanField(
        "Includes Workshop", default=False, render_kw={"class": "form-checkbox"}
    )

    submit = SubmitField("Save Package", render_kw={"class": "btn btn-primary"})


# ============================================
# ADD-ON ITEM FORMS
# ============================================


class AddOnItemForm(FlaskForm):
    """Form for managing add-on items"""

    name = StringField(
        "Item Name",
        validators=[DataRequired(), Length(max=100)],
        render_kw={
            "placeholder": "e.g., Extra Booth Electricity",
            "class": "form-input",
        },
    )

    description = TextAreaField(
        "Description",
        validators=[Optional()],
        render_kw={"rows": 3, "class": "form-textarea"},
    )

    price = DecimalField(
        "Price",
        validators=[DataRequired(), NumberRange(min=0)],
        render_kw={"placeholder": "0.00", "class": "form-input", "step": "0.01"},
    )

    currency = SelectField(
        "Currency",
        choices=[("TZS", "TZS"), ("USD", "USD"), ("KES", "KES")],
        default="TZS",
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    for_attendees = BooleanField(
        "Available for Attendees", default=False, render_kw={"class": "form-checkbox"}
    )
    for_exhibitors = BooleanField(
        "Available for Exhibitors", default=True, render_kw={"class": "form-checkbox"}
    )

    max_quantity_per_registration = IntegerField(
        "Max Per Registration",
        validators=[Optional(), NumberRange(min=1)],
        render_kw={"placeholder": "Optional limit", "class": "form-input"},
    )

    requires_approval = BooleanField(
        "Requires Approval", default=False, render_kw={"class": "form-checkbox"}
    )
    is_active = BooleanField(
        "Active", default=True, render_kw={"class": "form-checkbox"}
    )

    submit = SubmitField("Save Add-On", render_kw={"class": "btn btn-primary"})


# ============================================
# PROMO CODE FORMS
# ============================================


class PromoCodeForm(FlaskForm):
    """Form for creating/editing promo codes"""

    code = StringField(
        "Promo Code",
        validators=[DataRequired(), Length(min=3, max=50)],
        render_kw={
            "placeholder": "e.g., EARLY2025",
            "class": "form-input",
            "style": "text-transform: uppercase;",
        },
    )

    description = StringField(
        "Description",
        validators=[Optional(), Length(max=255)],
        render_kw={
            "placeholder": "Brief description of this promo code",
            "class": "form-input",
        },
    )

    discount_type = SelectField(
        "Discount Type",
        choices=[("percentage", "Percentage (%)"), ("fixed", "Fixed Amount")],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    discount_value = DecimalField(
        "Discount Value",
        validators=[DataRequired(), NumberRange(min=0)],
        render_kw={
            "placeholder": "e.g., 10 (for 10% or $10)",
            "class": "form-input",
            "step": "0.01",
        },
    )

    max_discount_amount = DecimalField(
        "Max Discount (for percentage)",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={
            "placeholder": "Optional cap for percentage discounts",
            "class": "form-input",
            "step": "0.01",
        },
    )

    min_purchase_amount = DecimalField(
        "Minimum Purchase",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={
            "placeholder": "Optional minimum purchase required",
            "class": "form-input",
            "step": "0.01",
        },
    )

    applicable_to_attendees = BooleanField(
        "Applicable to Attendees", default=True, render_kw={"class": "form-checkbox"}
    )
    applicable_to_exhibitors = BooleanField(
        "Applicable to Exhibitors", default=False, render_kw={"class": "form-checkbox"}
    )

    max_uses = IntegerField(
        "Total Max Uses",
        validators=[Optional(), NumberRange(min=1)],
        render_kw={"placeholder": "Leave blank for unlimited", "class": "form-input"},
    )

    max_uses_per_user = IntegerField(
        "Max Uses Per User",
        validators=[Optional(), NumberRange(min=1)],
        default=1,
        render_kw={"class": "form-input"},
    )

    valid_from = DateTimeField(
        "Valid From",
        validators=[DataRequired()],
        format="%Y-%m-%dT%H:%M",
        render_kw={"class": "form-input", "type": "datetime-local"},
    )

    valid_until = DateTimeField(
        "Valid Until",
        validators=[DataRequired()],
        format="%Y-%m-%dT%H:%M",
        render_kw={"class": "form-input", "type": "datetime-local"},
    )

    campaign_name = StringField(
        "Campaign Name",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Optional campaign tracking", "class": "form-input"},
    )

    campaign_source = StringField(
        "Campaign Source",
        validators=[Optional(), Length(max=100)],
        render_kw={
            "placeholder": "e.g., email, social, partner",
            "class": "form-input",
        },
    )

    is_active = BooleanField(
        "Active", default=True, render_kw={"class": "form-checkbox"}
    )

    submit = SubmitField("Save Promo Code", render_kw={"class": "btn btn-primary"})

    def validate_valid_until(self, field):
        """Ensure valid_until is after valid_from"""
        if self.valid_from.data and field.data:
            if field.data <= self.valid_from.data:
                raise ValidationError("End date must be after start date")


# ============================================
# PAYMENT MANAGEMENT FORMS
# ============================================


class PaymentVerificationForm(FlaskForm):
    """Form for manually verifying payments"""

    transaction_id = StringField(
        "Transaction/Reference ID",
        validators=[DataRequired(), Length(max=255)],
        render_kw={
            "placeholder": "Bank reference or transaction ID",
            "class": "form-input",
        },
    )

    payment_notes = TextAreaField(
        "Verification Notes",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Add any notes about this payment verification",
            "class": "form-textarea",
        },
    )

    verified_by = HiddenField()

    submit = SubmitField("Verify Payment", render_kw={"class": "btn btn-success"})


class RefundForm(FlaskForm):
    """Form for processing refunds"""

    refund_amount = DecimalField(
        "Refund Amount",
        validators=[DataRequired(), NumberRange(min=0.01)],
        render_kw={"placeholder": "0.00", "class": "form-input", "step": "0.01"},
    )

    refund_reason = TextAreaField(
        "Refund Reason",
        validators=[DataRequired(), Length(min=10, max=500)],
        render_kw={
            "rows": 4,
            "placeholder": "Explain why this refund is being processed",
            "class": "form-textarea",
        },
    )

    refund_reference = StringField(
        "Refund Reference",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Optional external reference", "class": "form-input"},
    )

    submit = SubmitField("Process Refund", render_kw={"class": "btn btn-danger"})


# ============================================
# BOOTH ASSIGNMENT FORMS
# ============================================


class BoothAssignmentForm(FlaskForm):
    """Form for assigning booths to exhibitors"""

    booth_number = StringField(
        "Booth Number",
        validators=[DataRequired(), Length(max=20)],
        render_kw={"placeholder": "e.g., A-101", "class": "form-input"},
    )

    notes = TextAreaField(
        "Assignment Notes",
        validators=[Optional()],
        render_kw={
            "rows": 2,
            "placeholder": "Optional notes",
            "class": "form-textarea",
        },
    )

    submit = SubmitField("Assign Booth", render_kw={"class": "btn btn-primary"})


# ============================================
# EMAIL FORMS
# ============================================


class SendEmailForm(FlaskForm):
    """Form for sending custom emails to registrants"""

    subject = StringField(
        "Email Subject",
        validators=[DataRequired(), Length(max=255)],
        render_kw={"placeholder": "Email subject line", "class": "form-input"},
    )

    message = TextAreaField(
        "Message",
        validators=[DataRequired(), Length(min=10)],
        render_kw={
            "rows": 10,
            "placeholder": "Email message body",
            "class": "form-textarea",
        },
    )

    send_copy = BooleanField(
        "Send me a copy", default=False, render_kw={"class": "form-checkbox"}
    )

    submit = SubmitField("Send Email", render_kw={"class": "btn btn-primary"})


class BulkEmailForm(FlaskForm):
    """Form for sending bulk emails"""

    recipient_type = SelectField(
        "Recipients",
        choices=[
            ("all_attendees", "All Attendees"),
            ("all_exhibitors", "All Exhibitors"),
            ("confirmed_attendees", "Confirmed Attendees"),
            ("confirmed_exhibitors", "Confirmed Exhibitors"),
            ("pending_payment", "Pending Payment"),
            ("checked_in", "Checked In"),
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    subject = StringField(
        "Email Subject",
        validators=[DataRequired(), Length(max=255)],
        render_kw={"placeholder": "Email subject line", "class": "form-input"},
    )

    message = TextAreaField(
        "Message",
        validators=[DataRequired(), Length(min=10)],
        render_kw={
            "rows": 10,
            "placeholder": "Email message body",
            "class": "form-textarea",
        },
    )

    send_test = BooleanField(
        "Send test email first", default=True, render_kw={"class": "form-checkbox"}
    )
    test_email = StringField(
        "Test Email Address",
        validators=[Optional(), Email()],
        render_kw={
            "placeholder": "your@email.com",
            "class": "form-input",
            "type": "email",
        },
    )

    submit = SubmitField("Send Bulk Email", render_kw={"class": "btn btn-primary"})


# ============================================
# CONTACT RESPONSE FORMS
# ============================================


class ContactReplyForm(FlaskForm):
    """Form for replying to contact submissions"""

    reply_message = TextAreaField(
        "Reply Message",
        validators=[DataRequired(), Length(min=10)],
        render_kw={
            "rows": 8,
            "placeholder": "Your response to this inquiry",
            "class": "form-textarea",
        },
    )

    mark_resolved = BooleanField(
        "Mark as Resolved", default=True, render_kw={"class": "form-checkbox"}
    )

    submit = SubmitField("Send Reply", render_kw={"class": "btn btn-primary"})


# ============================================
# REGISTRATION EDIT FORMS
# ============================================


class EditAttendeeForm(FlaskForm):
    """Form for editing attendee registrations"""

    first_name = StringField(
        "First Name",
        validators=[DataRequired(), Length(max=100)],
        render_kw={"class": "form-input"},
    )
    last_name = StringField(
        "Last Name",
        validators=[DataRequired(), Length(max=100)],
        render_kw={"class": "form-input"},
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
        render_kw={"class": "form-input", "type": "email"},
    )
    phone_number = StringField(
        "Phone", validators=[Optional()], render_kw={"class": "form-input"}
    )
    organization = StringField(
        "Organization",
        validators=[Optional(), Length(max=255)],
        render_kw={"class": "form-input"},
    )
    job_title = StringField(
        "Job Title",
        validators=[Optional(), Length(max=150)],
        render_kw={"class": "form-input"},
    )
    country = StringField(
        "Country",
        validators=[Optional(), Length(max=100)],
        render_kw={"class": "form-input"},
    )
    city = StringField(
        "City",
        validators=[Optional(), Length(max=100)],
        render_kw={"class": "form-input"},
    )

    dietary_requirement = StringField(
        "Dietary Requirement",
        validators=[Optional()],
        render_kw={"class": "form-input"},
    )
    accessibility_needs = TextAreaField(
        "Accessibility Needs",
        validators=[Optional()],
        render_kw={"rows": 3, "class": "form-textarea"},
    )

    admin_notes = TextAreaField(
        "Admin Notes",
        validators=[Optional()],
        render_kw={"rows": 3, "class": "form-textarea"},
    )

    submit = SubmitField("Update Attendee", render_kw={"class": "btn btn-primary"})


class EditExhibitorForm(FlaskForm):
    """Form for editing exhibitor registrations"""

    first_name = StringField(
        "Contact First Name",
        validators=[DataRequired(), Length(max=100)],
        render_kw={"class": "form-input"},
    )
    last_name = StringField(
        "Contact Last Name",
        validators=[DataRequired(), Length(max=100)],
        render_kw={"class": "form-input"},
    )
    email = StringField(
        "Contact Email",
        validators=[DataRequired(), Email()],
        render_kw={"class": "form-input", "type": "email"},
    )
    phone_number = StringField(
        "Contact Phone", validators=[Optional()], render_kw={"class": "form-input"}
    )

    company_legal_name = StringField(
        "Company Name",
        validators=[DataRequired(), Length(max=255)],
        render_kw={"class": "form-input"},
    )
    company_country = StringField(
        "Company Country",
        validators=[DataRequired(), Length(max=100)],
        render_kw={"class": "form-input"},
    )
    company_address = TextAreaField(
        "Company Address",
        validators=[DataRequired()],
        render_kw={"rows": 3, "class": "form-textarea"},
    )
    company_website = StringField(
        "Website",
        validators=[Optional(), URL()],
        render_kw={"class": "form-input", "type": "url"},
    )

    number_of_staff = IntegerField(
        "Number of Staff",
        validators=[Optional(), NumberRange(min=1)],
        render_kw={"class": "form-input"},
    )

    admin_notes = TextAreaField(
        "Admin Notes",
        validators=[Optional()],
        render_kw={"rows": 3, "class": "form-textarea"},
    )

    submit = SubmitField("Update Exhibitor", render_kw={"class": "btn btn-primary"})


# ============================================
# EXCHANGE RATE FORMS
# ============================================


class ExchangeRateForm(FlaskForm):
    """Form for managing currency exchange rates"""

    from_currency = SelectField(
        "From Currency",
        choices=[
            ("USD", "USD"),
            ("TZS", "TZS"),
            ("KES", "KES"),
            ("UGX", "UGX"),
            ("EUR", "EUR"),
            ("GBP", "GBP"),
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    to_currency = SelectField(
        "To Currency",
        choices=[
            ("USD", "USD"),
            ("TZS", "TZS"),
            ("KES", "KES"),
            ("UGX", "UGX"),
            ("EUR", "EUR"),
            ("GBP", "GBP"),
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    rate = DecimalField(
        "Exchange Rate",
        validators=[DataRequired(), NumberRange(min=0.000001)],
        render_kw={
            "placeholder": "0.000000",
            "class": "form-input",
            "step": "0.000001",
        },
    )

    effective_date = DateField(
        "Effective Date",
        validators=[DataRequired()],
        render_kw={"class": "form-input", "type": "date"},
    )

    source = StringField(
        "Source",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g., manual, api, bank", "class": "form-input"},
    )

    submit = SubmitField("Save Exchange Rate", render_kw={"class": "btn btn-primary"})
