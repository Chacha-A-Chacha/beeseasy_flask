"""
Contact Message Model
Stores contact form submissions for admin review and response tracking
"""

from datetime import datetime

from app.extensions import db


class ContactMessage(db.Model):
    """Model for storing contact form submissions"""

    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Contact Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(20))
    country_code = db.Column(db.String(10), default="+254")
    organization = db.Column(db.String(255))
    role = db.Column(db.String(100))

    # Inquiry Details
    inquiry_type = db.Column(db.String(50), nullable=False, index=True)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # Preferences
    preferred_contact_method = db.Column(db.String(20), default="email")
    newsletter_signup = db.Column(db.Boolean, default=False)

    # Status and Response Tracking
    status = db.Column(
        db.String(20), default="new", index=True
    )  # new, in_progress, resolved, closed
    priority = db.Column(db.String(20), default="normal")  # low, normal, high, urgent
    assigned_to = db.Column(db.String(255))  # Admin user name

    # Response tracking
    responded_at = db.Column(db.DateTime)
    responded_by = db.Column(db.String(255))
    response_message = db.Column(db.Text)
    response_notes = db.Column(db.Text)  # Internal notes

    # Timestamps
    submitted_at = db.Column(
        db.DateTime, default=datetime.now, nullable=False, index=True
    )
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<ContactMessage {self.reference_number}: {self.subject}>"

    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}"

    @property
    def full_phone(self):
        """Get formatted phone number"""
        if self.phone:
            return f"{self.country_code} {self.phone}"
        return None

    @property
    def is_new(self):
        """Check if message is new (unread)"""
        return self.status == "new"

    @property
    def is_responded(self):
        """Check if message has been responded to"""
        return self.responded_at is not None

    def mark_as_read(self):
        """Mark message as read (in progress)"""
        if self.status == "new":
            self.status = "in_progress"
            self.updated_at = datetime.now()

    def mark_as_resolved(
        self, resolved_by: str, response_message: str = None, notes: str = None
    ):
        """Mark message as resolved"""
        self.status = "resolved"
        self.responded_at = datetime.now()
        self.responded_by = resolved_by
        if response_message:
            self.response_message = response_message
        if notes:
            self.response_notes = notes
        self.updated_at = datetime.now()

    def assign_to(self, admin_name: str):
        """Assign message to admin user"""
        self.assigned_to = admin_name
        if self.status == "new":
            self.status = "in_progress"
        self.updated_at = datetime.now()

    def set_priority(self, priority: str):
        """Set message priority"""
        if priority in ["low", "normal", "high", "urgent"]:
            self.priority = priority
            self.updated_at = datetime.now()

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "reference_number": self.reference_number,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.full_phone,
            "organization": self.organization,
            "inquiry_type": self.inquiry_type,
            "subject": self.subject,
            "message": self.message,
            "status": self.status,
            "priority": self.priority,
            "submitted_at": self.submitted_at.isoformat()
            if self.submitted_at
            else None,
            "is_responded": self.is_responded,
        }
