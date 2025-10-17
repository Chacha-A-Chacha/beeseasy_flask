# app/forms/contact_form.py

"""
Enhanced contact form with inquiry categorization and phone validation.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField, RadioField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
import re

# Country codes for East Africa and common countries
COUNTRY_CODES = [
    ('+254', '🇰🇪 Kenya (+254)'),
    ('+255', '🇹🇿 Tanzania (+255)'),
    ('+256', '🇺🇬 Uganda (+256)'),
    ('+250', '🇷🇼 Rwanda (+250)'),
    ('+257', '🇧🇮 Burundi (+257)'),
    ('+211', '🇸🇸 South Sudan (+211)'),
    ('+251', '🇪🇹 Ethiopia (+251)'),
    ('+252', '🇸🇴 Somalia (+252)'),
    ('+27', '🇿🇦 South Africa (+27)'),
    ('+234', '🇳🇬 Nigeria (+234)'),
    ('+1', '🇺🇸 United States (+1)'),
    ('+44', '🇬🇧 United Kingdom (+44)'),
    ('+91', '🇮🇳 India (+91)'),
    ('+86', '🇨🇳 China (+86)'),
    ('+81', '🇯🇵 Japan (+81)'),
    ('+49', '🇩🇪 Germany (+49)'),
    ('+33', '🇫🇷 France (+33)'),
    ('+39', '🇮🇹 Italy (+39)'),
    ('+61', '🇦🇺 Australia (+61)'),
    ('+55', '🇧🇷 Brazil (+55)'),
]

INQUIRY_TYPES = [
    ('', 'Select inquiry type...'),
    ('registration', '📝 Event Registration & Attendance'),
    ('exhibition', '🏢 Exhibition & Booth Booking'),
    ('sponsorship', '🤝 Sponsorship Opportunities'),
    ('speaking', '🎤 Speaking Opportunities'),
    ('partnership', '💼 Partnership & Collaboration'),
    ('media', '📰 Media & Press Inquiries'),
    ('agenda', '📅 Program & Agenda Questions'),
    ('travel', '✈️ Travel & Accommodation'),
    ('technical', '🔧 Technical Support'),
    ('other', '💬 Other Inquiry')
]

CONTACT_METHODS = [
    ('email', 'Email'),
    ('phone', 'Phone'),
    ('either', 'Either Email or Phone')
]


class ContactForm(FlaskForm):
    """Enhanced contact form with better UX and intelligent routing"""

    # Personal Information
    first_name = StringField(
        "First Name",
        validators=[DataRequired(message='First name is required'), Length(max=50)],
        render_kw={
            'placeholder': 'Enter your first name',
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]'
        }
    )

    last_name = StringField(
        "Last Name",
        validators=[DataRequired(message='Last name is required'), Length(max=50)],
        render_kw={
            'placeholder': 'Enter your last name',
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]'
        }
    )

    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message='Email is required'),
            Email(message='Please enter a valid email address')
        ],
        render_kw={
            'placeholder': 'you@example.com',
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]',
            'type': 'email'
        }
    )

    # Phone with country code
    country_code = SelectField(
        "Country Code",
        choices=COUNTRY_CODES,
        default='+254',
        render_kw={
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]'
        }
    )

    phone = StringField(
        "Phone Number",
        validators=[Optional(), Length(min=7, max=15)],
        render_kw={
            'placeholder': 'e.g., 712 345 678',
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]',
            'type': 'tel'
        }
    )

    # Inquiry Context
    inquiry_type = SelectField(
        "What is your inquiry about?",
        choices=INQUIRY_TYPES,
        validators=[DataRequired(message='Please select an inquiry type')],
        render_kw={
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]'
        }
    )

    subject = StringField(
        "Subject",
        validators=[DataRequired(message='Subject is required'), Length(max=150)],
        render_kw={
            'placeholder': 'Brief subject of your inquiry',
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]'
        }
    )

    # Optional Context
    organization = StringField(
        "Organization/Company (Optional)",
        validators=[Optional(), Length(max=150)],
        render_kw={
            'placeholder': 'Your organization name',
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]'
        }
    )

    role = StringField(
        "Your Role (Optional)",
        validators=[Optional(), Length(max=100)],
        render_kw={
            'placeholder': 'e.g., Beekeeper, Researcher, Business Owner',
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]'
        }
    )

    # Message
    message = TextAreaField(
        "Your Message",
        validators=[
            DataRequired(message='Message is required'),
            Length(min=20, max=2000, message='Message must be between 20 and 2000 characters')
        ],
        render_kw={
            'rows': 6,
            'placeholder': 'Please provide details about your inquiry...\n\nFor registration issues, include your confirmation number.\nFor partnership inquiries, briefly describe your proposal.',
            'class': 'w-full px-3.5 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#F5C342] focus:border-[#F5C342]'
        }
    )

    # Contact Preferences
    preferred_contact_method = RadioField(
        "Preferred Contact Method",
        choices=CONTACT_METHODS,
        default='email',
        render_kw={'class': 'focus:ring-[#F5C342]'}
    )

    newsletter_signup = BooleanField(
        "Subscribe to event updates and newsletters",
        default=True,
        render_kw={'class': 'h-4 w-4 text-[#F5C342] focus:ring-[#F5C342] border-gray-300 rounded'}
    )

    # Privacy Consent
    privacy_consent = BooleanField(
        "I agree to the privacy policy",
        validators=[DataRequired(message='You must agree to the privacy policy to continue')],
        render_kw={'class': 'h-4 w-4 text-[#F5C342] focus:ring-[#F5C342] border-gray-300 rounded'}
    )

    submit = SubmitField(
        "Send Message",
        render_kw={
            'class': 'w-full rounded-md bg-[#F5C342] px-3.5 py-2.5 text-center text-sm font-semibold text-white shadow-sm hover:bg-[#e7b831] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#F5C342]'
        }
    )

    def validate_phone(self, field):
        """Validate phone number format"""
        if field.data:
            # Remove spaces and dashes
            phone = re.sub(r'[\s\-]', '', field.data)
            
            # Check if it contains only digits (after removing spaces/dashes)
            if not re.match(r'^\d+$', phone):
                raise ValidationError('Phone number should contain only digits')
            
            # Check minimum length
            if len(phone) < 7:
                raise ValidationError('Phone number is too short')

    def validate_email(self, field):
        """Enhanced email validation with typo suggestions"""
        email = field.data.lower()
        
        # Common domain typos
        typo_suggestions = {
            'gmial.com': 'gmail.com',
            'gmai.com': 'gmail.com',
            'gmil.com': 'gmail.com',
            'yahooo.com': 'yahoo.com',
            'yaho.com': 'yahoo.com',
            'hotmial.com': 'hotmail.com',
            'outlok.com': 'outlook.com'
        }
        
        if '@' in email:
            domain = email.split('@')[1]
            if domain in typo_suggestions:
                raise ValidationError(f'Did you mean {typo_suggestions[domain]}?')
