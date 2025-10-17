"""
Registration Service for BEEASY2025 Event Registration System

Handles all registration business logic including:
- Attendee registration with ticket claiming
- Exhibitor registration with package allocation
- Payment processing and tracking
- Promo code application
- Add-on purchases
- Email notifications
- Status management

Follows established service pattern:
- Static methods
- Returns tuple: (success: bool, message: str, object: Optional[Model])
- Comprehensive error handling with logging
- Database transaction management
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any, List

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    Registration,
    AttendeeRegistration,
    ExhibitorRegistration,
    RegistrationStatus,
    TicketPrice,
    ExhibitorPackagePrice,
    AddOnItem,
    AddOnPurchase,
    AttendeeTicketType,
    ExhibitorPackage,
)
from app.models import (
    Payment,
    PaymentStatus,
    PaymentMethod,
    # PaymentType,
    PromoCode,
    PromoCodeUsage,
    EmailLog,
)
from app.utils.model_utils import ValidationHelpers

# Configure logger
logger = logging.getLogger('registration_service')


# ============================================
# REGISTRATION SERVICE
# ============================================

class RegistrationService:
    """Service class for handling event registrations"""

    # ---------------------------------------------------------
    # ATTENDEE REGISTRATION
    # ---------------------------------------------------------

    @staticmethod
    def register_attendee(data: Dict[str, Any]) -> Tuple[bool, str, Optional[AttendeeRegistration]]:
        """
        Register a new event attendee with comprehensive data collection

        Args:
            data: Dictionary containing registration fields:
                Required:
                    - first_name, last_name, email, phone_number
                    - ticket_type (AttendeeTicketType enum or string)
                Optional:
                    - phone_country_code, organization, job_title
                    - professional_category, years_in_beekeeping
                    - session_interests, networking_goals
                    - dietary_requirement, dietary_notes
                    - accessibility_needs, tshirt_size
                    - country, city, needs_visa_letter
                    - linkedin_url, bio
                    - referral_source

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
            ticket_price = TicketPrice.query.filter_by(
                ticket_type=ticket_type
            ).first()

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
                industry_sector=data.get('industry_sector'),
                years_in_beekeeping=data.get('years_in_beekeeping'),
                company_size=data.get('company_size'),

                # Event preferences (optional)
                session_interests=data.get('session_interests'),
                networking_goals=data.get('networking_goals'),
                workshop_preferences=data.get('workshop_preferences'),
                topics_of_interest=data.get('topics_of_interest'),

                # Dietary and accessibility (optional)
                dietary_requirement=data.get('dietary_requirement'),
                dietary_notes=data.get('dietary_notes'),
                accessibility_needs=data.get('accessibility_needs'),
                special_requirements=data.get('special_requirements'),
                tshirt_size=data.get('tshirt_size'),

                # Travel (optional)
                country=data.get('country'),
                city=data.get('city'),
                needs_visa_letter=data.get('needs_visa_letter', False),
                needs_accommodation=data.get('needs_accommodation', False),
                arrival_date=data.get('arrival_date'),
                departure_date=data.get('departure_date'),
                accommodation_type=data.get('accommodation_type'),

                # Networking profile (optional)
                linkedin_url=data.get('linkedin_url'),
                twitter_handle=data.get('twitter_handle'),
                bio=data.get('bio'),

                # Objectives (optional)
                attendance_objectives=data.get('attendance_objectives'),
                expectations=data.get('expectations'),

                # Marketing (optional)
                referral_source=data.get('referral_source'),

                # Consent (defaults to True)
                consent_photography=data.get('consent_photography', True),
                consent_networking=data.get('consent_networking', True),
                consent_data_sharing=data.get('consent_data_sharing', False),
                newsletter_signup=data.get('newsletter_signup', True),

                # Status
                status=RegistrationStatus.PENDING,
            )

            db.session.add(attendee)
            db.session.flush()  # Get ID without committing

            logger.info(f"Attendee registration created: {attendee.reference_number}")

            # Step 6: Create initial payment record
            ticket_amount = ticket_price.get_current_price()

            payment = Payment(
                registration_id=attendee.id,
                # payment_type=PaymentType.INITIAL,
                subtotal=ticket_amount,
                payment_method=PaymentMethod.CARD,  # Default, can be updated
                payment_status=PaymentStatus.PENDING,
                currency=ticket_price.currency,
            )

            # Calculate tax (16% VAT)
            tax_rate = Decimal('0.16')
            payment.calculate_tax(float(tax_rate))
            payment.calculate_total()

            db.session.add(payment)

            # Step 7: Apply promo code if provided
            promo_code = data.get('promo_code')
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

            # Step 9: Send confirmation email (non-blocking)
            try:
                RegistrationService._send_attendee_confirmation_email(attendee, payment)
            except Exception as email_error:
                logger.error(f"Failed to send confirmation email: {email_error}")
                # Don't fail registration if email fails

            logger.info(f"Attendee registration completed: {attendee.reference_number}")

            return (
                True,
                f"Registration successful! Reference: {attendee.reference_number}",
                attendee
            )

        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error during attendee registration: {str(e)}", exc_info=True)
            return False, "A registration with this email already exists.", None

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
        Register a new exhibitor with comprehensive company data

        Args:
            data: Dictionary containing registration fields:
                Required:
                    - first_name, last_name, email, phone_number
                    - company_legal_name, company_country, company_address
                    - industry_category, company_description
                    - package_type (ExhibitorPackage enum or string)
                Optional:
                    - company_trading_name, company_registration_number
                    - company_website, company_email, company_phone
                    - secondary_contact_*, billing_contact_*
                    - products_services, target_customers
                    - booth preferences, requirements
                    - marketing assets, social media
                    - legal/compliance info

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
                company_trading_name=data.get('company_trading_name'),
                company_registration_number=data.get('company_registration_number'),
                company_website=data.get('company_website'),
                company_email=data.get('company_email'),
                company_phone=data.get('company_phone'),
                tax_id=data.get('tax_id'),
                vat_number=data.get('vat_number'),
                billing_address=data.get('billing_address'),

                # Contacts (optional)
                secondary_contact_name=data.get('secondary_contact_name'),
                secondary_contact_email=data.get('secondary_contact_email'),
                secondary_contact_phone=data.get('secondary_contact_phone'),
                secondary_contact_title=data.get('secondary_contact_title'),

                billing_contact_name=data.get('billing_contact_name'),
                billing_contact_email=data.get('billing_contact_email'),
                billing_contact_phone=data.get('billing_contact_phone'),

                # Company profile (optional)
                products_services=data.get('products_services'),
                target_customers=data.get('target_customers'),
                years_in_business=data.get('years_in_business'),
                employee_count=data.get('employee_count'),

                # Package
                package_type=package_type,
                package_price_id=package_price.id,

                # Booth preferences (optional)
                booth_preference_corner=data.get('booth_preference_corner', False),
                booth_preference_entrance=data.get('booth_preference_entrance', False),
                booth_preference_area=data.get('booth_preference_area'),
                booth_preference_notes=data.get('booth_preference_notes'),

                # Booth requirements (optional)
                number_of_staff=data.get('number_of_staff', 2),
                exhibitor_badges_needed=data.get('exhibitor_badges_needed', 2),
                electricity_required=data.get('electricity_required', False),
                electricity_watts=data.get('electricity_watts'),
                water_connection_required=data.get('water_connection_required', False),
                internet_required=data.get('internet_required', False),
                needs_storage=data.get('needs_storage', False),

                # Products to exhibit (optional)
                products_to_exhibit=data.get('products_to_exhibit'),
                product_demonstrations=data.get('product_demonstrations'),
                special_requirements=data.get('special_requirements'),

                # Setup logistics (optional)
                setup_date=data.get('setup_date'),
                setup_time=data.get('setup_time'),
                teardown_date=data.get('teardown_date'),
                shipping_method=data.get('shipping_method'),
                expected_delivery_date=data.get('expected_delivery_date'),
                delivery_contact_name=data.get('delivery_contact_name'),
                delivery_contact_phone=data.get('delivery_contact_phone'),

                # Accommodation (optional)
                accommodation_rooms_needed=data.get('accommodation_rooms_needed', 0),
                accommodation_checkin=data.get('accommodation_checkin'),
                accommodation_checkout=data.get('accommodation_checkout'),
                accommodation_notes=data.get('accommodation_notes'),

                # Marketing assets (optional)
                company_logo_url=data.get('company_logo_url'),
                company_video_url=data.get('company_video_url'),
                brochure_url=data.get('brochure_url'),
                product_images=data.get('product_images'),

                # Social media (optional)
                facebook_url=data.get('facebook_url'),
                instagram_handle=data.get('instagram_handle'),
                linkedin_url=data.get('linkedin_url'),
                twitter_handle=data.get('twitter_handle'),
                youtube_channel=data.get('youtube_channel'),

                # Legal/compliance (optional)
                has_liability_insurance=data.get('has_liability_insurance', False),
                insurance_policy_number=data.get('insurance_policy_number'),
                insurance_coverage_amount=data.get('insurance_coverage_amount'),
                insurance_expiry_date=data.get('insurance_expiry_date'),
                products_comply_regulations=data.get('products_comply_regulations', False),
                has_import_permits=data.get('has_import_permits', False),

                # Payment (optional)
                purchase_order_number=data.get('purchase_order_number'),
                payment_terms=data.get('payment_terms'),

                # Location
                country=data.get('country') or data.get('company_country'),
                city=data.get('city'),

                # Marketing
                referral_source=data.get('referral_source'),

                # Consent
                consent_photography=data.get('consent_photography', True),
                consent_networking=data.get('consent_networking', True),
                newsletter_signup=data.get('newsletter_signup', True),

                # Status
                status=RegistrationStatus.PENDING,
            )

            db.session.add(exhibitor)
            db.session.flush()  # Get ID without committing

            logger.info(f"Exhibitor registration created: {exhibitor.reference_number}")

            # Step 6: Process add-ons if provided
            addon_items = data.get('addons', [])
            total_addon_cost = Decimal('0.00')

            if addon_items:
                success, message, addon_cost = RegistrationService._process_addons(
                    registration=exhibitor,
                    addon_items=addon_items
                )
                if success:
                    total_addon_cost = addon_cost
                    logger.info(f"Add-ons processed: ${addon_cost}")
                else:
                    logger.warning(f"Add-on processing issue: {message}")

            # Step 7: Calculate total amount
            base_price = Decimal(str(package_price.price))

            # Add booth upgrade costs
            upgrade_cost = Decimal('0.00')
            if exhibitor.booth_preference_corner:
                upgrade_cost += Decimal('200.00')
            if exhibitor.booth_preference_entrance:
                upgrade_cost += Decimal('150.00')

            subtotal = base_price + upgrade_cost + total_addon_cost

            # Step 8: Create initial payment record
            payment_method = data.get('payment_method', 'invoice')
            if payment_method == 'invoice':
                payment_method = PaymentMethod.INVOICE
            elif payment_method == 'card':
                payment_method = PaymentMethod.CARD
            elif payment_method == 'bank_transfer':
                payment_method = PaymentMethod.BANK_TRANSFER
            else:
                payment_method = PaymentMethod.INVOICE

            payment = Payment(
                registration_id=exhibitor.id,
                # payment_type=PaymentType.INITIAL,
                subtotal=subtotal,
                payment_method=payment_method,
                payment_status=PaymentStatus.PENDING,
                currency=package_price.currency,
            )

            # Set due date for invoices (30 days)
            if payment_method == PaymentMethod.INVOICE:
                payment.payment_due_date = datetime.utcnow() + timedelta(days=30)

            # Calculate tax
            tax_rate = Decimal('0.16')
            payment.calculate_tax(float(tax_rate))
            payment.calculate_total()

            db.session.add(payment)

            # Step 9: Apply promo code if provided
            promo_code = data.get('promo_code')
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

            # Step 10: Commit transaction
            db.session.commit()

            # Step 11: Send confirmation email (non-blocking)
            try:
                RegistrationService._send_exhibitor_confirmation_email(exhibitor, payment)
            except Exception as email_error:
                logger.error(f"Failed to send confirmation email: {email_error}")
                # Don't fail registration if email fails

            logger.info(f"Exhibitor registration completed: {exhibitor.reference_number}")

            return (
                True,
                f"Registration successful! Reference: {exhibitor.reference_number}",
                exhibitor
            )

        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error during exhibitor registration: {str(e)}", exc_info=True)
            return False, "A registration with this email already exists.", None

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during exhibitor registration: {str(e)}", exc_info=True)
            return False, "A system error occurred. Please try again later.", None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in register_exhibitor: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred. Please contact support.", None

    # ---------------------------------------------------------
    # PAYMENT MANAGEMENT
    # ---------------------------------------------------------

    @staticmethod
    def process_payment_completion(
        payment_id: int,
        transaction_id: str,
        payment_method: Optional[PaymentMethod] = None
    ) -> Tuple[bool, str]:
        """
        Mark payment as completed and update registration status

        Args:
            payment_id: Payment record ID
            transaction_id: Transaction ID from payment gateway
            payment_method: Optional payment method override

        Returns:
            Tuple of (success, message)
        """
        try:
            payment = Payment.query.get(payment_id)

            if not payment:
                return False, "Payment not found."

            if payment.is_paid:
                return False, "Payment already completed."

            # Update payment method if provided
            if payment_method:
                payment.payment_method = payment_method

            # Mark payment as completed
            payment.mark_as_completed(transaction_id=transaction_id)

            # Update registration status if fully paid
            registration = payment.registration
            if registration.is_fully_paid():
                registration.status = RegistrationStatus.CONFIRMED
                registration.confirmed_at = datetime.utcnow()

                logger.info(f"Registration confirmed: {registration.reference_number}")

                # Generate QR code data
                registration.qr_code_data = f"BEEASY2025-{registration.id}-{registration.email}"

            db.session.commit()

            # Send receipt email (non-blocking)
            try:
                RegistrationService._send_payment_receipt_email(registration, payment)
            except Exception as email_error:
                logger.error(f"Failed to send receipt email: {email_error}")

            return True, "Payment completed successfully."

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error processing payment: {str(e)}", exc_info=True)
            return False, "Failed to process payment. Please contact support."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error processing payment: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred."

    @staticmethod
    def process_refund(
        payment_id: int,
        refund_amount: Decimal,
        reason: str,
        refunded_by: str
    ) -> Tuple[bool, str]:
        """
        Process a refund for a payment

        Args:
            payment_id: Payment record ID
            refund_amount: Amount to refund
            reason: Refund reason
            refunded_by: User who initiated refund

        Returns:
            Tuple of (success, message)
        """
        try:
            payment = Payment.query.get(payment_id)

            if not payment:
                return False, "Payment not found."

            if not payment.is_paid:
                return False, "Can only refund completed payments."

            # Process refund
            payment.process_refund(
                amount=refund_amount,
                reason=reason,
                refunded_by=refunded_by
            )

            # Update registration status
            registration = payment.registration
            registration.status = RegistrationStatus.REFUNDED

            db.session.commit()

            logger.info(f"Refund processed: {payment.payment_reference} - ${refund_amount}")

            # Send refund notification email
            try:
                RegistrationService._send_refund_notification_email(registration, payment)
            except Exception as email_error:
                logger.error(f"Failed to send refund email: {email_error}")

            return True, f"Refund of ${refund_amount} processed successfully."

        except ValueError as e:
            db.session.rollback()
            return False, str(e)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error processing refund: {str(e)}", exc_info=True)
            return False, "Failed to process refund."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error processing refund: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred."

    # ---------------------------------------------------------
    # STATUS MANAGEMENT
    # ---------------------------------------------------------

    @staticmethod
    def cancel_registration(
        registration_id: int,
        reason: str,
        cancelled_by: str
    ) -> Tuple[bool, str]:
        """
        Cancel a registration and release inventory

        Args:
            registration_id: Registration ID
            reason: Cancellation reason
            cancelled_by: User who cancelled

        Returns:
            Tuple of (success, message)
        """
        try:
            registration = Registration.query.get(registration_id)

            if not registration:
                return False, "Registration not found."

            if registration.status == RegistrationStatus.CANCELLED:
                return False, "Registration already cancelled."

            # Release inventory
            if isinstance(registration, AttendeeRegistration):
                if registration.ticket_price:
                    registration.ticket_price.release_tickets(1)
                    logger.info(f"Ticket released: {registration.ticket_type.value}")

            elif isinstance(registration, ExhibitorRegistration):
                if registration.package_price:
                    registration.package_price.release_package()
                    logger.info(f"Package released: {registration.package_type.value}")

            # Update status
            registration.status = RegistrationStatus.CANCELLED
            registration.admin_notes = f"Cancelled by {cancelled_by}: {reason}"

            db.session.commit()

            logger.info(f"Registration cancelled: {registration.reference_number}")

            # Send cancellation email
            try:
                RegistrationService._send_cancellation_email(registration, reason)
            except Exception as email_error:
                logger.error(f"Failed to send cancellation email: {email_error}")

            return True, "Registration cancelled successfully."

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error cancelling registration: {str(e)}", exc_info=True)
            return False, "Failed to cancel registration."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error cancelling registration: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred."

    # ---------------------------------------------------------
    # HELPER METHODS (PRIVATE)
    # ---------------------------------------------------------

    @staticmethod
    def _apply_promo_code(
        registration: Registration,
        payment: Payment,
        promo_code: str
    ) -> Tuple[bool, str]:
        """Apply promo code to payment"""
        try:
            promo = PromoCode.query.filter_by(code=promo_code.upper()).first()

            if not promo:
                return False, "Invalid promo code."

            if not promo.is_valid():
                return False, "Promo code is expired or inactive."

            if not promo.is_valid_for_user(registration.email):
                return False, "You have already used this promo code."

            # Check applicability
            if isinstance(registration, AttendeeRegistration) and not promo.applicable_to_attendees:
                return False, "This promo code is not valid for attendees."

            if isinstance(registration, ExhibitorRegistration) and not promo.applicable_to_exhibitors:
                return False, "This promo code is not valid for exhibitors."

            # Calculate discount
            original_amount = payment.subtotal
            discount = promo.calculate_discount(original_amount)

            if discount <= 0:
                return False, "Promo code does not apply to this purchase."

            # Apply discount
            payment.discount_amount = discount
            payment.calculate_total()

            # Record usage
            usage = PromoCodeUsage(
                promo_code_id=promo.id,
                registration_id=registration.id,
                payment_id=payment.id,
                original_amount=original_amount,
                discount_amount=discount,
                final_amount=payment.total_amount
            )
            db.session.add(usage)

            # Increment usage count
            promo.use_code()

            return True, f"Promo code applied! You saved ${discount}."

        except Exception as e:
            logger.error(f"Error applying promo code: {str(e)}")
            return False, "Failed to apply promo code."

    @staticmethod
    def _process_addons(
        registration: Registration,
        addon_items: List[Dict[str, Any]]
    ) -> Tuple[bool, str, Decimal]:
        """
        Process add-on purchases

        Args:
            registration: Registration object
            addon_items: List of dicts with 'addon_id' and 'quantity'

        Returns:
            Tuple of (success, message, total_cost)
        """
        total_cost = Decimal('0.00')

        try:
            for item in addon_items:
                addon_id = item.get('addon_id')
                quantity = item.get('quantity', 1)

                addon = AddOnItem.query.get(addon_id)

                if not addon:
                    logger.warning(f"Add-on not found: {addon_id}")
                    continue

                if not addon.is_available():
                    logger.warning(f"Add-on not available: {addon.name}")
                    continue

                # Check quantity limit
                if addon.max_quantity_per_registration and quantity > addon.max_quantity_per_registration:
                    quantity = addon.max_quantity_per_registration

                # Create purchase
                purchase = AddOnPurchase(
                    registration_id=registration.id,
                    addon_id=addon.id,
                    quantity=quantity,
                    unit_price=addon.price,
                    total_price=addon.price * quantity,
                    currency=addon.currency,
                    approved=not addon.requires_approval
                )

                db.session.add(purchase)
                total_cost += purchase.total_price

                logger.info(f"Add-on added: {addon.name} x{quantity}")

            return True, f"{len(addon_items)} add-ons processed", total_cost

        except Exception as e:
            logger.error(f"Error processing add-ons: {str(e)}")
            return False, "Failed to process some add-ons", total_cost

    @staticmethod
    def _send_attendee_confirmation_email(
        attendee: AttendeeRegistration,
        payment: Payment
    ) -> None:
        """Send confirmation email to attendee (placeholder)"""
        # TODO: Implement email sending using existing email service
        # This should integrate with your email service
        logger.info(f"Confirmation email queued for {attendee.email}")

        # Log email
        email_log = EmailLog(
            registration_id=attendee.id,
            recipient_email=attendee.email,
            recipient_name=attendee.computed_full_name,
            email_type='registration_confirmation',
            subject='Registration Confirmation - BEEASY2025',
            status='sent'
        )
        db.session.add(email_log)

    @staticmethod
    def _send_exhibitor_confirmation_email(
        exhibitor: ExhibitorRegistration,
        payment: Payment
    ) -> None:
        """Send confirmation email to exhibitor (placeholder)"""
        logger.info(f"Confirmation email queued for {exhibitor.email}")

        # Log email
        email_log = EmailLog(
            registration_id=exhibitor.id,
            recipient_email=exhibitor.email,
            recipient_name=exhibitor.computed_full_name,
            email_type='exhibitor_registration_confirmation',
            subject='Exhibitor Registration Confirmation - BEEASY2025',
            status='sent'
        )
        db.session.add(email_log)

    @staticmethod
    def _send_payment_receipt_email(
        registration: Registration,
        payment: Payment
    ) -> None:
        """Send payment receipt email (placeholder)"""
        logger.info(f"Receipt email queued for {registration.email}")

        # Log email
        email_log = EmailLog(
            registration_id=registration.id,
            recipient_email=registration.email,
            recipient_name=registration.computed_full_name,
            email_type='payment_receipt',
            subject=f'Payment Receipt - {payment.payment_reference}',
            status='sent'
        )
        db.session.add(email_log)

    @staticmethod
    def _send_refund_notification_email(
        registration: Registration,
        payment: Payment
    ) -> None:
        """Send refund notification email (placeholder)"""
        logger.info(f"Refund notification queued for {registration.email}")

        # Log email
        email_log = EmailLog(
            registration_id=registration.id,
            recipient_email=registration.email,
            recipient_name=registration.computed_full_name,
            email_type='refund_notification',
            subject='Refund Processed - BEEASY2025',
            status='sent'
        )
        db.session.add(email_log)

    @staticmethod
    def _send_cancellation_email(
        registration: Registration,
        reason: str
    ) -> None:
        """Send cancellation email (placeholder)"""
        logger.info(f"Cancellation email queued for {registration.email}")

        # Log email
        email_log = EmailLog(
            registration_id=registration.id,
            recipient_email=registration.email,
            recipient_name=registration.computed_full_name,
            email_type='registration_cancellation',
            subject='Registration Cancelled - BEEASY2025',
            status='sent'
        )
        db.session.add(email_log)
