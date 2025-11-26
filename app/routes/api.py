"""
API Routes for Admin Panel
Provides RESTful endpoints for AJAX operations, data fetching, and interactive features.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models.payment import EmailLog, ExchangeRate, Payment, PromoCode
from app.models.registration import (
    AddOnItem,
    AttendeeRegistration,
    AttendeeTicketType,
    ExhibitorPackage,
    ExhibitorRegistration,
    Registration,
    RegistrationStatus,
    TicketPrice,
)
from app.models.user import User, UserRole
from app.services.badge_service import BadgeService
from app.services.registration_service import RegistrationService

# Initialize logger
logger = logging.getLogger(__name__)

# Create Blueprint
api_bp = Blueprint("api", __name__)


# ============================================================================
# API DECORATORS
# ============================================================================


def api_admin_required(f):
    """Decorator for API endpoints that require admin/staff access"""
    from functools import wraps

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in [
            UserRole.ADMIN,
            UserRole.STAFF,
            UserRole.ORGANIZER,
        ]:
            return jsonify({"success": False, "error": "Unauthorized access"}), 403
        return f(*args, **kwargs)

    return decorated_function


def api_admin_only(f):
    """Decorator for API endpoints that require admin role only"""
    from functools import wraps

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated_function


# ============================================================================
# DASHBOARD & STATISTICS API
# ============================================================================


@api_bp.route("/dashboard/stats")
@api_admin_required
def dashboard_stats():
    """Get dashboard statistics (for real-time updates)"""
    try:
        total_registrations = Registration.query.count()
        total_attendees = AttendeeRegistration.query.count()
        total_exhibitors = ExhibitorRegistration.query.count()

        confirmed_registrations = Registration.query.filter_by(
            status=RegistrationStatus.CONFIRMED
        ).count()
        pending_registrations = Registration.query.filter_by(
            status=RegistrationStatus.PENDING_PAYMENT
        ).count()

        total_revenue = (
            db.session.query(db.func.sum(Payment.amount))
            .filter(Payment.status == "completed")
            .scalar()
            or 0
        )

        pending_payments = Payment.query.filter_by(status="pending").count()
        failed_payments = Payment.query.filter_by(status="failed").count()

        checked_in_count = Registration.query.filter_by(checked_in=True).count()

        assigned_booths = ExhibitorRegistration.query.filter(
            ExhibitorRegistration.booth_number.isnot(None)
        ).count()
        unassigned_booths = ExhibitorRegistration.query.filter(
            ExhibitorRegistration.booth_number.is_(None)
        ).count()

        return jsonify(
            {
                "success": True,
                "stats": {
                    "total_registrations": total_registrations,
                    "total_attendees": total_attendees,
                    "total_exhibitors": total_exhibitors,
                    "confirmed_registrations": confirmed_registrations,
                    "pending_registrations": pending_registrations,
                    "total_revenue": float(total_revenue),
                    "pending_payments": pending_payments,
                    "failed_payments": failed_payments,
                    "checked_in_count": checked_in_count,
                    "assigned_booths": assigned_booths,
                    "unassigned_booths": unassigned_booths,
                },
            }
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch statistics"}), 500


@api_bp.route("/dashboard/revenue-chart")
@api_admin_required
def revenue_chart_data():
    """Get revenue data for charts (last 30 days)"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # Revenue by day
        daily_revenue = (
            db.session.query(
                db.func.date(Payment.created_at).label("date"),
                db.func.sum(Payment.amount).label("revenue"),
            )
            .filter(
                Payment.status == "completed",
                Payment.created_at >= start_date,
                Payment.created_at <= end_date,
            )
            .group_by(db.func.date(Payment.created_at))
            .order_by(db.func.date(Payment.created_at))
            .all()
        )

        chart_data = [
            {"date": str(record.date), "revenue": float(record.revenue)}
            for record in daily_revenue
        ]

        return jsonify({"success": True, "data": chart_data})
    except Exception as e:
        logger.error(f"Error fetching revenue chart data: {str(e)}")
        return (
            jsonify({"success": False, "error": "Failed to fetch revenue data"}),
            500,
        )


