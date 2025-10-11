"""
Flask-WTF forms for Bee East Africa Symposium registration.
Supports both attendee and exhibitor registration using the unified Registration model.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TelField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from app.models.registration import Registration, RegistrationType
from app.extensions import db


class ExhibitorRegistrationForm(FlaskForm):
    """Registration form for exhibitors and organizations."""

    full_name = StringField(
        'Contact Person Full Name',
        validators=[
            DataRequired(message='Contact person name is required'),
            Length(min=3, max=150)
        ],
        render_kw={
            'placeholder': 'Name of the primary contact person',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600'
        }
    )

    organization = StringField(
        'Organization / Company Name',
        validators=[
            DataRequired(message='Organization name is required'),
            Length(min=3, max=150)
        ],
        render_kw={
            'placeholder': 'Enter your organization or company name',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600'
        }
    )

    email = EmailField(
        'Business Email Address',
        validators=[
            DataRequired(message='Email is required'),
            Email(message='Please enter a valid email address')
        ],
        render_kw={
            'placeholder': 'company@example.com',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600'
        }
    )

    phone = TelField(
        'Phone Number',
        validators=[
            DataRequired(message='Phone number is required'),
            Length(min=7, max=20)
        ],
        render_kw={
            'placeholder': 'e.g. +254712345678',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600'
        }
    )

    package = SelectField(
        'Preferred Category',
        choices=[
            ('standard', 'Standard Exhibitor'),
            ('premium', 'Premium Exhibitor'),
            ('sponsor', 'Sponsorship Partner')
        ],
        validators=[Optional()],
        render_kw={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600'
        }
    )

    category = HiddenField(default=RegistrationType.EXHIBITOR.value)

    def validate_email(self, field):
        """Prevent duplicate exhibitor registrations."""
        existing = (
            db.session.query(Registration)
            .filter_by(email=field.data.lower(), category=RegistrationType.EXHIBITOR)
            .first()
        )
        if existing:
            raise ValidationError('This email is already registered as an exhibitor.')
