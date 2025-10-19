"""
Registration Service for BEEASY2025 Event Registration System
Handles registration, badge generation, and email notifications
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any

from flask import current_app, url_for, render_template
from flask_mail import Message
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db, mail
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

logger = logging.getLogger('registration_service')


class RegistrationService:
    """Service class for handling event registrations"""

    # ---------------------------------------------------------
    # ATTENDEE REGISTRATION
    # ---------------------------------------------------------

    @staticmethod
    def register_attendee(data: Dict[str, Any]) -> Tuple[bool, str, Optional[AttendeeRegistration]]:
        """
        Register a new event attendee

        Args:
            data: Dictionary containing registration fields

        Returns:
            Tuple of (success, message, registration)
        """
        try:
            logger.info(f"Starting attendee registration for {data.get('email')}")

            # Step 1: Validate email availability
            email = data.get('email', '').lower().strip()
            is_available, msg = ValidationHelpers.check_email_availability(
                email=email,
                registration_type='attendee'
            )

            if not is_available:
                logger.warning(f"Duplicate attendee registration attempt: {email}")
                return False, msg, None

            # Step 2: Get and validate ticket type
            ticket_type = data.get('ticket_type')
            if isinstance(ticket_type, str):
                try:
                    ticket_type = AttendeeTicketType[ticket_type.upper()]
                except KeyError:
                    return False, f"Invalid ticket type: {ticket_type}", None

            # Step 3: Get ticket price and check availability
            ticket_price = TicketPrice.query.filter_by(ticket_type=ticket_type).first()

            if not ticket_price:
                logger.error(f"Ticket price not found for type: {ticket_type}")
                return False, "Selected ticket type is not available.", None

            if not ticket_price.is_available():
                logger.warning(f"Ticket {ticket_type} not available")
                return False, f"Sorry, {ticket_price.name} is sold out.", None

            # Step 4: Atomically claim ticket
            try:
                ticket_price.claim_tickets(quantity=1)
                logger.info(f"Ticket claimed: {ticket_type.value}")
            except ValueError as e:
                db.session.rollback()
                logger.warning(f"Failed to claim ticket: {str(e)}")
                return False, str(e), None

            # Step 5: Create attendee registration
            attendee = AttendeeRegistration(
                # Basic info (required)
                first_name=data.get('first_name').strip(),
                last_name=data.get('last_name').strip(),
                email=email,
                phone_country_code=data.get('phone_country_code', '+254'),
                phone_number=data.get('phone_number', '').strip(),

                # Ticket
                ticket_type=ticket_type,
                ticket_price_id=ticket_price.id,

                # Professional info (optional)
                organization=data.get('organization', '').strip() or None,
                job_title=data.get('job_title', '').strip() or None,
                professional_category=data.get('professional_category'),

                # Event preferences (consolidated to single JSONB field)
                event_preferences=data.get('event_preferences'),

                # Dietary and accessibility (operational)
                dietary_requirement=data.get('dietary_requirement'),
                dietary_notes=data.get('dietary_notes'),
                accessibility_needs=data.get('accessibility_needs'),
                special_requirements=data.get('special_requirements'),

                # Travel (operational)
                needs_visa_letter=data.get('needs_visa_letter', False),

                # Marketing
                referral_source=data.get('referral_source'),

                # Consent
                consent_photography=data.get('consent_photography', True),
                consent_networking=data.get('consent_networking', True),
                consent_data_sharing=data.get('consent_data_sharing', False),
                newsletter_signup=data.get('newsletter_signup', True),

                # Status
                status=RegistrationStatus.PENDING,
            )

            db.session.add(attendee)
            db.session.flush()

            logger.info(f"Attendee registration created: {attendee.reference_number}")

            # Step 6: Create payment record
            payment = RegistrationService._create_payment(attendee)
            db.session.add(payment)
            db.session.flush()

            # Step 7: Apply promo code if provided
            promo_code = data.get('promo_code', '').strip()
            if promo_code:
                success, message = RegistrationService._apply_promo_code(
                    registration=attendee,
                    payment=payment,
                    promo_code=promo_code
                )
                if success:
                    logger.info(f"Promo code applied: {promo_code}")
                else:
                    logger.warning(f"Promo code failed: {message}")

            # Step 8: Commit transaction
            db.session.commit()

            logger.info(f"Attendee registration complete: {attendee.reference_number}")

            return True, "Registration successful!", attendee

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during attendee registration: {str(e)}", exc_info=True)
            return False, "A system error occurred. Please try again later.", None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in register_attendee: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred. Please contact support.", None

    # ---------------------------------------------------------
    # EXHIBITOR REGISTRATION
    # ---------------------------------------------------------

    @staticmethod
    def register_exhibitor(data: Dict[str, Any]) -> Tuple[bool, str, Optional[ExhibitorRegistration]]:
        """
        Register a new exhibitor

        Args:
            data: Dictionary containing registration fields

        Returns:
            Tuple of (success, message, registration)
        """
        try:
            logger.info(f"Starting exhibitor registration for {data.get('email')}")

            # Step 1: Validate email availability
            email = data.get('email', '').lower().strip()
            is_available, msg = ValidationHelpers.check_email_availability(
                email=email,
                registration_type='exhibitor'
            )

            if not is_available:
                logger.warning(f"Duplicate exhibitor registration attempt: {email}")
                return False, msg, None

            # Step 2: Get and validate package type
            package_type = data.get('package_type')
            if isinstance(package_type, str):
                try:
                    package_type = ExhibitorPackage[package_type.upper()]
                except KeyError:
                    return False, f"Invalid package type: {package_type}", None

            # Step 3: Get package price and check availability
            package_price = ExhibitorPackagePrice.query.filter_by(
                package_type=package_type
            ).first()

            if not package_price:
                logger.error(f"Package price not found for type: {package_type}")
                return False, "Selected package is not available.", None

            if not package_price.is_available():
                logger.warning(f"Package {package_type} not available")
                return False, f"Sorry, {package_price.name} is sold out.", None

            # Step 4: Atomically claim package
            try:
                package_price.claim_package()
                logger.info(f"Package claimed: {package_type.value}")
            except ValueError as e:
                db.session.rollback()
                logger.warning(f"Failed to claim package: {str(e)}")
                return False, str(e), None

            # Step 5: Create exhibitor registration
            exhibitor = ExhibitorRegistration(
                # Contact person (required)
                first_name=data.get('first_name').strip(),
                last_name=data.get('last_name').strip(),
                email=email,
                phone_country_code=data.get('phone_country_code', '+254'),
                phone_number=data.get('phone_number', '').strip(),
                job_title=data.get('job_title'),

                # Company info (required)
                company_legal_name=data.get('company_legal_name').strip(),
                company_country=data.get('company_country'),
                company_address=data.get('company_address'),
                industry_category=data.get('industry_category'),
                company_description=data.get('company_description'),

                # Company info (optional)
                company_website=data.get('company_website'),
                alternate_contact_email=data.get('alternate_contact_email'),

                # Package
                package_type=package_type,
                package_price_id=package_price.id,

                # Exhibition details
                products_to_exhibit=data.get('products_to_exhibit'),
                number_of_staff=data.get('number_of_staff', 2),
                special_requirements=data.get('special_requirements'),

                # Marketing
                referral_source=data.get('referral_source'),

                # Consent
                consent_photography=data.get('consent_photography', True),
                consent_catalog=data.get('consent_catalog', True),
                newsletter_signup=data.get('newsletter_signup', True),

                # Status
                status=RegistrationStatus.PENDING,
            )

            db.session.add(exhibitor)
            db.session.flush()

            logger.info(f"Exhibitor registration created: {exhibitor.reference_number}")

            # Step 6: Create payment record
            payment = RegistrationService._create_payment(exhibitor)
            db.session.add(payment)
            db.session.flush()

            # Step 7: Apply promo code if provided
            promo_code = data.get('promo_code', '').strip()
            if promo_code:
                success, message = RegistrationService._apply_promo_code(
                    registration=exhibitor,
                    payment=payment,
                    promo_code=promo_code
                )
                if success:
                    logger.info(f"Promo code applied: {promo_code}")
                else:
                    logger.warning(f"Promo code failed: {message}")

            # Step 8: Commit transaction
            db.session.commit()

            logger.info(f"Exhibitor registration complete: {exhibitor.reference_number}")

            return True, "Registration successful!", exhibitor

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during exhibitor registration: {str(e)}", exc_info=True)
            return False, "A system error occurred. Please try again later.", None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in register_exhibitor: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred. Please contact support.", None

    # ---------------------------------------------------------
    # PAYMENT COMPLETION
    # ---------------------------------------------------------

    @staticmethod
    def process_payment_completion(
        payment_id: int,
        transaction_id: str,
        payment_method: PaymentMethod
    ) -> Tuple[bool, str]:
        """
        Process payment completion, confirm registration, generate badge, send email

        Args:
            payment_id: Payment record ID
            transaction_id: External transaction ID
            payment_method: Payment method used

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get payment
            payment = Payment.query.get(payment_id)
            if not payment:
                return False, "Payment record not found"

            # Get registration
            registration = payment.registration
            if not registration:
                return False, "Registration not found"

            # Mark payment as completed
            payment.mark_as_completed(transaction_id)
            payment.payment_method = payment_method

            # Update registration status
            registration.status = RegistrationStatus.CONFIRMED
            registration.confirmed_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Payment completed for {registration.reference_number}")

            # Generate badge
            success, message, badge_url = BadgeService.generate_badge(registration.id)

            if not success:
                logger.error(f"Badge generation failed for {registration.reference_number}: {message}")
                # Continue anyway - can regenerate later

            # Send confirmation email with badge
            RegistrationService._send_confirmation_email(registration, badge_url)

            return True, "Payment processed successfully"

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing payment completion: {str(e)}", exc_info=True)
            return False, f"Failed to process payment: {str(e)}"

    # ---------------------------------------------------------
    # HELPER METHODS
    # ---------------------------------------------------------

    @staticmethod
    def _create_payment(registration) -> Payment:
        """Create payment record for registration"""
        total_amount = registration.get_total_amount_due()

        payment = Payment(
            registration_id=registration.id,
            subtotal=total_amount,
            tax_amount=Decimal('0.00'),
            total_amount=total_amount,
            currency='USD',
            payment_method=PaymentMethod.CARD,  # Default, will be updated
            payment_status=PaymentStatus.PENDING
        )

        return payment

    @staticmethod
    def _apply_promo_code(
        registration,
        payment: Payment,
        promo_code: str
    ) -> Tuple[bool, str]:
        """
        Apply promo code to payment

        Args:
            registration: Registration object
            payment: Payment object
            promo_code: Promo code string

        Returns:
            Tuple of (success, message)
        """
        try:
            # Find promo code
            promo = PromoCode.query.filter_by(code=promo_code.upper()).first()

            if not promo:
                return False, "Invalid promo code"

            # Validate promo code
            if not promo.is_valid():
                return False, "Promo code is expired or inactive"

            # Check if user already used this code
            if not promo.is_valid_for_user(registration.email):
                return False, "You have already used this promo code"

            # Check applicability
            if registration.registration_type == 'attendee' and not promo.applicable_to_attendees:
                return False, "This code is not valid for attendees"

            if registration.registration_type == 'exhibitor' and not promo.applicable_to_exhibitors:
                return False, "This code is not valid for exhibitors"

            # Calculate discount
            discount = promo.calculate_discount(payment.subtotal)

            if discount <= 0:
                return False, "Minimum purchase amount not met"

            # Apply discount to payment
            payment.discount_amount = discount
            payment.total_amount = payment.subtotal - discount

            # Record promo code usage
            usage = PromoCodeUsage(
                promo_code_id=promo.id,
                registration_id=registration.id,
                payment_id=payment.id,
                discount_amount=discount,
                original_amount=payment.subtotal,
                final_amount=payment.total_amount
            )

            db.session.add(usage)

            # Increment promo code usage
            promo.use_code()

            logger.info(f"Promo code {promo_code} applied: ${discount} discount")

            return True, f"Promo code applied! You saved ${discount}"

        except Exception as e:
            logger.error(f"Error applying promo code: {str(e)}", exc_info=True)
            return False, "Failed to apply promo code"

    @staticmethod
    def _send_confirmation_email(registration, badge_url: Optional[str] = None):
        """
        Send registration confirmation email with badge download link

        Args:
            registration: Registration object
            badge_url: Badge download URL (optional)
        """
        try:
            # Generate badge download URL
            if badge_url:
                badge_download_url = url_for(
                    'main.download_badge',
                    reference=registration.reference_number,
                    _external=True
                )
            else:
                badge_download_url = None

            # Prepare email context
            context = {
                'registration': registration,
                'badge_url': badge_download_url,
                'event_name': current_app.config.get('EVENT_NAME', 'BEEASY 2025'),
                'event_date': 'March 15-17, 2025',
                'event_location': 'Nairobi, Kenya',
                'support_email': current_app.config.get('MAIL_DEFAULT_SENDER'),
            }

            # Determine email template based on registration type
            if registration.registration_type == 'attendee':
                template = 'registration_confirmation_attendee'
                subject = 'Registration Confirmed - BEEASY 2025'
            else:
                template = 'registration_confirmation_exhibitor'
                subject = 'Exhibitor Registration Confirmed - BEEASY 2025'

            # Render email
            html_body = render_template(f'emails/{template}.html', **context)
            text_body = render_template(f'emails/{template}.txt', **context)

            # Send email
            msg = Message(
                subject=subject,
                sender=current_app.config['MAIL_DEFAULT_SENDER'],
                recipients=[registration.email]
            )
            msg.html = html_body
            msg.body = text_body

            mail.send(msg)

            logger.info(f"Confirmation email sent to {registration.email}")

        except Exception as e:
            logger.error(f"Failed to send confirmation email: {str(e)}", exc_info=True)
            # Don't fail the registration if email fails