# ============================================================================
# REGISTRATION API
# ============================================================================


@api_bp.route("/registrations/<int:id>")
@api_admin_required
def get_registration(id):
    """Get detailed registration information"""
    try:
        registration = Registration.query.get_or_404(id)

        data = {
            "id": registration.id,
            "registration_type": registration.registration_type,
            "name": registration.name,
            "email": registration.email,
            "phone": registration.phone,
            "organization": registration.organization,
            "status": registration.status.value,
            "checked_in": registration.checked_in,
            "checked_in_at": (
                registration.checked_in_at.isoformat()
                if registration.checked_in_at
                else None
            ),
            "created_at": registration.created_at.isoformat(),
        }

        # Add type-specific data
        if isinstance(registration, AttendeeRegistration):
            data.update(
                {
                    "ticket_type": registration.ticket_type.value,
                    "dietary_requirements": registration.dietary_requirements,
                }
            )
        elif isinstance(registration, ExhibitorRegistration):
            data.update(
                {
                    "package": registration.package.value,
                    "booth_number": registration.booth_number,
                    "company_description": registration.company_description,
                }
            )

        # Add payment information
        data["payments"] = [
            {
                "id": payment.id,
                "amount": float(payment.amount),
                "status": payment.status,
                "payment_method": payment.payment_method,
                "created_at": payment.created_at.isoformat(),
            }
            for payment in registration.payments
        ]

        return jsonify({"success": True, "registration": data})
    except Exception as e:
        logger.error(f"Error fetching registration {id}: {str(e)}")
        return (
            jsonify({"success": False, "error": "Failed to fetch registration"}),
            500,
        )


@api_bp.route("/registrations/search")
@api_admin_required
def search_registrations():
    """Search registrations by name, email, or phone"""
    try:
        query = request.args.get("q", "").strip()
        registration_type = request.args.get("type")  # attendee or exhibitor
        limit = min(int(request.args.get("limit", 20)), 100)

        if not query or len(query) < 2:
            return jsonify({"success": True, "results": []})

        # Build search query
        search_query = Registration.query

        if registration_type == "attendee":
            search_query = AttendeeRegistration.query
        elif registration_type == "exhibitor":
            search_query = ExhibitorRegistration.query

        results = (
            search_query.filter(
                db.or_(
                    Registration.name.ilike(f"%{query}%"),
                    Registration.email.ilike(f"%{query}%"),
                    Registration.phone.ilike(f"%{query}%"),
                )
            )
            .order_by(Registration.created_at.desc())
            .limit(limit)
            .all()
        )

        data = [
            {
                "id": reg.id,
                "name": reg.name,
                "email": reg.email,
                "phone": reg.phone,
                "type": reg.registration_type,
                "status": reg.status.value,
                "checked_in": reg.checked_in,
            }
            for reg in results
        ]

        return jsonify({"success": True, "results": data})
    except Exception as e:
        logger.error(f"Error searching registrations: {str(e)}")
        return (
            jsonify({"success": False, "error": "Failed to search registrations"}),
            500,
        )


@api_bp.route("/registrations/<int:id>/checkin", methods=["POST"])
@api_admin_required
def api_checkin(id):
    """Quick check-in via API"""
    try:
        registration = Registration.query.get_or_404(id)

        if registration.checked_in:
            return jsonify({"success": False, "error": "Already checked in"}), 400

        registration.check_in(checked_in_by=current_user.name)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"{registration.name} checked in successfully",
                "checked_in_at": registration.checked_in_at.isoformat(),
            }
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error checking in registration {id}: {str(e)}")
        return jsonify({"success": False, "error": "Check-in failed"}), 500


@api_bp.route("/registrations/<int:id>/cancel", methods=["POST"])
@api_admin_required
def api_cancel_registration(id):
    """Cancel registration via API"""
    try:
        registration = Registration.query.get_or_404(id)

        if registration.status == RegistrationStatus.CANCELLED:
            return jsonify({"success": False, "error": "Already cancelled"}), 400

        registration.status = RegistrationStatus.CANCELLED
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Registration for {registration.name} cancelled",
            }
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling registration {id}: {str(e)}")
        return jsonify({"success": False, "error": "Cancellation failed"}), 500


