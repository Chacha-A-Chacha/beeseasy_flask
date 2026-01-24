"""
Newsletter Subscription Model
Stores email newsletter subscriptions for event updates
"""

from datetime import datetime

from app.extensions import db


class NewsletterSubscription(db.Model):
    """Model for storing newsletter email subscriptions"""

    __tablename__ = "newsletter_subscriptions"

    id = db.Column(db.Integer, primary_key=True)

    # Email (unique - one subscription per email)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # Subscription Details
    source = db.Column(
        db.String(50), nullable=False, index=True
    )  # overlay, registration_closed, footer, contact_form

    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_verified = db.Column(db.Boolean, default=False, index=True)

    # Verification
    verification_token = db.Column(db.String(100), unique=True, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    subscribed_at = db.Column(
        db.DateTime, default=datetime.now, nullable=False, index=True
    )
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Unsubscribe tracking
    unsubscribed_at = db.Column(db.DateTime, nullable=True)
    unsubscribe_reason = db.Column(db.String(255), nullable=True)

    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Metadata (optional user info if provided later)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<NewsletterSubscription {self.email} - {'Active' if self.is_active else 'Inactive'}>"

    @property
    def is_subscribed(self):
        """Check if subscription is active"""
        return self.is_active and not self.is_deleted

    @property
    def full_name(self):
        """Get full name if available"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return None

    def verify(self):
        """Mark subscription as verified"""
        self.is_verified = True
        self.verified_at = datetime.now()
        self.verification_token = None
        self.updated_at = datetime.now()

    def unsubscribe(self, reason: str = None):
        """Unsubscribe from newsletter"""
        self.is_active = False
        self.unsubscribed_at = datetime.now()
        if reason:
            self.unsubscribe_reason = reason
        self.updated_at = datetime.now()

    def resubscribe(self):
        """Resubscribe to newsletter"""
        self.is_active = True
        self.unsubscribed_at = None
        self.unsubscribe_reason = None
        self.updated_at = datetime.now()

    def soft_delete(self):
        """Soft delete subscription"""
        self.is_deleted = True
        self.deleted_at = datetime.now()
        self.is_active = False

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "email": self.email,
            "source": self.source,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "full_name": self.full_name,
            "subscribed_at": self.subscribed_at.isoformat()
            if self.subscribed_at
            else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "unsubscribed_at": self.unsubscribed_at.isoformat()
            if self.unsubscribed_at
            else None,
        }
