from datetime import datetime
from app.extensions import db
from enum import Enum


class RegistrationType(Enum):
    ATTENDEE = "attendee"
    EXHIBITOR = "exhibitor"


class Registration(db.Model):
    """Event registration record for attendees and exhibitors."""

    __tablename__ = "registrations"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(20), index=True)
    organization = db.Column(db.String(150))
    category = db.Column(db.Enum(RegistrationType), nullable=False, index=True)
    payment_status = db.Column(db.String(20), default="pending", index=True)
    amount_paid = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Foreign Key to User (who created the record, optional)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationship back to User
    created_by = db.relationship("User", back_populates="registrations", lazy="joined")

    # --- Model Methods ---
    def mark_as_paid(self, amount: float):
        """Mark registration as paid."""
        self.payment_status = "paid"
        self.amount_paid = amount

    def to_dict(self) -> dict:
        """Serialize record for JSON or export."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "organization": self.organization,
            "category": self.category.value,
            "payment_status": self.payment_status,
            "amount_paid": self.amount_paid,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by.name if self.created_by else None
        }

    def __repr__(self):
        return f"<Registration {self.full_name} ({self.category.value})>"
