"""
Updated registration routes for BEEASY2025
Single-page forms with AJAX validation
"""

import logging
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.extensions import db
from app.forms import AttendeeRegistrationForm, ExhibitorRegistrationForm
from app.models import (
    AttendeeRegistration,
    AttendeeTicketType,
    ExhibitorPackage,
    ExhibitorPackagePrice,
    PaymentStatus,
    PromoCode,
    Registration,
    RegistrationStatus,
    TicketPrice,
)
from app.services.registration_service import RegistrationService
from app.utils.enhanced_email import EnhancedEmailService

logger = logging.getLogger(__name__)

register_bp = Blueprint("register", __name__)


# ============================================
# LANDING / SELECTION
# ============================================


@register_bp.route("/attendee")
def attendee_index():
    """Attendee ticket selection landing page"""
    if not current_app.config.get("REGISTRATION_OPEN", False):
        return render_template(
            "register/registration_closed.html", registration_type="attendee"
        )

    tickets = (
        TicketPrice.query.filter_by(is_active=True).order_by(TicketPrice.price).all()
    )
    return render_template("register/attendee_index.html", tickets=tickets)


# ============================================
# ATTENDEE REGISTRATION
# ============================================


@register_bp.route("/attendee/form", methods=["GET", "POST"])
def register_attendee_form():
    """Single-page attendee registration form with pre-selected ticket"""
    form = AttendeeRegistrationForm()

    # Dynamically populate ticket choices from database
    form.populate_ticket_choices()

    # Populate country choices
    form.populate_country_choices()

    tickets = TicketPrice.query.filter_by(is_active=True).all()

    # Pre-select ticket if passed via query parameter
    selected_ticket_type = request.args.get("ticket_type")
    selected_ticket = None

    if selected_ticket_type and request.method == "GET":
        form.ticket_type.data = selected_ticket_type

    # Resolve selected_ticket for sidebar display on both GET and POST.
    # On GET it comes from the query param; on POST it comes from the submitted form data.
    ticket_type_value = form.ticket_type.data or selected_ticket_type
    if ticket_type_value:
        try:
            ticket_enum = AttendeeTicketType(ticket_type_value)
            selected_ticket = TicketPrice.query.filter_by(
                ticket_type=ticket_enum, is_active=True
            ).first()
        except (ValueError, AttributeError):
            logger.warning(f"Invalid ticket type: {ticket_type_value}")

    # Redirect to selection page if no valid ticket could be resolved
    if not selected_ticket:
        flash("Please select a ticket type first.", "warning")
        return redirect(url_for("register.attendee_index"))

    if form.validate_on_submit():
        # Process phone data from enhanced or fallback inputs
        country_code, phone_number = form.process_phone_data()

        # Update form data with processed phone values
        form_data = form.data.copy()
        form_data["phone_country_code"] = country_code
        form_data["phone_number"] = phone_number

        success, message, attendee = RegistrationService.register_attendee(form_data)

        if success:
            # Grant verified access so user can change ticket without OTP
            session["verified_ref"] = attendee.reference_number
            session["verified_ref_at"] = datetime.now().isoformat()
            flash(message, "success")
            return redirect(
                url_for("register.confirmation", ref=attendee.reference_number)
            )
        else:
            flash(message, "error")

    return render_template(
        "register/attendee.html",
        form=form,
        tickets=tickets,
        selected_ticket=selected_ticket,
    )


# ============================================
# EXHIBITOR REGISTRATION
# ============================================


@register_bp.route("/exhibitor")
def exhibitor_index():
    """Exhibitor package selection landing page"""
    if not current_app.config.get("REGISTRATION_OPEN", False):
        return render_template(
            "register/registration_closed.html", registration_type="exhibitor"
        )

    packages = (
        ExhibitorPackagePrice.query.filter_by(is_active=True)
        .order_by(ExhibitorPackagePrice.price)
        .all()
    )

    # Check if floor plan is available (you can implement this logic)
    floor_plan_available = False  # Set to True when you upload floor plan
    floor_plan_url = None  # Set to actual URL when available

    return render_template(
        "register/exhibitor_index.html",
        packages=packages,
        floor_plan_available=floor_plan_available,
        floor_plan_url=floor_plan_url,
    )