# ============================================================================
# PAYMENT API
# ============================================================================


@api_bp.route("/payments/<int:id>")
@api_admin_required
def get_payment(id):
    """Get payment details"""
    try:
        payment = Payment.query.get_or_404(id)

        data = {
            "id": payment.id,
            "amount": float(payment.amount),
            "status": payment.status,
            "payment_method": payment.payment_method,
            "transaction_id": payment.transaction_id,
            "reference_number": payment.reference_number,
            "created_at": payment.created_at.isoformat(),
            "verified_at": payment.verified_at.isoformat()
            if payment.verified_at
            else None,
            "verified_by": payment.verified_by,
            "registration": {
                "id": payment.registration.id,
                "name": payment.registration.name,
                "email": payment.registration.email,
            },
        }

        return jsonify({"success": True, "payment": data})
    except Exception as e:
        logger.error(f"Error fetching payment {id}: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch payment"}), 500


@api_bp.route("/payments/<int:id>/verify", methods=["POST"])
@api_admin_required
def api_verify_payment(id):
    """Quick payment verification via API"""
    try:
        payment = Payment.query.get_or_404(id)
        data = request.get_json()

        if not data or "transaction_id" not in data:
            return jsonify({"success": False, "error": "Transaction ID required"}), 400

        transaction_id = data["transaction_id"]
        notes = data.get("notes", "")

        # Mark payment as completed
        payment.mark_as_completed(transaction_id=transaction_id)
        payment.verified_by = current_user.name
        payment.verified_at = datetime.now()

        if notes:
            payment.payment_notes = notes

        # Update registration status
        registration = payment.registration
        if registration.is_fully_paid():
            registration.status = RegistrationStatus.CONFIRMED
            registration.confirmed_at = datetime.now()

        db.session.commit()
        logger.info(f"Payment {id} verified by {current_user.name}")

        return jsonify(
            {
                "success": True,
                "message": "Payment verified successfully",
                "payment_status": payment.status,
                "registration_status": registration.status.value,
            }
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error verifying payment {id}: {str(e)}")
        return jsonify({"success": False, "error": "Verification failed"}), 500


# ============================================================================
# PROMO CODE API
# ============================================================================


@api_bp.route("/promo-codes/validate")
@login_required
def validate_promo_code():
    """Validate promo code (public API for registration forms)"""
    try:
        code = request.args.get("code", "").strip().upper()
        registration_type = request.args.get("type")  # attendee or exhibitor

        if not code:
            return jsonify({"valid": False, "error": "Code required"}), 400

        promo_code = PromoCode.query.filter_by(code=code).first()

        if not promo_code:
            return jsonify({"valid": False, "error": "Invalid promo code"})

        # Check if active
        if not promo_code.is_active:
            return jsonify(
                {"valid": False, "error": "This promo code is no longer active"}
            )

        # Check expiry
        if promo_code.expires_at and promo_code.expires_at < datetime.now():
            return jsonify({"valid": False, "error": "This promo code has expired"})

        # Check usage limit
        if promo_code.usage_limit and promo_code.times_used >= promo_code.usage_limit:
            return jsonify(
                {"valid": False, "error": "This promo code has reached its usage limit"}
            )

        # Check applicable registration type
        if registration_type and promo_code.applicable_to != "both":
            if promo_code.applicable_to != registration_type:
                return jsonify(
                    {
                        "valid": False,
                        "error": f"This code is only valid for {promo_code.applicable_to} registrations",
                    }
                )

        # Return discount details
        return jsonify(
            {
                "valid": True,
                "code": promo_code.code,
                "discount_type": promo_code.discount_type,
                "discount_value": float(promo_code.discount_value),
                "description": promo_code.description,
            }
        )
    except Exception as e:
        logger.error(f"Error validating promo code: {str(e)}")
        return jsonify({"valid": False, "error": "Validation failed"}), 500


@api_bp.route("/promo-codes/<int:id>/toggle", methods=["POST"])
@api_admin_required
def toggle_promo_code(id):
    """Toggle promo code active status"""
    try:
        promo_code = PromoCode.query.get_or_404(id)
        promo_code.is_active = not promo_code.is_active
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "is_active": promo_code.is_active,
                "message": f"Promo code {'activated' if promo_code.is_active else 'deactivated'}",
            }
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling promo code {id}: {str(e)}")
        return jsonify({"success": False, "error": "Toggle failed"}), 500


