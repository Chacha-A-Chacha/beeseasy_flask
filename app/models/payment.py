"""
Payment and Supporting Models for BEEASY2025 Registration System
Continuation of registration_models.py

Includes:
- Payment model with multi-payment support
- Promo code system
- Email tracking
- Exchange rate handling
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
import secrets

from sqlalchemy import CheckConstraint, Index, UniqueConstraint, event, or_
from sqlalchemy.orm import validates, relationship
from sqlalchemy.dialects.postgresql import JSONB
from enum import Enum

from app.extensions import db
# Import enums from main models file
from app.models import PaymentStatus, PaymentMethod  # PaymentType


# ============================================
# PAYMENT MODEL
# ============================================

class Payment(db.Model):
    """
    Payment transactions for registrations
    Supports multiple payments per registration for partial payments, retries, refunds
    """
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'),
                                nullable=False, index=True)

    # Payment identification
    payment_reference = db.Column(db.String(100), unique=True, nullable=False, index=True)
    invoice_number = db.Column(db.String(50), unique=True, index=True)

    # Payment type
    # payment_type = db.Column(db.Enum(PaymentType),
    #                          default=PaymentType.INITIAL,
    #                          nullable=False)

    # Amount details
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), default=0.0)  # e.g., 0.16 for 16%
    discount_amount = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    currency = db.Column(db.String(3), default='USD', nullable=False)

    # Exchange rate (if paid in different currency)
    exchange_rate = db.Column(db.Numeric(10, 6))
    base_currency_amount = db.Column(db.Numeric(10, 2))  # Amount in base currency

    # Payment details
    payment_method = db.Column(db.Enum(PaymentMethod), nullable=False)
    payment_status = db.Column(db.Enum(PaymentStatus),
                               default=PaymentStatus.PENDING,
                               nullable=False,
                               index=True)

    # Gateway information (Stripe)
    stripe_payment_intent_id = db.Column(db.String(255), unique=True, index=True)
    stripe_checkout_session_id = db.Column(db.String(255), unique=True)
    stripe_customer_id = db.Column(db.String(255), index=True)
    stripe_charge_id = db.Column(db.String(255))
    stripe_refund_id = db.Column(db.String(255))

    # Alternative payment details
    transaction_id = db.Column(db.String(255), index=True)  # For mobile money, bank transfer
    bank_reference = db.Column(db.String(100))
    mpesa_receipt = db.Column(db.String(100))  # M-Pesa specific

    # Invoice details
    invoice_url = db.Column(db.String(500))
    invoice_generated = db.Column(db.Boolean, default=False)
    invoice_sent = db.Column(db.Boolean, default=False)
    invoice_sent_at = db.Column(db.DateTime)

    # Receipt
    receipt_number = db.Column(db.String(50))
    receipt_url = db.Column(db.String(500))
    receipt_generated = db.Column(db.Boolean, default=False)
    receipt_sent = db.Column(db.Boolean, default=False)
    receipt_sent_at = db.Column(db.DateTime)

    # Payment timeline
    payment_initiated_at = db.Column(db.DateTime, index=True)
    payment_completed_at = db.Column(db.DateTime, index=True)
    payment_failed_at = db.Column(db.DateTime)

    # Due dates (for invoice payments)
    payment_due_date = db.Column(db.DateTime, index=True)
    payment_reminder_sent = db.Column(db.Boolean, default=False)

    # Refund information
    refund_amount = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    refund_reason = db.Column(db.Text)
    refunded_at = db.Column(db.DateTime)
    refund_reference = db.Column(db.String(100))
    refund_requested_by = db.Column(db.String(255))
    refund_approved_by = db.Column(db.String(255))

    # Failure information
    failure_reason = db.Column(db.Text)
    failure_code = db.Column(db.String(50))
    retry_count = db.Column(db.Integer, default=0)

    # Admin notes
    payment_notes = db.Column(db.Text)
    verified_by = db.Column(db.String(255))  # Admin who verified manual payment
    verified_at = db.Column(db.DateTime)

    # Reconciliation
    reconciled = db.Column(db.Boolean, default=False, index=True)
    reconciled_at = db.Column(db.DateTime)
    reconciled_by = db.Column(db.String(255))

    # Metadata
    payment_metadata = db.Column(JSONB)  # Additional payment metadata
    gateway_response = db.Column(JSONB)  # Raw gateway response

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Optimistic locking
    version = db.Column(db.Integer, default=1, nullable=False)

    # Relationships
    registration = relationship('Registration', back_populates='payments')
    promo_code_usage = relationship('PromoCodeUsage', back_populates='payment',
                                    uselist=False, cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint('subtotal >= 0', name='check_subtotal_positive'),
        CheckConstraint('tax_amount >= 0', name='check_tax_positive'),
        CheckConstraint('discount_amount >= 0', name='check_discount_positive'),
        CheckConstraint('total_amount >= 0', name='check_total_positive'),
        CheckConstraint('refund_amount >= 0', name='check_refund_positive'),
        CheckConstraint("currency IN ('USD', 'KES', 'TZS', 'UGX', 'EUR', 'GBP')",
                        name='check_payment_valid_currency'),
        Index('idx_payment_status_date', 'payment_status', 'payment_completed_at'),
        Index('idx_payment_registration_status', 'registration_id', 'payment_status'),
        Index('idx_payment_method_status', 'payment_method', 'payment_status'),
        Index('idx_payment_reconciled', 'reconciled', 'reconciled_at'),
    )

    __mapper_args__ = {
        'version_id_col': version,
        'version_id_generator': False
    }

    def __init__(self, **kwargs):
        super(Payment, self).__init__(**kwargs)
        if not self.payment_reference:
            self.payment_reference = self._generate_payment_reference()
        if not self.payment_initiated_at:
            self.payment_initiated_at = datetime.utcnow()

    def _generate_payment_reference(self) -> str:
        """Generate unique payment reference"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        random_str = ''.join(secrets.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(6))
        return f"PAY{timestamp}{random_str}"

    def calculate_total(self) -> Decimal:
        """Calculate total with tax and discount"""
        subtotal = Decimal(str(self.subtotal))
        tax = Decimal(str(self.tax_amount))
        discount = Decimal(str(self.discount_amount))

        self.total_amount = subtotal + tax - discount
        return self.total_amount

    def calculate_tax(self, tax_rate: float) -> Decimal:
        """Calculate tax amount based on rate"""
        self.tax_rate = Decimal(str(tax_rate))
        self.tax_amount = Decimal(str(self.subtotal)) * self.tax_rate
        return self.tax_amount

    @validates('subtotal', 'total_amount', 'tax_amount', 'discount_amount', 'refund_amount')
    def validate_amounts(self, key, value):
        """Ensure amounts are non-negative"""
        if value is not None:
            value = Decimal(str(value))
            if value < 0:
                raise ValueError(f"{key} cannot be negative")
        return value

    @property
    def is_paid(self) -> bool:
        """Check if payment is completed"""
        return self.payment_status == PaymentStatus.COMPLETED

    @property
    def is_pending(self) -> bool:
        """Check if payment is pending"""
        return self.payment_status in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]

    @property
    def is_failed(self) -> bool:
        """Check if payment failed"""
        return self.payment_status == PaymentStatus.FAILED

    @property
    def net_amount(self) -> Decimal:
        """Get net amount after refunds"""
        return Decimal(str(self.total_amount)) - Decimal(str(self.refund_amount))

    def mark_as_completed(self, transaction_id: Optional[str] = None):
        """Mark payment as completed"""
        self.payment_status = PaymentStatus.COMPLETED
        self.payment_completed_at = datetime.utcnow()
        if transaction_id:
            self.transaction_id = transaction_id

        # Auto-generate receipt if not exists
        if not self.receipt_number:
            self.receipt_number = f"RCP{self.payment_reference[3:]}"

    def mark_as_failed(self, reason: str, error_code: Optional[str] = None):
        """Mark payment as failed"""
        self.payment_status = PaymentStatus.FAILED
        self.payment_failed_at = datetime.now()
        self.failure_reason = reason
        self.failure_code = error_code
        self.retry_count += 1

    def process_refund(self, amount: Decimal, reason: str, refunded_by: str):
        """Process a refund"""
        amount = Decimal(str(amount))

        if amount > self.net_amount:
            raise ValueError("Refund amount cannot exceed net payment amount")

        self.refund_amount = amount
        self.refund_reason = reason
        self.refunded_at = datetime.now()
        self.refund_requested_by = refunded_by

        # Update status
        if amount >= Decimal(str(self.total_amount)):
            self.payment_status = PaymentStatus.REFUNDED
        else:
            self.payment_status = PaymentStatus.PARTIALLY_REFUNDED

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Serialize payment to dictionary

        Args:
            include_sensitive: If False, excludes sensitive payment details
        """
        data = {
            "payment_reference": self.payment_reference,
            "invoice_number": self.invoice_number,
            "payment_type": self.payment_type.value,
            "total_amount": float(self.total_amount),
            "currency": self.currency,
            "payment_method": self.payment_method.value,
            "payment_status": self.payment_status.value,
            "payment_completed_at": self.payment_completed_at.isoformat() if self.payment_completed_at else None,
            "created_at": self.created_at.isoformat(),
        }

        if include_sensitive:
            data.update({
                "stripe_payment_intent_id": self.stripe_payment_intent_id,
                "transaction_id": self.transaction_id,
                "bank_reference": self.bank_reference,
            })

        return data

    def __repr__(self):
        # Truncate reference for security
        ref = self.payment_reference[:10] + "..." if len(self.payment_reference) > 10 else self.payment_reference
        return f'<Payment {ref} - {self.currency}{self.total_amount} - {self.payment_status.value}>'


# ============================================
# PROMO CODE MODELS
# ============================================

class PromoCode(db.Model):
    """Promotional/discount codes"""
    __tablename__ = 'promo_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))

    # Discount details
    discount_type = db.Column(db.String(20), nullable=False)  # 'percentage' or 'fixed'
    discount_value = db.Column(db.Numeric(10, 2), nullable=False)
    max_discount_amount = db.Column(db.Numeric(10, 2))  # Max discount for percentage
    min_purchase_amount = db.Column(db.Numeric(10, 2))  # Minimum purchase required

    # Applicability
    applicable_to_attendees = db.Column(db.Boolean, default=True)
    applicable_to_exhibitors = db.Column(db.Boolean, default=False)
    applicable_ticket_types = db.Column(JSONB)  # Specific ticket types
    applicable_packages = db.Column(JSONB)  # Specific exhibitor packages

    # Usage limits
    max_uses = db.Column(db.Integer)  # Total times code can be used
    current_uses = db.Column(db.Integer, default=0, nullable=False)
    max_uses_per_user = db.Column(db.Integer, default=1)

    # Validity period
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_until = db.Column(db.DateTime, nullable=False)

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Campaign tracking
    campaign_name = db.Column(db.String(100))
    campaign_source = db.Column(db.String(100))  # e.g., 'email', 'social', 'partner'

    # Metadata
    created_by = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    usages = relationship('PromoCodeUsage', back_populates='promo_code',
                          cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint('discount_value >= 0', name='check_discount_value_positive'),
        CheckConstraint('current_uses >= 0', name='check_current_uses_positive'),
        CheckConstraint("discount_type IN ('percentage', 'fixed')",
                        name='check_valid_discount_type'),
        CheckConstraint(
            "(discount_type = 'percentage' AND discount_value <= 100) OR discount_type = 'fixed'",
            name='check_percentage_max_100'
        ),
        Index('idx_promo_code_active', 'code', 'is_active'),
        Index('idx_promo_validity', 'valid_from', 'valid_until', 'is_active'),
    )

    @validates('code')
    def validate_code(self, key, value):
        """Validate and normalize promo code"""
        if value:
            value = value.upper().strip()
            if not value.replace('-', '').replace('_', '').isalnum():
                raise ValueError("Promo code must be alphanumeric (dashes and underscores allowed)")
        return value

    def is_valid(self) -> bool:
        """Check if promo code is currently valid (basic check)"""
        if not self.is_active:
            return False

        now = datetime.utcnow()
        if now < self.valid_from or now > self.valid_until:
            return False

        if self.max_uses and self.current_uses >= self.max_uses:
            return False

        return True

    def is_valid_for_user(self, email: str) -> bool:
        """Check if promo code is valid for specific user"""
        if not self.is_valid():
            return False

        # Check per-user limit
        if self.max_uses_per_user:
            from app.models import Registration

            usage_count = (db.session.query(PromoCodeUsage)
                           .join(Registration)
                           .filter(
                PromoCodeUsage.promo_code_id == self.id,
                Registration.email == email.lower()
            )
                           .count())

            if usage_count >= self.max_uses_per_user:
                return False

        return True

    def calculate_discount(self, amount: Decimal) -> Decimal:
        """
        Calculate discount amount

        Args:
            amount: Purchase amount to apply discount to

        Returns:
            Discount amount
        """
        amount = Decimal(str(amount))

        # Check minimum purchase
        if self.min_purchase_amount and amount < Decimal(str(self.min_purchase_amount)):
            return Decimal('0.00')

        if self.discount_type == 'percentage':
            discount = amount * (Decimal(str(self.discount_value)) / 100)

            # Apply max discount cap
            if self.max_discount_amount:
                discount = min(discount, Decimal(str(self.max_discount_amount)))

            return discount.quantize(Decimal('0.01'))
        else:  # fixed
            # Don't exceed purchase amount
            return min(Decimal(str(self.discount_value)), amount)

    def use_code(self) -> bool:
        """
        Increment usage count atomically
        Returns True if successful, False if limit reached
        """
        result = db.session.execute(
            db.update(PromoCode)
            .where(
                PromoCode.id == self.id,
                PromoCode.is_active == True,
                or_(
                    PromoCode.max_uses.is_(None),
                    PromoCode.current_uses < PromoCode.max_uses
                )
            )
            .values(current_uses=PromoCode.current_uses + 1)
        )

        return result.rowcount > 0

    def __repr__(self):
        return f'<PromoCode {self.code} - {self.discount_value}{"%" if self.discount_type == "percentage" else self.currency}>'


class PromoCodeUsage(db.Model):
    """Track promo code usage per registration"""
    __tablename__ = 'promo_code_usage'

    id = db.Column(db.Integer, primary_key=True)
    promo_code_id = db.Column(db.Integer, db.ForeignKey('promo_codes.id'),
                              nullable=False, index=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'),
                                nullable=False, index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'))

    discount_amount = db.Column(db.Numeric(10, 2), nullable=False)
    original_amount = db.Column(db.Numeric(10, 2), nullable=False)
    final_amount = db.Column(db.Numeric(10, 2), nullable=False)

    used_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    promo_code = relationship('PromoCode', back_populates='usages')
    registration = relationship('Registration')
    payment = relationship('Payment', back_populates='promo_code_usage')

    __table_args__ = (
        UniqueConstraint('promo_code_id', 'registration_id',
                         name='uq_promo_registration'),
        CheckConstraint('discount_amount >= 0', name='check_usage_discount_positive'),
        Index('idx_promo_usage_date', 'promo_code_id', 'used_at'),
    )

    def __repr__(self):
        return f'<PromoCodeUsage {self.promo_code.code if self.promo_code else "N/A"} - ${self.discount_amount}>'


# ============================================
# EMAIL LOG MODEL
# ============================================

class EmailLog(db.Model):
    """Track emails sent to registrants"""
    __tablename__ = 'email_logs'

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), index=True)

    recipient_email = db.Column(db.String(255), nullable=False, index=True)
    recipient_name = db.Column(db.String(255))

    email_type = db.Column(db.String(50), nullable=False, index=True)
    template_name = db.Column(db.String(100))
    subject = db.Column(db.String(255))

    # Status
    status = db.Column(db.String(20), default='sent', nullable=False, index=True)
    error_message = db.Column(db.Text)

    # Email service provider details
    message_id = db.Column(db.String(255), unique=True)
    provider = db.Column(db.String(50))  # 'sendgrid', 'ses', 'smtp', etc.

    # Tracking
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    delivered_at = db.Column(db.DateTime)
    opened_at = db.Column(db.DateTime)
    first_opened_at = db.Column(db.DateTime)
    open_count = db.Column(db.Integer, default=0)
    clicked_at = db.Column(db.DateTime)
    click_count = db.Column(db.Integer, default=0)
    bounced_at = db.Column(db.DateTime)
    bounce_type = db.Column(db.String(50))  # 'hard', 'soft'
    complained_at = db.Column(db.DateTime)  # Spam complaint

    # Metadata
    email_metadata = db.Column(JSONB)

    # Relationships
    registration = relationship('Registration', back_populates='email_logs')

    __table_args__ = (
        Index('idx_email_type_status', 'email_type', 'status'),
        Index('idx_email_sent_date', 'sent_at'),
        Index('idx_email_recipient', 'recipient_email', 'sent_at'),
    )

    @validates('status')
    def validate_status(self, key, value):
        """Validate email status"""
        valid_statuses = ['pending', 'sent', 'delivered', 'opened', 'clicked',
                          'bounced', 'failed', 'complained']
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return value

    def mark_opened(self):
        """Mark email as opened"""
        if not self.first_opened_at:
            self.first_opened_at = datetime.utcnow()
        self.opened_at = datetime.utcnow()
        self.open_count += 1
        if self.status == 'delivered' or self.status == 'sent':
            self.status = 'opened'

    def mark_clicked(self):
        """Mark email link as clicked"""
        self.clicked_at = datetime.utcnow()
        self.click_count += 1
        if self.status in ['delivered', 'sent', 'opened']:
            self.status = 'clicked'

    def __repr__(self):
        return f'<EmailLog {self.email_type} to {self.recipient_email[:20]}... - {self.status}>'


# ============================================
# EXCHANGE RATE MODEL
# ============================================

class ExchangeRate(db.Model):
    """Track exchange rates for multi-currency support"""
    __tablename__ = 'exchange_rates'

    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(3), nullable=False, index=True)
    to_currency = db.Column(db.String(3), nullable=False, index=True)
    rate = db.Column(db.Numeric(10, 6), nullable=False)

    # Validity
    effective_date = db.Column(db.Date, nullable=False, index=True)
    expiry_date = db.Column(db.Date)

    # Source
    source = db.Column(db.String(100))  # 'manual', 'api', 'bank'

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(255))

    __table_args__ = (
        UniqueConstraint('from_currency', 'to_currency', 'effective_date',
                         name='uq_currency_pair_date'),
        CheckConstraint('rate > 0', name='check_rate_positive'),
        CheckConstraint("from_currency IN ('USD', 'KES', 'TZS', 'UGX', 'EUR', 'GBP')",
                        name='check_from_currency_valid'),
        CheckConstraint("to_currency IN ('USD', 'KES', 'TZS', 'UGX', 'EUR', 'GBP')",
                        name='check_to_currency_valid'),
        Index('idx_currency_pair_date', 'from_currency', 'to_currency', 'effective_date'),
    )

    @classmethod
    def get_current_rate(cls, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Get current exchange rate for currency pair"""
        if from_currency == to_currency:
            return Decimal('1.0')

        rate = (cls.query
                .filter_by(from_currency=from_currency, to_currency=to_currency)
                .filter(cls.effective_date <= datetime.now().date())
                .order_by(cls.effective_date.desc())
                .first())

        if rate:
            return Decimal(str(rate.rate))

        return None

    @classmethod
    def convert_amount(cls, amount: Decimal, from_currency: str,
                       to_currency: str) -> Optional[Decimal]:
        """Convert amount from one currency to another"""
        rate = cls.get_current_rate(from_currency, to_currency)
        if rate:
            return (Decimal(str(amount)) * rate).quantize(Decimal('0.01'))
        return None

    def __repr__(self):
        return f'<ExchangeRate {self.from_currency}/{self.to_currency} = {self.rate}>'


# ============================================
# EVENT LISTENERS
# ============================================

# @event.listens_for(Payment, 'before_insert')
# def generate_invoice_number(mapper, connection, target):
#     """Auto-generate invoice number if not provided"""
#     if not target.invoice_number and target.payment_type == PaymentType.INITIAL:
#         timestamp = datetime.now().strftime('%Y%m')
#         random_str = ''.join(secrets.choice('0123456789') for _ in range(6))
#         target.invoice_number = f"INV{timestamp}{random_str}"


@event.listens_for(Payment, 'before_update')
def update_registration_status(mapper, connection, target):
    """Update registration status when payment completes"""
    from app.models.registration import Registration, RegistrationStatus

    # Check if payment status changed to completed
    if target.payment_status == PaymentStatus.COMPLETED and target.payment_completed_at:
        # This will be handled in the service layer to avoid circular imports
        pass
