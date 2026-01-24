"""
Newsletter Subscription Form
Simple form for email newsletter signups
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class NewsletterSubscriptionForm(FlaskForm):
    """Simple newsletter subscription form"""

    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
            Length(max=255, message="Email is too long"),
        ],
        render_kw={
            "placeholder": "Enter your email",
            "class": "w-full rounded-full border-0 bg-white px-4 py-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-accent-orange text-base",
            "type": "email",
            "autocomplete": "email",
        },
    )

    submit = SubmitField(
        "Notify Me",
        render_kw={
            "class": "flex-none rounded-full bg-accent-orange px-6 py-3 text-base font-semibold text-white shadow-lg hover:bg-accent-yellow hover:text-primary-dark transition-all duration-300"
        },
    )

    def validate_email(self, field):
        """Enhanced email validation with common typo detection"""
        email = field.data.lower().strip()

        # Common domain typos
        typo_suggestions = {
            "gmial.com": "gmail.com",
            "gmai.com": "gmail.com",
            "gmil.com": "gmail.com",
            "yahooo.com": "yahoo.com",
            "yaho.com": "yahoo.com",
            "hotmial.com": "hotmail.com",
            "outlok.com": "outlook.com",
            "outloo.com": "outlook.com",
        }

        if "@" in email:
            domain = email.split("@")[1]
            if domain in typo_suggestions:
                from wtforms.validators import ValidationError

                raise ValidationError(f"Did you mean {typo_suggestions[domain]}?")
