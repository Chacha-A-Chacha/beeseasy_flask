"""
Flask-WTF forms for Bee East Africa Symposium authentication.
Covers login, password reset (request + complete), and password change.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, HiddenField
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, Regexp, ValidationError
)


# ---------------------------------------------------------
# LOGIN FORM
# ---------------------------------------------------------
class LoginForm(FlaskForm):
    """Login form for symposium participants and staff."""

    identifier = StringField(
        'Email or Name',
        validators=[
            DataRequired(message='Please enter your email or name'),
            Length(min=3, max=120, message='Must be between 3 and 120 characters')
        ],
        render_kw={
            'placeholder': 'Enter your email or name',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600',
            'autocomplete': 'username',
            'autofocus': True
        }
    )

    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required'),
            Length(min=6, max=255, message='Password must be at least 6 characters')
        ],
        render_kw={
            'placeholder': 'Enter your password',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600',
            'autocomplete': 'current-password'
        }
    )

    remember_me = BooleanField(
        'Remember me',
        default=False,
        render_kw={
            'class': 'h-4 w-4 text-yellow-600 focus:ring-yellow-600 border-gray-300 rounded'
        }
    )

    next_url = HiddenField()

    def validate_identifier(self, field):
        """Ensure the field is not empty after trimming."""
        if not field.data or not field.data.strip():
            raise ValidationError('Identifier cannot be empty')


# ---------------------------------------------------------
# PASSWORD RESET REQUEST FORM
# ---------------------------------------------------------
class PasswordResetRequestForm(FlaskForm):
    """Request password reset via email."""

    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email address is required'),
            Email(message='Please enter a valid email address')
        ],
        render_kw={
            'placeholder': 'Enter your registered email',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600',
            'autocomplete': 'email',
            'autofocus': True
        }
    )


# ---------------------------------------------------------
# PASSWORD RESET FORM (WITH TOKEN)
# ---------------------------------------------------------
class PasswordResetForm(FlaskForm):
    """Form for users resetting their password with a valid token."""

    token = HiddenField(validators=[DataRequired()])

    password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message='Password is required'),
            Length(min=8, max=255, message='Password must be at least 8 characters'),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
                message='Must contain at least one uppercase letter, one lowercase letter, and one number'
            )
        ],
        render_kw={
            'placeholder': 'Enter new password',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600',
            'autocomplete': 'new-password'
        }
    )

    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm your password'),
            EqualTo('password', message='Passwords must match')
        ],
        render_kw={
            'placeholder': 'Confirm new password',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600',
            'autocomplete': 'new-password'
        }
    )

    def validate_password(self, field):
        """Additional weak password protection."""
        common_passwords = ['password', '123456', 'qwerty', 'abc123', 'bee123', 'symposium']
        if field.data.lower() in common_passwords:
            raise ValidationError('This password is too common. Please choose a more secure one.')


# ---------------------------------------------------------
# PASSWORD CHANGE FORM (LOGGED-IN USERS)
# ---------------------------------------------------------
class PasswordChangeForm(FlaskForm):
    """Form for authenticated users to change password."""

    current_password = PasswordField(
        'Current Password',
        validators=[
            DataRequired(message='Current password is required'),
            Length(min=6, max=255)
        ],
        render_kw={
            'placeholder': 'Enter your current password',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600',
            'autocomplete': 'current-password'
        }
    )

    new_password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message='New password is required'),
            Length(min=8, max=255),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
                message='Must contain at least one uppercase, one lowercase, and one number'
            )
        ],
        render_kw={
            'placeholder': 'Enter new password',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600',
            'autocomplete': 'new-password'
        }
    )

    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(),
            EqualTo('new_password', message='Passwords must match')
        ],
        render_kw={
            'placeholder': 'Confirm new password',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-yellow-600 focus:border-yellow-600',
            'autocomplete': 'new-password'
        }
    )

    def validate_new_password(self, field):
        """Ensure new password is strong and not same as current."""
        if field.data == self.current_password.data:
            raise ValidationError('New password must be different from the current one.')

        if len(field.data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
