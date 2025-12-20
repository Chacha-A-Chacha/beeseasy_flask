# app/services/contact_service.py

"""
Enhanced contact service with intelligent routing, auto-replies, and logging.
"""

import logging
import secrets
from datetime import datetime

from flask import current_app

from app.extensions import db
from app.models.contact import ContactMessage
from app.utils.enhanced_email import EnhancedEmailService, Priority

logger = logging.getLogger(__name__)


class ContactService:
    """Enhanced contact handling with routing and auto-replies"""

    # Inquiry routing map
    ROUTING_MAP = {
        "registration": "registrations@pollination.africa",
        "exhibition": "exhibitions@pollination.africa",
        "sponsorship": "partnerships@pollination.africa",
        "speaking": "info@pollination.africa",
        "partnership": "partnerships@pollination.africa",
        "media": "press@pollination.africa",
        "agenda": "info@pollination.africa",
        "travel": "info@pollination.africa",
        "technical": "support@pollination.africa",
        "other": "info@pollination.africa",
    }

    # Category-specific reference number prefixes
    CATEGORY_PREFIXES = {
        "registration": "PACREG",  # Event Registration & Attendance
        "exhibition": "PACEXH",  # Exhibition & Booth Booking
        "sponsorship": "PACSPO",  # Sponsorship Opportunities
        "speaking": "PACSPK",  # Speaking Opportunities
        "partnership": "PACPAR",  # Partnership & Collaboration
        "media": "PACMED",  # Media & Press Inquiries
        "agenda": "PACAGN",  # Program & Agenda Questions
        "travel": "PACTRV",  # Travel & Accommodation
        "technical": "PACTEC",  # Technical Support
        "other": "PACGEN",  # General/Other Inquiries
    }

    @staticmethod
    def send_contact_message(form_data: dict) -> tuple:
        """
        Send contact inquiry with intelligent routing and auto-reply.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            tuple: (success: bool, message: str, reference_number: str)
        """
        try:
            # Get inquiry type and determine prefix
            inquiry_type = form_data.get("inquiry_type", "other")
            prefix = ContactService.CATEGORY_PREFIXES.get(inquiry_type, "PACGEN")

            # Generate category-specific reference number
            # Format: {prefix}{YYYYMMDD}{6-random-chars}
            reference_number = f"{prefix}{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(3).upper()}"

            # Save to database first
            contact_message = ContactMessage(
                reference_number=reference_number,
                first_name=form_data.get("first_name"),
                last_name=form_data.get("last_name"),
                email=form_data.get("email"),
                phone=form_data.get("phone"),
                country_code=form_data.get("country_code", "+254"),
                organization=form_data.get("organization"),
                role=form_data.get("role"),
                inquiry_type=form_data.get("inquiry_type", "other"),
                subject=form_data.get("subject"),
                message=form_data.get("message"),
                preferred_contact_method=form_data.get(
                    "preferred_contact_method", "email"
                ),
                newsletter_signup=form_data.get("newsletter_signup", False),
                status="new",
                submitted_at=datetime.now(),
            )
            db.session.add(contact_message)
            db.session.commit()

            # Initialize email service
            email_service = EnhancedEmailService(current_app)

            # Use default info email for now (routing map reserved for future team expansion)
            team_recipient = current_app.config.get(
                "CONTACT_EMAIL", "info@pollination.africa"
            )
            # TODO: Uncomment when team is bigger and has dedicated department emails
            # team_recipient = ContactService.ROUTING_MAP.get(
            #     inquiry_type, ContactService.ROUTING_MAP["other"]
            # )

            # Format phone number
            full_phone = None
            if form_data.get("phone"):
                country_code = form_data.get("country_code", "+254")
                full_phone = f"{country_code} {form_data.get('phone')}"

            # Prepare email context
            email_context = {
                **form_data,
                "full_phone": full_phone,
                "reference_number": reference_number,
                "submitted_at": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
                "event_name": current_app.config.get(
                    "EVENT_NAME", "Pollination Africa Symposium 2026"
                ),
                "event_date": current_app.config.get("EVENT_DATE", "3-5 June 2026"),
                "event_location": current_app.config.get(
                    "EVENT_LOCATION",
                    "Arusha International Conference Centre, Arusha, Tanzania",
                ),
                "contact_email": current_app.config.get(
                    "CONTACT_EMAIL", "info@pollination.africa"
                ),
                "support_phone": current_app.config.get(
                    "SUPPORT_PHONE", "+254 719 740 938"
                ),
                "support_whatsapp": current_app.config.get(
                    "SUPPORT_WHATSAPP", "+254 719 740 938"
                ),
                "website_url": current_app.config.get(
                    "WEBSITE_URL", "https://pollination.africa"
                ),
            }

            # Send to team (high priority)
            team_subject = f"[{inquiry_type.upper()}] {form_data.get('subject')}"
            email_service.send_notification(
                recipient=team_recipient,
                template="contact_team",
                subject=team_subject,
                template_context=email_context,
                priority=Priority.HIGH,
            )

            # Send auto-reply to user (normal priority)
            user_subject = f"We've received your inquiry - {form_data.get('subject')}"
            email_service.send_notification(
                recipient=form_data.get("email"),
                template="contact_confirmation",
                subject=user_subject,
                template_context=email_context,
                priority=Priority.NORMAL,
            )

            # Log the inquiry
            logger.info(
                f"Contact inquiry queued - Type: {inquiry_type}, "
                f"From: {form_data.get('email')}, Ref: {reference_number}"
            )

            return (
                True,
                f"Thank you! Your message has been sent. Reference: {reference_number}",
                reference_number,
            )

        except Exception as e:
            logger.error(f"Failed to send contact message: {e}", exc_info=True)
            return (
                False,
                "Sorry, we couldn't send your message. Please try again or email us directly at info@pollination.africa",
                None,
            )
