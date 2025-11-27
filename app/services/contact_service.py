# app/services/contact_service.py

"""
Enhanced contact service with intelligent routing, auto-replies, and logging.
"""

import logging
import secrets
from datetime import datetime

from flask import current_app, render_template
from flask_mail import Message

from app.extensions import db, mail
from app.models.contact import ContactMessage

logger = logging.getLogger(__name__)


class ContactService:
    """Enhanced contact handling with routing and auto-replies"""

    # Inquiry routing map
    ROUTING_MAP = {
        "registration": "registrations@beeseasy.org",
        "exhibition": "exhibitions@beeseasy.org",
        "sponsorship": "partnerships@beeseasy.org",
        "speaking": "speakers@beeseasy.org",
        "partnership": "partnerships@beeseasy.org",
        "media": "press@beeseasy.org",
        "agenda": "info@beeseasy.org",
        "travel": "info@beeseasy.org",
        "technical": "support@beeseasy.org",
        "other": "info@beeseasy.org",
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
            # Generate reference number
            reference_number = (
                f"BEE{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(3).upper()}"
            )

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

            # Determine recipient based on inquiry type
            inquiry_type = form_data.get("inquiry_type", "other")
            recipient = ContactService.ROUTING_MAP.get(
                inquiry_type, ContactService.ROUTING_MAP["other"]
            )

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
                    "EVENT_NAME", "Bee East Africa Symposium 2025"
                ),
            }

            # Send to team
            team_subject = f"[{inquiry_type.upper()}] {form_data.get('subject')}"
            team_msg = Message(
                subject=team_subject,
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                recipients=[recipient],
                reply_to=form_data.get("email"),
            )
            team_msg.html = render_template("emails/contact_team.html", **email_context)
            team_msg.body = ContactService._create_plain_text_team_email(email_context)

            # Send auto-reply to user
            user_subject = f"We've received your inquiry - {form_data.get('subject')}"
            user_msg = Message(
                subject=user_subject,
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                recipients=[form_data.get("email")],
            )
            user_msg.html = render_template(
                "emails/contact_confirmation.html", **email_context
            )
            user_msg.body = ContactService._create_plain_text_confirmation(
                email_context
            )

            # Send both emails
            mail.send(team_msg)
            mail.send(user_msg)

            # Log the inquiry
            logger.info(
                f"Contact inquiry received - Type: {inquiry_type}, "
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
                "Sorry, we couldn't send your message. Please try again or email us directly at info@beeseasy.org",
                None,
            )

    @staticmethod
    def _create_plain_text_team_email(context: dict) -> str:
        """Create plain text version for team email"""
        return f"""
New Contact Inquiry - Reference: {context["reference_number"]}

INQUIRY DETAILS:
---------------
Type: {context["inquiry_type"].title()}
Subject: {context["subject"]}
Submitted: {context["submitted_at"]}

CONTACT INFORMATION:
-------------------
Name: {context["first_name"]} {context["last_name"]}
Email: {context["email"]}
Phone: {context.get("full_phone", "Not provided")}
Organization: {context.get("organization", "Not provided")}
Role: {context.get("role", "Not provided")}

PREFERRED CONTACT METHOD:
------------------------
{context.get("preferred_contact_method", "email").title()}

MESSAGE:
--------
{context["message"]}

NEWSLETTER SIGNUP: {"Yes" if context.get("newsletter_signup") else "No"}

---
Sent from {context["event_name"]} Contact Form
        """

    @staticmethod
    def _create_plain_text_confirmation(context: dict) -> str:
        """Create plain text confirmation for user"""
        inquiry_type = context["inquiry_type"]

        # Custom messages based on inquiry type
        next_steps = {
            "registration": "You can start your registration at: https://beeseasy.org/register",
            "exhibition": "View exhibition packages at: https://beeseasy.org/partners",
            "sponsorship": "Learn about sponsorship opportunities at: https://beeseasy.org/partners",
            "speaking": "Review our speaker guidelines at: https://beeseasy.org/speakers",
            "media": "Visit our media center at: https://beeseasy.org/news",
        }

        return f"""
Thank you for contacting {context["event_name"]}!

Hi {context["first_name"]},

We've received your inquiry about "{context["subject"]}" and will respond within 24-48 hours.

YOUR INQUIRY DETAILS:
--------------------
Reference Number: {context["reference_number"]}
Inquiry Type: {inquiry_type.title()}
Submitted: {context["submitted_at"]}

{next_steps.get(inquiry_type, "We will review your message and get back to you soon.")}

{next_steps.get(inquiry_type, "We will review your message and get back to you soon.")}

If you have urgent questions, you can also reach us at:
📧 Email: info@beeseasy.org
📞 Phone: +254 719 740 938

Best regards,
The BEEASY2025 Team

---
This is an automated confirmation. Please do not reply to this email.
        """
