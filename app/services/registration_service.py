"""
Registration service for handling attendee and exhibitor registrations.
Handles database operations, validation, and email notifications.
"""

import logging
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db  # email_service
from app.models.registration import Registration, RegistrationType
# from app.utils.enhanced_email import Priority


class RegistrationService:
    """Service class to handle attendee and exhibitor registration operations."""

    @staticmethod
    def register_attendee(data: dict):
        """
        Register a new event attendee.

        Args:
            data (dict): Registration data with fields:
                - full_name
                - email
                - phone
                - organization (optional)

        Returns:
            tuple: (success: bool, message: str, registration: Registration|None)
        """
        logger = logging.getLogger('registration_service')

        try:
            # Check for duplicate registration
            existing = (
                db.session.query(Registration)
                .filter_by(email=data['email'].lower(), category=RegistrationType.ATTENDEE)
                .first()
            )
            if existing:
                return False, "This email is already registered as an attendee.", None

            registration = Registration(
                full_name=data.get('full_name').strip(),
                email=data.get('email').lower().strip(),
                phone=data.get('phone').strip(),
                organization=data.get('organization', '').strip() or None,
                category=RegistrationType.ATTENDEE,
                payment_status="pending",
                amount_paid=0.0
            )

            db.session.add(registration)
            db.session.commit()

            logger.info(f"New attendee registration: {registration.full_name} ({registration.email})")

            # Send confirmation email
            try:
                template_context = {
                    "full_name": registration.full_name,
                    "email": registration.email,
                    "category": "Attendee",
                    "organization": registration.organization or "N/A",
                    "event_name": current_app.config.get("EVENT_NAME", "Bee East Africa Symposium"),
                    "event_date": current_app.config.get("EVENT_DATE", "To be announced"),
                    "contact_email": current_app.config.get("CONTACT_EMAIL", "info@beeseasy.org"),
                }

                email_service.send_notification(
                    recipient=registration.email,
                    template="attendee_registration_confirmation",
                    subject=f"Your Registration for {template_context['event_name']}",
                    template_context=template_context,
                    priority=Priority.NORMAL,
                    group_id="attendee_registration"
                )
            except Exception as email_error:
                logger.warning(f"Attendee registration email failed: {email_error}")

            return True, "Registration successful. A confirmation email has been sent.", registration

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during attendee registration: {str(e)}", exc_info=True)
            return False, "A system error occurred. Please try again later.", None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in register_attendee: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred. Please try again later.", None

    # ---------------------------------------------------------
    # EXHIBITOR REGISTRATION
    # ---------------------------------------------------------
    @staticmethod
    def register_exhibitor(data: dict):
        """
        Register a new exhibitor or organization.

        Args:
            data (dict): Registration data with fields:
                - full_name (contact person)
                - email
                - phone
                - organization
                - package (optional)

        Returns:
            tuple: (success: bool, message: str, registration: Registration|None)
        """
        logger = logging.getLogger('registration_service')

        try:
            existing = (
                db.session.query(Registration)
                .filter_by(email=data['email'].lower(), category=RegistrationType.EXHIBITOR)
                .first()
            )
            if existing:
                return False, "This email is already registered as an exhibitor.", None

            registration = Registration(
                full_name=data.get('full_name').strip(),
                email=data.get('email').lower().strip(),
                phone=data.get('phone').strip(),
                organization=data.get('organization', '').strip(),
                category=RegistrationType.EXHIBITOR,
                payment_status="pending",
                amount_paid=0.0
            )

            db.session.add(registration)
            db.session.commit()

            logger.info(f"New exhibitor registration: {registration.organization} ({registration.email})")

            # Send confirmation email
            try:
                template_context = {
                    "organization": registration.organization,
                    "contact_name": registration.full_name,
                    "email": registration.email,
                    "category": "Exhibitor",
                    "event_name": current_app.config.get("EVENT_NAME", "Bee East Africa Symposium"),
                    "event_date": current_app.config.get("EVENT_DATE", "To be announced"),
                    "contact_email": current_app.config.get("CONTACT_EMAIL", "info@beeseasy.org"),
                }

                email_service.send_notification(
                    recipient=registration.email,
                    template="exhibitor_registration_confirmation",
                    subject=f"Exhibitor Registration Confirmation - {template_context['event_name']}",
                    template_context=template_context,
                    priority=Priority.HIGH,
                    group_id="exhibitor_registration"
                )
            except Exception as email_error:
                logger.warning(f"Exhibitor registration email failed: {email_error}")

            return True, "Registration successful. A confirmation email has been sent.", registration

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during exhibitor registration: {str(e)}", exc_info=True)
            return False, "A system error occurred. Please try again later.", None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in register_exhibitor: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred. Please try again later.", None

    # ---------------------------------------------------------
    # COMMON METHODS
    # ---------------------------------------------------------
    @staticmethod
    def mark_payment_complete(registration_id: int, amount: float):
        """Mark registration as paid."""
        logger = logging.getLogger('registration_service')

        try:
            registration = db.session.query(Registration).filter_by(id=registration_id).first()
            if not registration:
                return False, "Registration not found."

            registration.mark_as_paid(amount)
            db.session.commit()

            logger.info(f"Payment marked complete for {registration.full_name} ({registration.email})")

            # Optionally send receipt email
            try:
                template_context = {
                    "full_name": registration.full_name,
                    "amount": amount,
                    "payment_status": "Paid",
                    "category": registration.category.value.title(),
                    "event_name": current_app.config.get("EVENT_NAME", "Bee East Africa Symposium"),
                }

                email_service.send_notification(
                    recipient=registration.email,
                    template="payment_receipt",
                    subject=f"Payment Receipt - {template_context['event_name']}",
                    template_context=template_context,
                    priority=Priority.NORMAL,
                    group_id="payment_receipt"
                )
            except Exception as email_error:
                logger.warning(f"Payment confirmation email failed: {email_error}")

            return True, "Payment marked successfully."

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error while marking payment complete: {str(e)}", exc_info=True)
            return False, "Database error occurred."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in mark_payment_complete: {str(e)}", exc_info=True)
            return False, "Unexpected system error."
