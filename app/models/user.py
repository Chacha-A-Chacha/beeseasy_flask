from datetime import datetime
from enum import Enum

from flask_login import UserMixin

from app.extensions import bcrypt, db, login_manager


class UserRole(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    ORGANIZER = "organizer"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """System user — handles admin, staff, and organizer roles."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Enum(UserRole), index=True, default=UserRole.STAFF)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)

    # Relationships
    registrations = db.relationship(
        "Registration", back_populates="created_by", lazy="select"
    )

    # --- Methods ---
    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_organizer(self) -> bool:
        return self.role == UserRole.ORGANIZER

    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"