@register_bp.route("/exhibitor/form", methods=["GET", "POST"])
def register_exhibitor_form():
    """Single-page exhibitor registration form with pre-selected package"""
    form = ExhibitorRegistrationForm()

    # Dynamically populate package choices from database
    form.populate_package_choices()

    # Populate country choices
    form.populate_country_choices()

    packages = ExhibitorPackagePrice.query.filter_by(is_active=True).all()

    # Pre-select package if passed via query parameter
    selected_package_type = request.args.get("package_type")
    selected_package = None

    if selected_package_type and request.method == "GET":
        form.package_type.data = selected_package_type

    # Resolve selected_package for sidebar display on both GET and POST.
    # On GET it comes from the query param; on POST it comes from the submitted form data.
    package_type_value = form.package_type.data or selected_package_type
    if package_type_value:
        try:
            package_enum = ExhibitorPackage(package_type_value)
            selected_package = ExhibitorPackagePrice.query.filter_by(
                package_type=package_enum, is_active=True
            ).first()
        except (ValueError, AttributeError):
            logger.warning(f"Invalid package type: {package_type_value}")

    # Redirect to selection page if no valid package could be resolved
    if not selected_package:
        flash("Please select a package first.", "warning")
        return redirect(url_for("register.exhibitor_index"))

    if form.validate_on_submit():
        # Process phone data from enhanced or fallback inputs
        country_code, phone_number = form.process_phone_data()

        # Update form data with processed phone values
        form_data = form.data.copy()
        form_data["phone_country_code"] = country_code
        form_data["phone_number"] = phone_number

        success, message, exhibitor = RegistrationService.register_exhibitor(form_data)

        if success:
            flash(message, "success")
            return redirect(
                url_for("register.confirmation", ref=exhibitor.reference_number)
            )
        else:
            flash(message, "error")

    return render_template(
        "register/exhibitor.html",
        form=form,
        packages=packages,
        selected_package=selected_package,
    )


# ============================================
# CONFIRMATION PAGE
# ============================================


@register_bp.route("/confirmation/<ref>")
def confirmation(ref):
    """
    Registration confirmation page
    Shows registration summary and checkout option
    """
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    # Get payment info
    payment = registration.payments[0] if registration.payments else None
    balance_due = registration.get_balance_due()

    return render_template(
        "register/confirmation.html",
        registration=registration,
        payment=payment,
        balance_due=balance_due,
    )


# ============================================
# RESUME REGISTRATION (Email OTP)
# ============================================


def _generate_otp():
    """Generate a 6-digit numeric OTP"""
    return "".join(secrets.choice("0123456789") for _ in range(6))


@register_bp.route("/resume", methods=["GET", "POST"])
def resume_registration():
    """Enter email to receive OTP and resume a pending registration"""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            flash("Please enter your email address.", "error")
            return render_template("register/resume_email.html")

        # Find pending registration
        registration = Registration.query.filter(
            db.func.lower(Registration.email) == email,
            Registration.is_deleted == False,
            Registration.status.in_([
                RegistrationStatus.PENDING,
                RegistrationStatus.CONFIRMED,
            ]),
        ).order_by(Registration.created_at.desc()).first()

        if not registration:
            flash("No registration found for this email address.", "error")
            return render_template("register/resume_email.html")

        # Generate OTP
        otp = _generate_otp()
        registration.resume_otp = otp
        registration.resume_otp_expires = datetime.now() + timedelta(minutes=10)
        registration.resume_otp_attempts = 0
        db.session.commit()

        # Send OTP email
        try:
            email_service = EnhancedEmailService(current_app)

            ticket_name = ""
            if hasattr(registration, "ticket_price") and registration.ticket_price:
                ticket_name = registration.ticket_price.name
            elif hasattr(registration, "package_price") and registration.package_price:
                ticket_name = registration.package_price.name

            email_service.send_notification(
                recipient=registration.email,
                template="resume_otp",
                subject="Your Verification Code - Pollination Africa Summit",
                template_context={
                    "first_name": registration.first_name,
                    "otp_code": otp,
                    "reference_number": registration.reference_number,
                    "ticket_name": ticket_name,
                    "email": registration.email,
                },
                priority=0,  # High priority
            )
        except Exception as e:
            logger.error(f"Failed to send OTP email: {str(e)}")

        # Store email in session for the verify step
        session["resume_email"] = email
        flash("A verification code has been sent to your email.", "success")
        return redirect(url_for("register.verify_otp"))

    return render_template("register/resume_email.html")


