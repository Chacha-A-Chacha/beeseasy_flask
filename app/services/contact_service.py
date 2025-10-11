"""
Service for processing and sending contact form submissions via email.
"""

from flask_mail import Message
from flask import current_app
from app.extensions import mail
import logging

logger = logging.getLogger(__name__)


class ContactService:
    """Handles sending contact inquiries through email."""

    @staticmethod
    def send_contact_message(form_data: dict) -> bool:
        """
        Sends the contact message using Flask-Mail.

        Args:
            form_data: dict containing 'first_name', 'last_name', 'email', 'phone', 'message'

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            subject = f"New Contact Message from {form_data.get('first_name')} {form_data.get('last_name')}"
            recipient = current_app.config.get("MAIL_DEFAULT_RECEIVER", "info@beeseasy.org")

            msg = Message(
                subject=subject,
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                recipients=[recipient],
            )

            msg.body = (
                f"Name: {form_data.get('first_name')} {form_data.get('last_name')}\n"
                f"Email: {form_data.get('email')}\n"
                f"Phone: {form_data.get('phone') or 'N/A'}\n\n"
                f"Message:\n{form_data.get('message')}\n"
            )

            mail.send(msg)
            logger.info(f"Contact message sent successfully from {form_data.get('email')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send contact message: {e}", exc_info=True)
            return False
