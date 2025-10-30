"""
Registration Service for BEEASY2025 Event Registration System
Handles registration, payment creation, badge generation, and email notifications
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any

from flask import current_app, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.utils.enhanced_email import EnhancedEmailService
from app.models import (
    AttendeeRegistration,
    ExhibitorRegistration,
    RegistrationStatus,
    TicketPrice,
    ExhibitorPackagePrice,
    AttendeeTicketType,
    ExhibitorPackage,
    Payment,
    PaymentStatus,
    PaymentMethod,
    PromoCode,
    PromoCodeUsage,
)
from app.services.badge_service import BadgeService
from app.utils.model_utils import ValidationHelpers

logger = logging.getLogger("registration_service")


class RegistrationService:
    """Service class for handling event registrations"""

    # ---------------------------------------------------------
    # ATTENDEE REGISTRATION
    # ---------------------------------------------------------

    @staticmethod
    def register_attendee(
        data: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[AttendeeRegistration]]:
        """Register new attendee, create payment, send registration email"""
        try:
            logger.info(f"Starting attendee registration for {data.get('email')}")

            # Validate email
            email = data.get("email", "").lower().strip()
            is_available, msg = ValidationHelpers.check_email_availability(
                email=email, registration_type="attendee"
            )
            if not is_available:
                return False, msg, None

            # Get and validate ticket
            ticket_type = data.get("ticket_type")
            if isinstance(ticket_type, str):
                try:
                    ticket_type = AttendeeTicketType[ticket_type.upper()]
                except KeyError:
                    return False, f"Invalid ticket type: {ticket_type}", None

            ticket_price = TicketPrice.query.filter_by(ticket_type=ticket_type).first()
            if not ticket_price or not ticket_price.is_available():
                return False, f"Ticket {ticket_type.value} is not available", None

            # Claim ticket
            try:
                ticket_price.claim_tickets(quantity=1)
            except ValueError as e:
                db.session.rollback()
                return False, str(e), None

            # Create registration
            attendee = AttendeeRegistration(
                first_name=data.get("first_name").strip(),
                last_name=data.get("last_name").strip(),
                email=email,
                phone_country_code=data.get("phone_country_code", "+254"),
                phone_number=data.get("phone_number", "").strip(),
                ticket_type=ticket_type,
                ticket_price_id=ticket_price.id,
                organization=data.get("organization", "").strip() or None,
                job_title=data.get("job_title", "").strip() or None,
                professional_category=data.get("professional_category"),
                event_preferences=data.get("event_preferences"),
                dietary_requirement=data.get("dietary_requirement"),
                dietary_notes=data.get("dietary_notes"),
                accessibility_needs=data.get("accessibility_needs"),
                special_requirements=data.get("special_requirements"),
                needs_visa_letter=data.get("needs_visa_letter", False),
                referral_source=data.get("referral_source"),
                consent_photography=data.get("consent_photography", True),
                consent_networking=data.get("consent_networking", True),
                consent_data_sharing=data.get("consent_data_sharing", False),
                newsletter_signup=data.get("newsletter_signup", True),
                status=RegistrationStatus.PENDING,
            )

            db.session.add(attendee)
            db.session.flush()

            # Create payment
            payment = RegistrationService._create_payment(attendee)
            db.session.add(payment)
            db.session.flush()

            # Apply promo code if provided
            promo_code = data.get("promo_code", "").strip()
            if promo_code:
                success, message = RegistrationService._apply_promo_code(
                    registration=attendee, payment=payment, promo_code=promo_code
                )
                if success:
                    logger.info(f"Promo code applied: {promo_code}")

            # Check if free ticket - auto-complete and generate badge
            if payment.total_amount <= 0:
                logger.info(
                    f"Free ticket detected for {attendee.reference_number} - auto-completing"
                )

                # Mark payment as completed
                payment.payment_status = PaymentStatus.COMPLETED
                payment.payment_method = PaymentMethod.FREE
                payment.transaction_id = f"FREE-{attendee.reference_number}"
                payment.paid_at = datetime.utcnow()

                # Confirm registration
                attendee.status = RegistrationStatus.CONFIRMED
                attendee.confirmed_at = datetime.utcnow()

                db.session.commit()

                # Generate badge immediately
                badge_success, badge_message, badge_url = BadgeService.generate_badge(
                    attendee.id
                )
                if not badge_success:
                    logger.error(
                        f"Badge generation failed for free ticket: {badge_message}"
                    )
                    # Continue anyway - badge can be regenerated later

                # Send confirmation email WITH badge
                RegistrationService._send_confirmation_email(attendee, badge_url)

                logger.info(
                    f"Free ticket registration completed: {attendee.reference_number}"
                )
                return (
                    True,
                    "Registration successful! Check your email for your badge.",
                    attendee,
                )

            else:
                # Paid ticket - send registration received email with checkout link
                db.session.commit()
                RegistrationService._send_registration_email(attendee, payment)

                logger.info(
                    f"Paid ticket registration created: {attendee.reference_number}"
                )
                return (
                    True,
                    "Registration successful! Please complete payment to receive your badge.",
                    attendee,
                )

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error: {str(e)}", exc_info=True)
            return False, "System error. Please try again.", None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return False, "Unexpected error. Please contact support.", None

    # ---------------------------------------------------------
    # EXHIBITOR REGISTRATION
    # ---------------------------------------------------------

    @staticmethod
    def register_exhibitor(
        data: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[ExhibitorRegistration]]:
        """Register new exhibitor, create payment, send registration email"""
        try:
            logger.info(f"Starting exhibitor registration for {data.get('email')}")

            # Validate email
            email = data.get("email", "").lower().strip()
            is_available, msg = ValidationHelpers.check_email_availability(
                email=email, registration_type="exhibitor"
            )
            if not is_available:
                return False, msg, None

            # Get and validate package
            package_type = data.get("package_type")
            if isinstance(package_type, str):
                try:
                    package_type = ExhibitorPackage[package_type.upper()]
                except KeyError:
                    return False, f"Invalid package type: {package_type}", None

            package_price = ExhibitorPackagePrice.query.filter_by(
                package_type=package_type
            ).first()
            if not package_price or not package_price.is_available():
                return False, f"Package {package_type.value} is not available", None

            # Claim package
            try:
                package_price.claim_package()
            except ValueError as e:
                db.session.rollback()
                return False, str(e), None

            # Create registration
            exhibitor = ExhibitorRegistration(
                first_name=data.get("first_name").strip(),
                last_name=data.get("last_name").strip(),
                email=email,
                phone_country_code=data.get("phone_country_code", "+254"),
                phone_number=data.get("phone_number", "").strip(),
                job_title=data.get("job_title"),
                company_legal_name=data.get("company_legal_name").strip(),
                company_country=data.get("company_country"),
                company_address=data.get("company_address"),
                industry_category=data.get("industry_category"),
                company_description=data.get("company_description"),
                company_website=data.get("company_website"),
                alternate_contact_email=data.get("alternate_contact_email"),
                package_type=package_type,
                package_price_id=package_price.id,
                products_to_exhibit=data.get("products_to_exhibit"),
                number_of_staff=data.get("number_of_staff", 2),
                special_requirements=data.get("special_requirements"),
                referral_source=data.get("referral_source"),
                consent_photography=data.get("consent_photography", True),
                consent_catalog=data.get("consent_catalog", True),
                newsletter_signup=data.get("newsletter_signup", True),
                status=RegistrationStatus.PENDING,
            )

            db.session.add(exhibitor)
            db.session.flush()

            # Create payment
            payment = RegistrationService._create_payment(exhibitor)
            db.session.add(payment)
            db.session.flush()

            # Apply promo code if provided
            promo_code = data.get("promo_code", "").strip()
            if promo_code:
                success, message = RegistrationService._apply_promo_code(
                    registration=exhibitor, payment=payment, promo_code=promo_code
                )
                if success:
                    logger.info(f"Promo code applied: {promo_code}")

            db.session.commit()

            # Send registration received email with checkout link
            RegistrationService._send_registration_email(exhibitor, payment)

            logger.info(f"Exhibitor registered: {exhibitor.reference_number}")
            return True, "Registration successful!", exhibitor

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error: {str(e)}", exc_info=True)
            return False, "System error. Please try again.", None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return False, "Unexpected error. Please contact support.", None

    # ---------------------------------------------------------
    # PAYMENT COMPLETION
    # ---------------------------------------------------------

    @staticmethod
    def process_payment_completion(
        payment_id: int, transaction_id: str, payment_method: PaymentMethod
    ) -> Tuple[bool, str]:
        """
        Process payment completion: confirm registration, generate badge, send confirmation

        Called by:
        - Stripe webhook (automated)
        - Admin interface (manual confirmation for invoice/bank)
        - M-Pesa callback (when implemented)
        """
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return False, "Payment not found"

            registration = payment.registration
            if not registration:
                return False, "Registration not found"

            # Mark payment completed
            payment.mark_as_completed(transaction_id)
            payment.payment_method = payment_method

            # Confirm registration
            registration.status = RegistrationStatus.CONFIRMED
            registration.confirmed_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Payment completed: {registration.reference_number}")

            # Generate badge
            success, message, badge_url = BadgeService.generate_badge(registration.id)
            if not success:
                logger.error(f"Badge generation failed: {message}")
                # Continue - badge can be regenerated later

            # Send confirmation email with badge
            RegistrationService._send_confirmation_email(registration, badge_url)

            return True, "Payment processed successfully"

        except Exception as e:
            db.session.rollback()
            logger.error(f"Payment completion error: {str(e)}", exc_info=True)
            return False, f"Failed to process payment: {str(e)}"

    # ---------------------------------------------------------
    # HELPER METHODS
    # ---------------------------------------------------------

    @staticmethod
    def _create_payment(registration) -> Payment:
        """Create payment record for registration"""
        total_amount = registration.get_total_amount_due()

        # Set payment due date (7 days for invoice, immediate for others)
        due_date = datetime.utcnow() + timedelta(days=7)

        payment = Payment(
            registration_id=registration.id,
            subtotal=total_amount,
            tax_amount=Decimal("0.00"),
            total_amount=total_amount,
            currency="USD",
            payment_method=PaymentMethod.CARD,  # Default, updated at checkout
            payment_status=PaymentStatus.PENDING,
            payment_due_date=due_date,
        )

        return payment

    @staticmethod
    def _apply_promo_code(
        registration, payment: Payment, promo_code: str
    ) -> Tuple[bool, str]:
        """Apply promo code discount to payment"""
        try:
            promo = PromoCode.query.filter_by(code=promo_code.upper()).first()
            if not promo or not promo.is_valid():
                return False, "Invalid or expired promo code"

            if not promo.is_valid_for_user(registration.email):
                return False, "You have already used this promo code"

            # Check applicability
            if (
                registration.registration_type == "attendee"
                and not promo.applicable_to_attendees
            ):
                return False, "Code not valid for attendees"
            if (
                registration.registration_type == "exhibitor"
                and not promo.applicable_to_exhibitors
            ):
                return False, "Code not valid for exhibitors"

            # Calculate and apply discount
            discount = promo.calculate_discount(payment.subtotal)
            if discount <= 0:
                return False, "Minimum purchase amount not met"

            payment.discount_amount = discount
            payment.total_amount = payment.subtotal - discount

            # Record usage
            usage = PromoCodeUsage(
                promo_code_id=promo.id,
                registration_id=registration.id,
                payment_id=payment.id,
                discount_amount=discount,
                original_amount=payment.subtotal,
                final_amount=payment.total_amount,
            )
            db.session.add(usage)
            promo.use_code()

            return True, f"Promo applied! Saved ${discount}"

        except Exception as e:
            logger.error(f"Promo code error: {str(e)}", exc_info=True)
            return False, "Failed to apply promo code"

    # ---------------------------------------------------------
    # EMAIL NOTIFICATIONS
    # ---------------------------------------------------------

    @staticmethod
    def _send_registration_email(registration, payment: Payment):
        """
        Send initial registration email with checkout link
        Sent immediately after registration creation
        """
        try:
            # Initialize email service
            email_service = EnhancedEmailService(current_app)

            checkout_url = url_for(
                "payments.checkout", ref=registration.reference_number, _external=True
            )

            context = {
                "registration": registration,
                "payment": payment,
                "checkout_url": checkout_url,
                "amount_due": float(payment.total_amount),
                "currency": payment.currency,
                "due_date": payment.payment_due_date.strftime("%B %d, %Y")
                if payment.payment_due_date
                else None,
                "event_name": "BEEASY 2025 - Bee East Africa Symposium",
                "event_date": "March 15-17, 2025",
            }

            # Select template
            if registration.registration_type == "attendee":
                template = "registration_received_attendee"
                subject = "Registration Received - Complete Payment"
            else:
                template = "registration_received_exhibitor"
                subject = "Exhibitor Registration Received - Complete Payment"

            # Send via enhanced email service
            email_service.send_notification(
                recipient=registration.email,
                template=template,
                subject=subject,
                template_context=context,
                priority=1,  # Normal priority
            )

            logger.info(f"Registration email queued for {registration.email}")

        except Exception as e:
            logger.error(f"Failed to send registration email: {str(e)}", exc_info=True)

    @staticmethod
    def _send_confirmation_email(registration, badge_url: Optional[str]):
        """
        Send payment confirmation email with badge download link
        Sent after payment is completed and badge is generated
        """
        try:
            # Initialize email service
            email_service = EnhancedEmailService(current_app)

            badge_download_url = None
            if badge_url:
                badge_download_url = url_for(
                    "main.download_badge",
                    reference=registration.reference_number,
                    _external=True,
                )

            context = {
                "registration": registration,
                "badge_url": badge_download_url,
                "event_name": "BEEASY 2025 - Bee East Africa Symposium",
                "event_date": "March 15-17, 2025",
                "event_location": "Kenyatta International Convention Centre, Nairobi",
                "event_time": "9:00 AM - 5:00 PM",
                "whatsapp": "+254 719 740 938",
            }

            # Select template
            if registration.registration_type == "attendee":
                template = "payment_confirmed_attendee"
                subject = "Payment Confirmed - Your Badge is Ready!"
            else:
                template = "payment_confirmed_exhibitor"
                subject = "Payment Confirmed - Exhibitor Badge Ready"

            # Send via enhanced email service with high priority
            email_service.send_notification(
                recipient=registration.email,
                template=template,
                subject=subject,
                template_context=context,
                priority=0,  # High priority for confirmations
            )

            logger.info(f"Confirmation email queued for {registration.email}")

        except Exception as e:
            logger.error(f"Failed to send confirmation email: {str(e)}", exc_info=True)