@register_bp.route("/resume/verify", methods=["GET", "POST"])
def verify_otp():
    """Verify OTP and redirect to confirmation page"""
    email = session.get("resume_email")
    if not email:
        flash("Please enter your email first.", "warning")
        return redirect(url_for("register.resume_registration"))

    if request.method == "POST":
        otp_input = request.form.get("otp", "").strip()

        if not otp_input or len(otp_input) != 6:
            flash("Please enter the 6-digit code.", "error")
            return render_template("register/resume_verify.html", email=email)

        registration = Registration.query.filter(
            db.func.lower(Registration.email) == email.lower(),
            Registration.is_deleted == False,
            Registration.resume_otp.isnot(None),
        ).order_by(Registration.created_at.desc()).first()

        if not registration:
            flash("No pending verification found. Please try again.", "error")
            return redirect(url_for("register.resume_registration"))

        # Check attempts
        if registration.resume_otp_attempts >= 5:
            registration.resume_otp = None
            registration.resume_otp_expires = None
            db.session.commit()
            flash("Too many attempts. Please request a new code.", "error")
            return redirect(url_for("register.resume_registration"))

        # Check expiry
        if registration.resume_otp_expires and datetime.now() > registration.resume_otp_expires:
            registration.resume_otp = None
            db.session.commit()
            flash("Code has expired. Please request a new one.", "error")
            return redirect(url_for("register.resume_registration"))

        # Verify OTP
        registration.resume_otp_attempts = (registration.resume_otp_attempts or 0) + 1

        if otp_input != registration.resume_otp:
            db.session.commit()
            remaining = 5 - registration.resume_otp_attempts
            flash(f"Invalid code. {remaining} attempts remaining.", "error")
            return render_template("register/resume_verify.html", email=email)

        # Success — clear OTP and mark session as verified
        registration.resume_otp = None
        registration.resume_otp_expires = None
        registration.resume_otp_attempts = 0
        db.session.commit()

        session["verified_ref"] = registration.reference_number
        session["verified_ref_at"] = datetime.now().isoformat()
        session.pop("resume_email", None)

        return redirect(url_for("register.confirmation", ref=registration.reference_number))

    return render_template("register/resume_verify.html", email=email)


# ============================================
# CHANGE TICKET TYPE
# ============================================


