"""
Optimized Event Registration Database Models for BEEASY2025
Production-ready with security, performance, and data integrity enhancements

Key Features:
- Joined Table Inheritance (JTI) for normalized schema
- Comprehensive validation and constraints
- PII protection and security measures
- Performance optimizations with proper indexing
- Atomic operations for inventory management
- Backward compatibility with existing system
- Multi-payment support
"""

import re
import secrets
import string
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Index,
    UniqueConstraint,
    and_,
    event,
    func,
    or_,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship, validates

from app.extensions import db

# ============================================
# ENUMS FOR CONSISTENT DATA
# ============================================


class RegistrationStatus(Enum):
    """Registration workflow status"""

    DRAFT = "draft"  # Started but not submitted
    PENDING = "pending"  # Submitted, awaiting payment
    PAYMENT_PENDING = "payment_pending"  # Payment initiated
    CONFIRMED = "confirmed"  # Payment confirmed, active
    CANCELLED = "cancelled"  # Cancelled by user/admin
    REFUNDED = "refunded"  # Payment refunded
    WAITLISTED = "waitlisted"  # On waitlist
    EXPIRED = "expired"  # Registration expired


class PaymentStatus(Enum):
    """Payment processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    PARTIALLY_PAID = "partially_paid"


class PaymentMethod(Enum):
    """Available payment methods"""

    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    INVOICE = "invoice"
    FREE = "free"
    CASH = "cash"


class PaymentType(Enum):
    """Type of payment transaction"""

    INITIAL = "initial"
    PARTIAL = "partial"
    BALANCE = "balance"
    REFUND = "refund"
    RETRY = "retry"


class AttendeeTicketType(Enum):
    """Attendee ticket categories"""

    FREE = "free"
    STANDARD = "standard"
    VIP = "vip"
    STUDENT = "student"
    GROUP = "group"
    EARLY_BIRD = "early_bird"
    SPEAKER = "speaker"
    VOLUNTEER = "volunteer"


class ExhibitorPackage(Enum):
    """Exhibitor booth packages"""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    CUSTOM = "custom"


class ProfessionalCategory(Enum):
    """Professional categories - broad classifications"""

    FARMER = "farmer"
    RESEARCHER_ACADEMIC = "researcher_academic"
    STUDENT = "student"
    GOVERNMENT_OFFICIAL = "government_official"
    NGO_NONPROFIT = "ngo_nonprofit"
    PRIVATE_SECTOR = "private_sector"
    ENTREPRENEUR = "entrepreneur"
    CONSULTANT = "consultant"
    EXTENSION_OFFICER = "extension_officer"
    COOPERATIVE_MEMBER = "cooperative_member"
    INVESTOR = "investor"
    MEDIA_JOURNALIST = "media_journalist"
    POLICY_MAKER = "policy_maker"
    CONSERVATIONIST = "conservationist"
    EDUCATOR = "educator"
    OTHER = "other"


class IndustryCategory(Enum):
    """Industry categories for exhibitors - broad classifications"""

    AGRICULTURE_INPUTS = "agriculture_inputs"
    EQUIPMENT_MACHINERY = "equipment_machinery"
    PROCESSING_PACKAGING = "processing_packaging"
    TECHNOLOGY_INNOVATION = "technology_innovation"
    FINANCIAL_SERVICES = "financial_services"
    TRAINING_EDUCATION = "training_education"
    RESEARCH_DEVELOPMENT = "research_development"
    CONSULTING_ADVISORY = "consulting_advisory"
    CONSERVATION_ENVIRONMENT = "conservation_environment"
    CERTIFICATION_STANDARDS = "certification_standards"
    LOGISTICS_SUPPLY_CHAIN = "logistics_supply_chain"
    MARKETING_TRADE = "marketing_trade"
    GOVERNMENT_AGENCY = "government_agency"
    NGO_DEVELOPMENT = "ngo_development"
    MEDIA_COMMUNICATIONS = "media_communications"
    HEALTHCARE_NUTRITION = "healthcare_nutrition"
    TOURISM_HOSPITALITY = "tourism_hospitality"
    OTHER = "other"


# ============================================
# HELPER FUNCTIONS
# ============================================


def generate_reference_number(prefix: str = "BEE") -> str:
    """Generate unique reference number"""
    timestamp = datetime.now().strftime("%Y%m%d")
    random_str = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
    )
    return f"{prefix}{timestamp}{random_str}"


def generate_confirmation_code() -> str:
    """Generate short confirmation code"""
    return secrets.token_urlsafe(6).upper()[:8]


def validate_email_format(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def sanitize_phone(phone: str) -> str:
    """Sanitize phone number"""
    return re.sub(r"[^\d+\-\s]", "", phone).strip()


# ============================================
# PRICING CONFIGURATION MODELS
# ============================================


class TicketPrice(db.Model):
    """Ticket pricing configuration with inventory management"""

    __tablename__ = "ticket_prices"

    id = db.Column(db.Integer, primary_key=True)
    ticket_type = db.Column(db.Enum(AttendeeTicketType), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    currency = db.Column(db.String(3), default="TZS", nullable=False)

    # Availability
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    max_quantity = db.Column(db.Integer)
    current_quantity = db.Column(db.Integer, default=0, nullable=False)

    # Early bird pricing
    early_bird_price = db.Column(db.Numeric(10, 2))
    early_bird_deadline = db.Column(db.DateTime)

    # Inclusions
    includes_lunch = db.Column(db.Boolean, default=False)
    includes_materials = db.Column(db.Boolean, default=False)
    includes_certificate = db.Column(db.Boolean, default=False)
    includes_networking = db.Column(db.Boolean, default=True)

    # Optimistic locking
    version = db.Column(db.Integer, default=1, nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        CheckConstraint("price >= 0", name="check_ticket_price_positive"),
        CheckConstraint(
            "current_quantity >= 0", name="check_current_quantity_positive"
        ),
        CheckConstraint(
            "currency IN ('USD', 'KES', 'TZS', 'UGX', 'EUR', 'GBP')",
            name="check_valid_currency",
        ),
        Index("idx_ticket_active_type", "is_active", "ticket_type"),
    )

    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}

    @validates("currency")
    def validate_currency(self, key, value):
        valid_currencies = ["USD", "KES", "TZS", "UGX", "EUR", "GBP"]
        if value not in valid_currencies:
            raise ValueError(f"Currency must be one of {valid_currencies}")
        return value

    def get_current_price(self) -> Decimal:
        """Get current price based on early bird deadline"""
        if self.early_bird_price and self.early_bird_deadline:
            if datetime.now() < self.early_bird_deadline:
                return Decimal(str(self.early_bird_price))
        return Decimal(str(self.price))

    def is_available(self) -> bool:
        """Check if tickets are still available"""
        if not self.is_active:
            return False
        if self.max_quantity and self.current_quantity >= self.max_quantity:
            return False
        return True

    def claim_tickets(self, quantity: int = 1) -> bool:
        """
        Atomically claim tickets with race condition prevention
        Returns True if successful, raises ValueError if not available
        """
        result = db.session.execute(
            db.update(TicketPrice)
            .where(
                TicketPrice.id == self.id,
                TicketPrice.is_active.is_(True),
                or_(
                    TicketPrice.max_quantity.is_(None),
                    TicketPrice.current_quantity + quantity <= TicketPrice.max_quantity,
                ),
            )
            .values(
                current_quantity=TicketPrice.current_quantity + quantity,
                version=TicketPrice.version + 1,
            )
        )

        if result.rowcount == 0:
            raise ValueError(f"Ticket {self.name} is no longer available")

        return True

    def release_tickets(self, quantity: int = 1) -> bool:
        """Release claimed tickets (e.g., on cancellation)"""
        result = db.session.execute(
            db.update(TicketPrice)
            .where(TicketPrice.id == self.id, TicketPrice.current_quantity >= quantity)
            .values(
                current_quantity=TicketPrice.current_quantity - quantity,
                version=TicketPrice.version + 1,
            )
        )
        return result.rowcount > 0

    def __repr__(self):
        return f"<TicketPrice {self.name} - {self.currency}{self.price}>"


class ExhibitorPackagePrice(db.Model):
    """Exhibitor package pricing with inventory management"""

    __tablename__ = "exhibitor_package_prices"

    id = db.Column(db.Integer, primary_key=True)
    package_type = db.Column(db.Enum(ExhibitorPackage), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="TSH", nullable=False)

    # Booth specifications
    booth_size = db.Column(db.String(50))
    included_passes = db.Column(db.Integer, default=2)

    # Inclusions
    includes_electricity = db.Column(db.Boolean, default=False)
    includes_wifi = db.Column(db.Boolean, default=False)
    includes_furniture = db.Column(db.Boolean, default=True)
    includes_catalog_listing = db.Column(db.Boolean, default=True)
    includes_social_media = db.Column(db.Boolean, default=False)
    includes_speaking_slot = db.Column(db.Boolean, default=False)
    includes_workshop = db.Column(db.Boolean, default=False)

    # Features stored as JSON for flexibility
    features = db.Column(JSON)

    # Availability
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    max_quantity = db.Column(db.Integer)
    current_quantity = db.Column(db.Integer, default=0, nullable=False)

    # Optimistic locking
    version = db.Column(db.Integer, default=1, nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="check_package_price_positive"),
        CheckConstraint(
            "current_quantity >= 0", name="check_package_quantity_positive"
        ),
        CheckConstraint(
            "currency IN ('USD', 'KES', 'TZS', 'UGX', 'EUR', 'GBP')",
            name="check_package_valid_currency",
        ),
        Index("idx_package_active_type", "is_active", "package_type"),
    )

    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}

    def is_available(self) -> bool:
        """Check if package is still available"""
        if not self.is_active:
            return False
        if self.max_quantity and self.current_quantity >= self.max_quantity:
            return False
        return True

    def claim_package(self) -> bool:
        """Atomically claim package"""
        result = db.session.execute(
            db.update(ExhibitorPackagePrice)
            .where(
                ExhibitorPackagePrice.id == self.id,
                ExhibitorPackagePrice.is_active.is_(True),
                or_(
                    ExhibitorPackagePrice.max_quantity.is_(None),
                    ExhibitorPackagePrice.current_quantity
                    < ExhibitorPackagePrice.max_quantity,
                ),
            )
            .values(
                current_quantity=ExhibitorPackagePrice.current_quantity + 1,
                version=ExhibitorPackagePrice.version + 1,
            )
        )

        if result.rowcount == 0:
            raise ValueError(f"Package {self.name} is no longer available")

        return True

    def release_package(self) -> bool:
        """Release claimed package"""
        result = db.session.execute(
            db.update(ExhibitorPackagePrice)
            .where(
                ExhibitorPackagePrice.id == self.id,
                ExhibitorPackagePrice.current_quantity > 0,
            )
            .values(
                current_quantity=ExhibitorPackagePrice.current_quantity - 1,
                version=ExhibitorPackagePrice.version + 1,
            )
        )
        return result.rowcount > 0

    def __repr__(self):
        return f"<ExhibitorPackage {self.name} - {self.currency}{self.price}>"


class AddOnItem(db.Model):
    """Add-on items/services available for purchase"""

    __tablename__ = "addon_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)

    # Applicability
    for_attendees = db.Column(db.Boolean, default=False)
    for_exhibitors = db.Column(db.Boolean, default=True)

    # Restrictions
    max_quantity_per_registration = db.Column(db.Integer)
    requires_approval = db.Column(db.Boolean, default=False)

    # Availability
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    available_from = db.Column(db.DateTime)
    available_until = db.Column(db.DateTime)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="check_addon_price_positive"),
        CheckConstraint(
            "currency IN ('USD', 'KES', 'TZS', 'UGX', 'EUR', 'GBP')",
            name="check_addon_valid_currency",
        ),
        Index(
            "idx_addon_active_applicability",
            "is_active",
            "for_attendees",
            "for_exhibitors",
        ),
    )

    def is_available(self) -> bool:
        """Check if add-on is currently available"""
        if not self.is_active:
            return False
        now = datetime.now()
        if self.available_from and now < self.available_from:
            return False
        if self.available_until and now > self.available_until:
            return False
        return True

    def __repr__(self):
        return f"<AddOn {self.name} - {self.currency}{self.price}>"


# ============================================
# BASE REGISTRATION MODEL
# ============================================


class Registration(db.Model):
    """
    Base registration model using Joined Table Inheritance (JTI)
    Contains only shared fields across all registration types
    """

    __tablename__ = "registrations"

    id = db.Column(db.Integer, primary_key=True)

    # Registration identification
    reference_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    confirmation_code = db.Column(db.String(20), unique=True, nullable=False)

    # Polymorphic discriminator
    registration_type = db.Column(db.String(20), nullable=False, index=True)

    # Status tracking
    status = db.Column(
        db.Enum(RegistrationStatus),
        default=RegistrationStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Contact Information
    first_name = db.Column(db.String(100), nullable=False, index=True)
    last_name = db.Column(db.String(100), nullable=False, index=True)

    email = db.Column(db.String(255), nullable=False, index=True)
    phone_country_code = db.Column(db.String(10), default="+254")
    phone_number = db.Column(db.String(20))

    # Organization (optional for attendees, required for exhibitors)
    organization = db.Column(db.String(255))
    job_title = db.Column(db.String(150))

    # Location
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))

    # QR Code for check-in
    qr_code_data = db.Column(db.String(500))
    qr_code_image_url = db.Column(db.String(500))

    # Consent and preferences
    consent_photography = db.Column(db.Boolean, default=True)
    consent_networking = db.Column(db.Boolean, default=True)
    consent_data_sharing = db.Column(db.Boolean, default=False)
    newsletter_signup = db.Column(db.Boolean, default=True)

    # Marketing
    referral_source = db.Column(db.String(100))

    # Admin management
    admin_notes = db.Column(db.Text)
    internal_tags = db.Column(JSON)  # For admin categorization

    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.String(255))

    # Timestamps
    created_at = db.Column(
        db.DateTime, default=datetime.now, nullable=False, index=True
    )
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    confirmed_at = db.Column(db.DateTime)

    # Optimistic locking
    version = db.Column(db.Integer, default=1, nullable=False)

    # Polymorphic configuration
    __mapper_args__ = {
        "polymorphic_on": registration_type,
        "version_id_col": version,
        "version_id_generator": False,
        "with_polymorphic": "*",
    }

    # Relationships
    payments = relationship(
        "Payment",
        back_populates="registration",
        cascade="all, delete-orphan",
        lazy="select",
    )
    addon_purchases = relationship(
        "AddOnPurchase",
        back_populates="registration",
        cascade="all, delete-orphan",
        lazy="select",
    )
    email_logs = relationship(
        "EmailLog",
        back_populates="registration",
        cascade="all, delete-orphan",
        lazy="select",
    )
    created_by = relationship("User", back_populates="registrations")

    __table_args__ = (
        UniqueConstraint(
            "email", "registration_type", "is_deleted", name="uq_email_type_active"
        ),
        CheckConstraint(
            r"email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'",
            name="check_valid_email",
        ),
        CheckConstraint(
            r"phone_country_code ~ '^\+[0-9]{1,4}$'", name="check_valid_country_code"
        ),
        Index("idx_status_created", "status", "created_at"),
        Index("idx_email_lower", func.lower("email")),
        Index("idx_reference_number", "reference_number"),
        Index("idx_type_status", "registration_type", "status"),
        Index("idx_deleted", "is_deleted", "deleted_at"),
    )

    def __init__(self, **kwargs):
        super(Registration, self).__init__(**kwargs)
        if not self.reference_number:
            self.reference_number = generate_reference_number()
        if not self.confirmation_code:
            self.confirmation_code = generate_confirmation_code()

    @hybrid_property
    def computed_full_name(self) -> str:
        """Computed full name from first and last name"""
        return f"{self.first_name} {self.last_name}"

    @hybrid_property
    def full_phone(self) -> Optional[str]:
        """Get full phone number with country code"""
        if self.phone_number:
            return f"{self.phone_country_code} {self.phone_number}"
        return None

    @validates("email")
    def validate_email(self, key, value):
        """Validate and normalize email"""
        if not value:
            raise ValueError("Email is required")

        value = value.lower().strip()

        if not validate_email_format(value):
            raise ValueError("Invalid email format")

        return value

    @validates("phone_number")
    def validate_phone_number(self, key, value):
        """Sanitize phone number"""
        if value:
            return sanitize_phone(value)
        return value

    @validates("first_name", "last_name")
    def validate_names(self, key, value):
        """Validate name fields"""
        if value:
            value = value.strip()
            if len(value) < 2:
                raise ValueError(f"{key} must be at least 2 characters")
        return value

    def get_total_amount_due(self) -> Decimal:
        """Calculate total amount to be paid (abstract method)"""
        raise NotImplementedError("Subclasses must implement get_total_amount_due()")

    def get_total_paid(self) -> Decimal:
        """Get total amount paid across all completed payments"""
        return sum(
            Decimal(str(p.total_amount))
            for p in self.payments
            if p.payment_status == PaymentStatus.COMPLETED
        )

    def get_total_refunded(self) -> Decimal:
        """Get total amount refunded"""
        return sum(
            Decimal(str(p.refund_amount))
            for p in self.payments
            if p.payment_status
            in [PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED]
        )

    def get_balance_due(self) -> Decimal:
        """Calculate outstanding balance"""
        total_due = self.get_total_amount_due()
        total_paid = self.get_total_paid()
        total_refunded = self.get_total_refunded()
        return total_due - (total_paid - total_refunded)

    def is_fully_paid(self) -> bool:
        """Check if registration is fully paid"""
        return self.get_balance_due() <= 0

    def soft_delete(self, deleted_by: str):
        """Soft delete the registration"""
        self.is_deleted = True
        self.deleted_at = datetime.now()
        self.deleted_by = deleted_by
        self.status = RegistrationStatus.CANCELLED

    def to_dict(self, include_pii: bool = False) -> Dict[str, Any]:
        """
        Serialize registration to dictionary with PII protection

        Args:
            include_pii: If False, redacts sensitive information
        """
        data = {
            "id": self.id,
            "reference_number": self.reference_number,
            "confirmation_code": self.confirmation_code,
            "registration_type": self.registration_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat()
            if self.confirmed_at
            else None,
        }

        if include_pii:
            data.update(
                {
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                    "email": self.email,
                    "phone": self.full_phone,
                    "organization": self.organization,
                    "country": self.country,
                    "city": self.city,
                }
            )
        else:
            # Redact PII
            data.update(
                {
                    "first_name": self.first_name[0] + "***",
                    "last_name": self.last_name[0] + "***",
                    "email": self.email.split("@")[0][:2]
                    + "***@"
                    + self.email.split("@")[1],
                }
            )

        return data

    def __repr__(self):
        return f"<Registration {self.reference_number[:15]}... - {self.status.value}>"


# ============================================
# ATTENDEE REGISTRATION MODEL
# ============================================


class AttendeeRegistration(Registration):
    """Attendee-specific registration details using Joined Table Inheritance"""

    __tablename__ = "attendee_registrations"

    id = db.Column(db.Integer, db.ForeignKey("registrations.id"), primary_key=True)

    # Ticket information
    ticket_type = db.Column(
        db.Enum(AttendeeTicketType),
        nullable=False,
        default=AttendeeTicketType.FREE,
        index=True,
    )
    ticket_price_id = db.Column(db.Integer, db.ForeignKey("ticket_prices.id"))

    # Professional information (simplified)
    professional_category = db.Column(db.Enum(ProfessionalCategory), index=True)

    # Event preferences (consolidated from 4 fields to 1)
    event_preferences = db.Column(
        JSON
    )  # Combines: session_interests, networking_goals, workshop_preferences, topics_of_interest

    # Dietary and accessibility (operational - keep)
    dietary_requirement = db.Column(db.String(50))
    dietary_notes = db.Column(db.Text)
    accessibility_needs = db.Column(db.Text)
    special_requirements = db.Column(db.Text)

    # Travel and visa (operational - keep)
    needs_visa_letter = db.Column(db.Boolean, default=False)
    visa_letter_sent = db.Column(db.Boolean, default=False)
    visa_letter_sent_at = db.Column(db.DateTime)

    # Check-in tracking
    checked_in = db.Column(db.Boolean, default=False, index=True)
    checked_in_at = db.Column(db.DateTime)
    checked_in_by = db.Column(db.String(255))
    badge_printed = db.Column(db.Boolean, default=False)

    __mapper_args__ = {
        "polymorphic_identity": "attendee",
    }

    # Relationships
    ticket_price = relationship(
        "TicketPrice", backref="attendee_registrations", lazy="joined"
    )

    __table_args__ = (
        # Index('idx_attendee_ticket_status', 'ticket_type', 'status'),
        Index("idx_attendee_checkin", "checked_in", "checked_in_at"),
    )

    def get_base_price(self) -> Decimal:
        """Get base ticket price"""
        if self.ticket_price:
            return Decimal(str(self.ticket_price.price))
        return Decimal("0.00")

    def get_total_amount_due(self) -> Decimal:
        """Calculate total amount due for attendee"""
        base_price = self.get_base_price()

        # Add add-ons
        addons_total = sum(
            Decimal(str(addon.total_price)) for addon in self.addon_purchases
        )

        return base_price + addons_total

    def check_in(self, checked_in_by: str):
        """Mark attendee as checked in"""
        self.checked_in = True
        self.checked_in_at = datetime.utcnow()
        self.checked_in_by = checked_in_by

    def __repr__(self):
        return f"<AttendeeRegistration {self.reference_number[:15]}... - {self.ticket_type.value}>"


# ============================================
# EXHIBITOR REGISTRATION MODEL - CLEANED
# ============================================


class ExhibitorRegistration(Registration):
    """Exhibitor-specific registration details using Joined Table Inheritance"""

    __tablename__ = "exhibitor_registrations"

    id = db.Column(db.Integer, db.ForeignKey("registrations.id"), primary_key=True)

    # Company information (simplified - single name only)
    company_legal_name = db.Column(db.String(255), nullable=False, index=True)
    company_country = db.Column(db.String(100), nullable=False)
    company_address = db.Column(db.Text, nullable=False)
    company_website = db.Column(db.String(255))

    # Simplified contacts - remove duplicate company email/phone (use primary contact)
    # Remove secondary and billing contacts - too much
    alternate_contact_email = db.Column(db.String(255))  # Single backup contact

    # Company profile
    industry_category = db.Column(db.Enum(IndustryCategory), nullable=False, index=True)
    company_description = db.Column(db.Text, nullable=False)

    # Package selection
    package_type = db.Column(db.Enum(ExhibitorPackage), nullable=False, index=True)
    package_price_id = db.Column(
        db.Integer, db.ForeignKey("exhibitor_package_prices.id")
    )

    # Booth assignment (operational - keep)
    booth_number = db.Column(db.String(20), index=True)
    booth_assigned = db.Column(db.Boolean, default=False)
    booth_assigned_at = db.Column(db.DateTime)
    booth_assigned_by = db.Column(db.String(255))

    # Booth requirements (operational - keep)
    number_of_staff = db.Column(db.Integer, default=2)
    exhibitor_badges_needed = db.Column(db.Integer, default=2)
    badges_generated = db.Column(db.Boolean, default=False)

    # Products and requirements (simplified)
    products_to_exhibit = db.Column(db.Text)  # Changed from JSONB to simple text
    special_requirements = db.Column(db.Text)

    # Admin management (operational - keep)
    exhibitor_manual_sent = db.Column(db.Boolean, default=False)
    exhibitor_manual_sent_at = db.Column(db.DateTime)
    contract_signed = db.Column(db.Boolean, default=False)
    contract_signed_at = db.Column(db.DateTime)
    contract_url = db.Column(db.String(500))

    # Lead tracking (operational - keep)
    lead_retrieval_access = db.Column(db.Boolean, default=False)
    lead_retrieval_activated = db.Column(db.Boolean, default=False)
    total_leads_captured = db.Column(db.Integer, default=0)

    __mapper_args__ = {
        "polymorphic_identity": "exhibitor",
    }

    # Relationships
    package_price = relationship(
        "ExhibitorPackagePrice", backref="exhibitor_registrations", lazy="joined"
    )

    __table_args__ = (
        Index("idx_exhibitor_booth", "booth_number", "booth_assigned"),
        Index("idx_exhibitor_company", "company_legal_name"),
    )

    def get_base_price(self) -> Decimal:
        """Get base package price"""
        if self.package_price:
            return Decimal(str(self.package_price.price))
        return Decimal("0.00")

    def get_total_amount_due(self) -> Decimal:
        """Calculate total amount due for exhibitor"""
        base_price = self.get_base_price()

        # Add add-ons
        addons_total = sum(
            Decimal(str(addon.total_price)) for addon in self.addon_purchases
        )

        return base_price + addons_total

    def assign_booth(self, booth_number: str, assigned_by: str):
        """Assign booth to exhibitor"""
        self.booth_number = booth_number
        self.booth_assigned = True
        self.booth_assigned_at = datetime.utcnow()
        self.booth_assigned_by = assigned_by

    def __repr__(self):
        return f"<ExhibitorRegistration {self.reference_number[:15]}... - {self.company_legal_name[:30]}>"


# ============================================
# ADD-ON PURCHASE MODEL
# ============================================


class AddOnPurchase(db.Model):
    """Track add-on items purchased with registration"""

    __tablename__ = "addon_purchases"

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(
        db.Integer, db.ForeignKey("registrations.id"), nullable=False, index=True
    )
    addon_id = db.Column(
        db.Integer, db.ForeignKey("addon_items.id"), nullable=False, index=True
    )

    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)

    # Status
    approved = db.Column(db.Boolean, default=True)
    approved_by = db.Column(db.String(255))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)

    # Notes
    special_instructions = db.Column(db.Text)

    # Fulfillment
    fulfilled = db.Column(db.Boolean, default=False)
    fulfilled_at = db.Column(db.DateTime)
    fulfillment_notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    addon_item = relationship("AddOnItem", backref="purchases", lazy="joined")
    registration = relationship("Registration", back_populates="addon_purchases")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_addon_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_addon_unit_price_positive"),
        CheckConstraint("total_price >= 0", name="check_addon_total_price_positive"),
        Index("idx_addon_purchase_registration", "registration_id", "addon_id"),
    )

    def __init__(self, **kwargs):
        super(AddOnPurchase, self).__init__(**kwargs)
        # Auto-calculate total price
        if self.quantity and self.unit_price:
            self.total_price = Decimal(str(self.unit_price)) * self.quantity

    def approve(self, approved_by: str):
        """Approve add-on purchase"""
        self.approved = True
        self.approved_by = approved_by
        self.approved_at = datetime.now()

    def reject(self, rejected_by: str, reason: str):
        """Reject add-on purchase"""
        self.approved = False
        self.approved_by = rejected_by
        self.approved_at = datetime.now()
        self.rejection_reason = reason

    def __repr__(self):
        addon_name = self.addon_item.name if self.addon_item else "Unknown"
        return f"<AddOnPurchase {addon_name} x{self.quantity}>"