# ============================================================================
# EXHIBITOR API
# ============================================================================


@api_bp.route("/exhibitors/<int:id>/assign-booth", methods=["POST"])
@api_admin_required
def api_assign_booth(id):
    """Assign booth number via API"""
    try:
        exhibitor = ExhibitorRegistration.query.get_or_404(id)
        data = request.get_json()

        if not data or "booth_number" not in data:
            return jsonify({"success": False, "error": "Booth number required"}), 400

        booth_number = data["booth_number"].strip()

        # Check if booth already assigned to someone else
        existing = ExhibitorRegistration.query.filter(
            ExhibitorRegistration.booth_number == booth_number,
            ExhibitorRegistration.id != id,
        ).first()

        if existing:
            return jsonify(
                {
                    "success": False,
                    "error": f"Booth {booth_number} already assigned to {existing.name}",
                }
            ), 400

        exhibitor.booth_number = booth_number
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Booth {booth_number} assigned to {exhibitor.name}",
            }
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error assigning booth to exhibitor {id}: {str(e)}")
        return jsonify({"success": False, "error": "Booth assignment failed"}), 500


# ============================================================================
# BADGE API
# ============================================================================


@api_bp.route("/badges/<int:id>/generate", methods=["POST"])
@api_admin_required
def api_generate_badge(id):
    """Generate badge for single registration"""
    try:
        registration = Registration.query.get_or_404(id)

        success = BadgeService.generate_qr_code(registration)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Badge generated for {registration.name}",
                    "qr_code_filename": registration.qr_code_filename,
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to generate badge"}), 500
    except Exception as e:
        logger.error(f"Error generating badge for registration {id}: {str(e)}")
        return jsonify({"success": False, "error": "Badge generation failed"}), 500


# ============================================================================
# EXCHANGE RATE API
# ============================================================================


@api_bp.route("/exchange-rates/current")
def get_current_exchange_rate():
    """Get current exchange rate (public API)"""
    try:
        rate = ExchangeRate.get_current_rate()

        if rate:
            return jsonify(
                {
                    "success": True,
                    "rate": float(rate.rate),
                    "usd_to_tzs": float(rate.rate),
                    "effective_from": rate.effective_from.isoformat(),
                    "created_by": rate.created_by,
                }
            )
        else:
            return jsonify(
                {"success": False, "error": "No exchange rate available"}
            ), 404
    except Exception as e:
        logger.error(f"Error fetching exchange rate: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch rate"}), 500


@api_bp.route("/exchange-rates/<int:id>/activate", methods=["POST"])
@api_admin_only
def activate_exchange_rate(id):
    """Activate an exchange rate"""
    try:
        rate = ExchangeRate.query.get_or_404(id)

        # Deactivate all other rates
        ExchangeRate.query.update({ExchangeRate.is_active: False})

        # Activate this rate
        rate.is_active = True
        db.session.commit()

        return jsonify(
            {"success": True, "message": f"Exchange rate {rate.rate} activated"}
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error activating exchange rate {id}: {str(e)}")
        return jsonify({"success": False, "error": "Activation failed"}), 500


# ============================================================================
# USER API
# ============================================================================


@api_bp.route("/users/<int:id>/toggle-status", methods=["POST"])
@api_admin_only
def toggle_user_status(id):
    """Toggle user active status"""
    try:
        user = User.query.get_or_404(id)

        # Prevent disabling yourself
        if user.id == current_user.id:
            return jsonify(
                {"success": False, "error": "Cannot deactivate your own account"}
            ), 400

        user.is_active = not user.is_active
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "is_active": user.is_active,
                "message": f"User {'activated' if user.is_active else 'deactivated'}",
            }
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling user status {id}: {str(e)}")
        return jsonify({"success": False, "error": "Toggle failed"}), 500


