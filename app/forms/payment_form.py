"""
Enhanced Flask-WTF forms for BEEASY2025 Registration System
Comprehensive forms matching the optimized database models
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, EmailField, TelField, SelectField, TextAreaField
)
from wtforms.validators import (
    DataRequired, Email, Length, Optional
)


class PaymentMethodForm(FlaskForm):
    """Payment method selection form"""

    payment_method = SelectField(
        'Payment Method',
        choices=[
            ('card', 'Credit/Debit Card'),
            ('mobile_money', 'Mobile Money (M-Pesa/Airtel)'),
            ('bank_transfer', 'Bank Transfer'),
            ('invoice', 'Invoice (Company Payment)'),
        ],
        validators=[DataRequired()],
        render_kw={'class': 'payment-method-selector'}
    )

    # For mobile money
    mobile_number = TelField(
        'Mobile Money Number',
        validators=[Optional(), Length(max=20)],
        render_kw={'placeholder': '0712345678'}
    )

    # For bank transfer
    bank_name = StringField(
        'Bank Name',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'Your bank name'}
    )

    # Billing details
    billing_name = StringField(
        'Name on Card/Invoice',
        validators=[Optional(), Length(max=200)],
        render_kw={'placeholder': 'Full name'}
    )

    billing_email = EmailField(
        'Billing Email',
        validators=[Optional(), Email()],
        render_kw={'placeholder': 'billing@company.com'}
    )

    billing_address = TextAreaField(
        'Billing Address',
        validators=[Optional(), Length(max=500)],
        render_kw={'rows': 2, 'placeholder': 'Street address, city, postal code, country'}
    )

    # Notes
    payment_notes = TextAreaField(
        'Payment Notes',
        validators=[Optional(), Length(max=500)],
        render_kw={'rows': 2, 'placeholder': 'Any special payment instructions...'}
    )


# ============================================
# PROMO CODE VALIDATION FORM
# ============================================

class PromoCodeForm(FlaskForm):
    """Standalone promo code validation form"""

    promo_code = StringField(
        'Promo Code',
        validators=[DataRequired(), Length(min=3, max=50)],
        render_kw={'placeholder': 'Enter promo code', 'class': 'promo-code-input'}
    )
