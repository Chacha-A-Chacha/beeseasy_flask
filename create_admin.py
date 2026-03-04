"""Run this script in cPanel Python Terminal to create an admin user."""

from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app("production")

with app.app_context():
    existing = User.query.filter_by(email="calex2607@gmail.com").first()
    if existing:
        print("User with this email already exists.")
    else:
        u = User(email="calex2607@gmail.com", name="CHACHA", role="admin")
        u.set_password("123123123")
        u.is_active = True
        db.session.add(u)
        db.session.commit()
        print("Admin created successfully.")
