"""
Authentication service for Bee East Africa Symposium.
Handles user login, logout, password management, and email notifications.
"""

import logging
import secrets
from datetime import datetime, timedelta
from flask import current_app, request, url_for, render_template
from flask_login import login_user, logout_user, current_user
from app.models.user import User
from app.extensions import db, mail
from flask_mail import Message


class AuthService:
    """Service class for authentication and user security operations."""

    # -------------------- LOGIN --------------------
    @staticmethod
    def authenticate_user(identifier, password, remember_me=False):
        """
        Authenticate user via email or username.
        """
        logger = logging.getLogger('auth_service')

        try:
            user = (
                db.session.query(User)
                .filter(
                    (User.email == identifier) | (User.full_name == identifier),
                    User.is_active == True
                )
                .first()
            )

            if not user:
                return False, None, "Invalid email or password"

            if not user.check_password(password):
                return False, None, "Invalid email or password"

            login_user(user, remember=remember_me)
            logger.info(f"User logged in: {user.email}")
            return True, user, "Login successful"

        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            db.session.rollback()
            return False, None, "An error occurred during login"


    # -------------------- LOGOUT --------------------
    @staticmethod
    def logout_user_session():
        """
        Logout the current user and clear session cookies.
        """
        from flask import make_response, redirect, url_for
        try:
            logout_user()
            response = make_response(redirect(url_for('auth.login')))
            response.set_cookie('session', '', expires=0)
            response.set_cookie('remember_token', '', expires=0)
            return True, response
        except Exception as e:
            logging.error(f"Logout error: {e}")
            return False, None


    # -------------------- PASSWORD RESET (REQUEST) --------------------
    @staticmethod
    def initiate_password_reset(email):
        """Send password reset link."""
        try:
            user = db.session.query(User).filter_by(email=email, is_active=True).first()

            if not user:
                # Hide whether user exists
                return True, "If that email exists, a reset link has been sent.", None

            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=2)
            db.session.commit()

            reset_url = url_for('auth.password_reset', token=token, _external=True)
            subject = f"Password Reset - {current_app.config.get('SITE_NAME', 'Bee East Africa Symposium')}"
            html = render_template('emails/password_reset.html', user=user, reset_url=reset_url)

            msg = Message(subject=subject, recipients=[user.email], html=html)
            mail.send(msg)

            return True, "If that email exists, a reset link has been sent.", token

        except Exception as e:
            logging.error(f"Password reset initiation error: {e}", exc_info=True)
            db.session.rollback()
            return False, "Unable to send reset email. Please try again.", None


    # -------------------- PASSWORD RESET (VERIFY + COMPLETE) --------------------
    @staticmethod
    def verify_reset_token(token):
        """Verify password reset token."""
        user = db.session.query(User).filter_by(password_reset_token=token).first()

        if not user or not user.password_reset_expires or datetime.utcnow() > user.password_reset_expires:
            return False, None, "Reset link invalid or expired"

        return True, user, "Token valid"


    @staticmethod
    def reset_password(user, new_password):
        """Set new password for user."""
        if len(new_password) < 8:
            return False, "Password must be at least 8 characters long"

        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()

        # Optional: send confirmation email
        try:
            msg = Message(
                subject=f"Password Changed Successfully - {current_app.config.get('SITE_NAME', 'Bee East Africa Symposium')}",
                recipients=[user.email],
                html=render_template('emails/password_reset_confirmation.html', user=user)
            )
            mail.send(msg)
        except Exception:
            logging.warning("Password change email could not be sent, but password was updated.")

        return True, "Your password has been reset successfully"


    # -------------------- PASSWORD CHANGE --------------------
    @staticmethod
    def change_password(user, current_password, new_password):
        """Change password for authenticated user."""
        if not user.check_password(current_password):
            return False, "Current password is incorrect"

        if len(new_password) < 8:
            return False, "New password must be at least 8 characters long"

        user.set_password(new_password)
        db.session.commit()

        try:
            msg = Message(
                subject=f"Password Changed - {current_app.config.get('SITE_NAME', 'Bee East Africa Symposium')}",
                recipients=[user.email],
                html=render_template('emails/password_change_confirmation.html', user=user)
            )
            mail.send(msg)
        except Exception:
            logging.warning("Password change confirmation email failed to send.")

        return True, "Password changed successfully"


    # -------------------- PASSWORD STRENGTH --------------------
    @staticmethod
    def validate_password_strength(password):
        """Basic password strength validation."""
        score = 0
        if len(password) >= 8: score += 1
        if any(c.islower() for c in password): score += 1
        if any(c.isupper() for c in password): score += 1
        if any(c.isdigit() for c in password): score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password): score += 1

        valid = score >= 3
        message = "Strong password" if valid else "Use a mix of letters, numbers, and symbols."
        return valid, message, score