# ============================================================================
# STATISTICS & REPORTS API
# ============================================================================


@api_bp.route("/reports/registration-summary")
@api_admin_required
def registration_summary():
    """Get registration summary statistics"""
    try:
        # By status
        by_status = (
            db.session.query(Registration.status, db.func.count(Registration.id))
            .group_by(Registration.status)
            .all()
        )

        # By type
        by_type = (
            db.session.query(
                Registration.registration_type, db.func.count(Registration.id)
            )
            .group_by(Registration.registration_type)
            .all()
        )

        # Attendee ticket types
        by_ticket = (
            db.session.query(
                AttendeeRegistration.ticket_type, db.func.count(AttendeeRegistration.id)
            )
            .group_by(AttendeeRegistration.ticket_type)
            .all()
        )

        # Exhibitor packages
        by_package = (
            db.session.query(
                ExhibitorRegistration.package, db.func.count(ExhibitorRegistration.id)
            )
            .group_by(ExhibitorRegistration.package)
            .all()
        )

        return jsonify(
            {
                "success": True,
                "summary": {
                    "by_status": {status.value: count for status, count in by_status},
                    "by_type": {reg_type: count for reg_type, count in by_type},
                    "by_ticket_type": {
                        ticket.value: count for ticket, count in by_ticket
                    },
                    "by_package": {
                        package.value: count for package, count in by_package
                    },
                },
            }
        )
    except Exception as e:
        logger.error(f"Error fetching registration summary: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch summary"}), 500


@api_bp.route("/reports/revenue-summary")
@api_admin_required
def revenue_summary():
    """Get revenue summary statistics"""
    try:
        # Total revenue
        total_revenue = (
            db.session.query(db.func.sum(Payment.amount))
            .filter(Payment.status == "completed")
            .scalar()
            or 0
        )

        # By payment method
        by_method = (
            db.session.query(Payment.payment_method, db.func.sum(Payment.amount))
            .filter(Payment.status == "completed")
            .group_by(Payment.payment_method)
            .all()
        )

        # By registration type
        by_type = (
            db.session.query(
                Registration.registration_type, db.func.sum(Payment.amount)
            )
            .join(Payment.registration)
            .filter(Payment.status == "completed")
            .group_by(Registration.registration_type)
            .all()
        )

        # Pending revenue
        pending_revenue = (
            db.session.query(db.func.sum(Payment.amount))
            .filter(Payment.status == "pending")
            .scalar()
            or 0
        )

        return jsonify(
            {
                "success": True,
                "summary": {
                    "total_revenue": float(total_revenue),
                    "pending_revenue": float(pending_revenue),
                    "by_payment_method": {
                        method: float(amount) for method, amount in by_method
                    },
                    "by_registration_type": {
                        reg_type: float(amount) for reg_type, amount in by_type
                    },
                },
            }
        )
    except Exception as e:
        logger.error(f"Error fetching revenue summary: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch summary"}), 500


# ============================================================================
# EMAIL API
# ============================================================================


@api_bp.route("/emails/<int:id>")
@api_admin_required
def get_email_log(id):
    """Get email log details"""
    try:
        email_log = EmailLog.query.get_or_404(id)

        data = {
            "id": email_log.id,
            "recipient_email": email_log.recipient_email,
            "subject": email_log.subject,
            "body": email_log.body,
            "sent_at": email_log.sent_at.isoformat(),
            "sent_by": email_log.sent_by,
            "registration": {
                "id": email_log.registration.id,
                "name": email_log.registration.name,
                "email": email_log.registration.email,
            }
            if email_log.registration
            else None,
        }

        return jsonify({"success": True, "email": data})
    except Exception as e:
        logger.error(f"Error fetching email log {id}: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch email log"}), 500


# ============================================================================
# HEALTH CHECK
# ============================================================================


@api_bp.route("/health")
def health_check():
    """API health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})