@register_bp.route("/change-ticket/<ref>", methods=["GET", "POST"])
def change_ticket(ref):
    """Allow user to change ticket type before payment"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    # Security: must have verified via OTP or be the same session
    verified_ref = session.get("verified_ref")
    if verified_ref != ref:
        flash("Please verify your identity to change your ticket.", "warning")
        return redirect(url_for("register.resume_registration"))

    # Check verification hasn't expired (30 min window)
    verified_at = session.get("verified_ref_at")
    if verified_at:
        try:
            verified_time = datetime.fromisoformat(verified_at)
            if datetime.now() - verified_time > timedelta(minutes=30):
                session.pop("verified_ref", None)
                session.pop("verified_ref_at", None)
                flash("Your session has expired. Please verify again.", "warning")
                return redirect(url_for("register.resume_registration"))
        except (ValueError, TypeError):
            pass

    # Only attendees can change tickets
    if not isinstance(registration, AttendeeRegistration):
        flash("Ticket changes are only available for attendee registrations.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    # Only PENDING registrations
    if registration.status != RegistrationStatus.PENDING:
        flash("Ticket can only be changed before payment is completed.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    # Check payment status
    payment = registration.payments[0] if registration.payments else None
    if payment and payment.payment_status not in (PaymentStatus.PENDING, PaymentStatus.FAILED):
        flash("Cannot change ticket after payment has been initiated.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    tickets = TicketPrice.query.filter_by(is_active=True).order_by(TicketPrice.price).all()

    if request.method == "POST":
        new_ticket_type = request.form.get("ticket_type")
        new_group_size = request.form.get("group_size")

        if new_group_size:
            try:
                new_group_size = int(new_group_size)
            except ValueError:
                new_group_size = None

        success, message = RegistrationService.change_ticket(
            registration, new_ticket_type, new_group_size
        )

        if success:
            flash(message, "success")
        else:
            flash(message, "error")

        return redirect(url_for("register.confirmation", ref=ref))

    return render_template(
        "register/change_ticket.html",
        registration=registration,
        tickets=tickets,
        current_ticket=registration.ticket_price,
        payment=payment,
    )


# ============================================
# AJAX ENDPOINTS
# ============================================


@register_bp.route("/api/validate-email", methods=["POST"])
def validate_email():
    """Check email availability"""
    email = request.json.get("email", "").lower()
    registration_type = request.json.get("type", "attendee")

    if not email:
        return jsonify({"valid": False, "message": "Email is required"})

    existing = Registration.query.filter(
        db.func.lower(Registration.email) == email,
        Registration.registration_type == registration_type,
        Registration.is_deleted == False,
    ).first()

    if existing:
        return jsonify(
            {
                "valid": False,
                "message": f"This email is already registered as {registration_type}",
            }
        )

    return jsonify({"valid": True, "message": "Email available"})


@register_bp.route("/api/validate-promo", methods=["POST"])
def validate_promo():
    """Validate promo code"""
    code = request.json.get("code", "").upper()
    email = request.json.get("email", "").lower()
    registration_type = request.json.get("type", "attendee")

    if not code:
        return jsonify({"valid": False, "message": "Promo code is required"})

    promo = PromoCode.query.filter_by(code=code).first()

    if not promo:
        return jsonify({"valid": False, "message": "Invalid promo code"})

    if not promo.is_valid():
        return jsonify({"valid": False, "message": "Promo code is expired or inactive"})

    if email and not promo.is_valid_for_user(email):
        return jsonify(
            {"valid": False, "message": "You have already used this promo code"}
        )

    # Check applicability by registration type
    if registration_type == "attendee" and not promo.applicable_to_attendees:
        return jsonify(
            {"valid": False, "message": "This code is not valid for attendees"}
        )

    if registration_type == "exhibitor" and not promo.applicable_to_exhibitors:
        return jsonify(
            {"valid": False, "message": "This code is not valid for exhibitors"}
        )

    # Check applicability by specific ticket type or package
    ticket_type = request.json.get("ticket_type", "")
    package_type = request.json.get("package_type", "")

    if ticket_type and promo.applicable_ticket_types:
        if ticket_type not in promo.applicable_ticket_types:
            return jsonify(
                {"valid": False, "message": "This code is not valid for your ticket type"}
            )

    if package_type and promo.applicable_packages:
        if package_type not in promo.applicable_packages:
            return jsonify(
                {"valid": False, "message": "This code is not valid for your package"}
            )

    # Calculate discount preview
    amount = Decimal(request.json.get("amount", "0"))
    discount = float(promo.calculate_discount(amount))

    return jsonify(
        {
            "valid": True,
            "message": f"Valid! {promo.description}",
            "discount": discount,
            "discount_type": promo.discount_type,
            "discount_value": float(promo.discount_value),
        }
    )


@register_bp.route("/api/ticket-info/<ticket_type>")
def ticket_info(ticket_type):
    """Get ticket pricing info"""
    try:
        ticket_enum = AttendeeTicketType[ticket_type.upper()]
    except KeyError:
        return jsonify({"error": "Invalid ticket type"}), 400

    ticket = TicketPrice.query.filter_by(ticket_type=ticket_enum).first()

    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    return jsonify(
        {
            "name": ticket.name,
            "price": float(ticket.get_current_price()),
            "currency": ticket.currency,
            "available": ticket.is_available(),
            "max_quantity": ticket.max_quantity,
            "current_quantity": ticket.current_quantity,
            "includes_lunch": ticket.includes_lunch,
            "includes_materials": ticket.includes_materials,
            "includes_certificate": ticket.includes_certificate,
        }
    )


@register_bp.route("/api/package-info/<package_type>")
def package_info(package_type):
    """Get package pricing info"""
    try:
        package_enum = ExhibitorPackage[package_type.upper()]
    except KeyError:
        return jsonify({"error": "Invalid package type"}), 400

    package = ExhibitorPackagePrice.query.filter_by(package_type=package_enum).first()

    if not package:
        return jsonify({"error": "Package not found"}), 404

    return jsonify(
        {
            "name": package.name,
            "price": float(package.price),
            "currency": package.currency,
            "available": package.is_available(),
            "booth_size": package.booth_size,
            "included_passes": package.included_passes,
            "features": package.features,
            "includes_electricity": package.includes_electricity,
            "includes_wifi": package.includes_wifi,
            "includes_speaking_slot": package.includes_speaking_slot,
        }
    )


@register_bp.route("/api/payment-status/<ref>")
def payment_status(ref):
    """
    Check payment status (for polling after payment)
    Used by frontend to detect when payment completes
    """
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first()

    if not registration:
        return jsonify({"error": "Registration not found"}), 404

    payment = registration.payments[0] if registration.payments else None

    return jsonify(
        {
            "status": registration.status.value,
            "is_confirmed": registration.status == RegistrationStatus.CONFIRMED,
            "balance_due": float(registration.get_balance_due()),
            "has_badge": registration.qr_code_image_url is not None,
            "badge_url": registration.qr_code_image_url,
            "payment_status": payment.payment_status.value if payment else None,
            "confirmed_at": registration.confirmed_at.isoformat()
            if registration.confirmed_at
            else None,
        }
    )


@register_bp.route("/api/calculate-total", methods=["POST"])
def calculate_total():
    """Calculate total cost with add-ons and upgrades"""
    data = request.json

    base_price = Decimal(str(data.get("base_price", 0)))

    # Add booth upgrades
    if data.get("corner_booth"):
        base_price += Decimal("200.00")
    if data.get("entrance_booth"):
        base_price += Decimal("150.00")

    # Add-ons
    addons_total = Decimal("0.00")
    for addon in data.get("addons", []):
        addons_total += Decimal(str(addon.get("price", 0))) * addon.get("quantity", 1)

    subtotal = base_price + addons_total

    # Apply promo discount
    discount = Decimal(str(data.get("discount", 0)))
    total = subtotal - discount

    return jsonify(
        {
            "base_price": float(base_price),
            "addons_total": float(addons_total),
            "subtotal": float(subtotal),
            "discount": float(discount),
            "total": float(total),
            "currency": "USD",
        }
    )
