"""
Updated registration routes for BEEASY2025
Single-page forms with AJAX validation
"""

import logging
from decimal import Decimal

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.extensions import db
from app.forms import AttendeeRegistrationForm, ExhibitorRegistrationForm
from app.models import (
    AttendeeTicketType,
    ExhibitorPackage,
    ExhibitorPackagePrice,
    PromoCode,
    Registration,
    RegistrationStatus,
    TicketPrice,
)
from app.services.registration_service import RegistrationService

logger = logging.getLogger(__name__)

register_bp = Blueprint("register", __name__)


# ============================================
# LANDING / SELECTION
# ============================================


@register_bp.route("/attendee")
def attendee_index():
    """Attendee ticket selection landing page"""
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

    tickets = TicketPrice.query.filter_by(is_active=True).all()

    # Pre-select ticket if passed via query parameter
    selected_ticket_type = request.args.get("ticket_type")
    selected_ticket = None

    if selected_ticket_type and request.method == "GET":
        form.ticket_type.data = selected_ticket_type
        # Get the actual ticket object for sidebar display
        try:
            ticket_enum = AttendeeTicketType(selected_ticket_type)
            selected_ticket = TicketPrice.query.filter_by(
                ticket_type=ticket_enum, is_active=True
            ).first()
        except (ValueError, AttributeError):
            logger.warning(f"Invalid ticket type: {selected_ticket_type}")

    if form.validate_on_submit():
        # Process phone data from enhanced or fallback inputs
        country_code, phone_number = form.process_phone_data()

        # Update form data with processed phone values
        form_data = form.data.copy()
        form_data["phone_country_code"] = country_code
        form_data["phone_number"] = phone_number

        success, message, attendee = RegistrationService.register_attendee(form_data)

        if success:
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

    packages = ExhibitorPackagePrice.query.filter_by(is_active=True).all()

    # Pre-select package if passed via query parameter
    selected_package_type = request.args.get("package_type")
    selected_package = None

    if selected_package_type and request.method == "GET":
        form.package_type.data = selected_package_type
        # Get the actual package object for sidebar display
        try:
            package_enum = ExhibitorPackage(selected_package_type)
            selected_package = ExhibitorPackagePrice.query.filter_by(
                package_type=package_enum, is_active=True
            ).first()
        except (ValueError, AttributeError):
            logger.warning(f"Invalid package type: {selected_package_type}")

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
        not Registration.is_deleted,
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

    # Check applicability
    if registration_type == "attendee" and not promo.applicable_to_attendees:
        return jsonify(
            {"valid": False, "message": "This code is not valid for attendees"}
        )

    if registration_type == "exhibitor" and not promo.applicable_to_exhibitors:
        return jsonify(
            {"valid": False, "message": "This code is not valid for exhibitors"}
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
    subtotal_after_discount = subtotal - discount

    # Calculate tax
    tax_rate = Decimal("0.16")
    tax = subtotal_after_discount * tax_rate

    total = subtotal_after_discount + tax

    return jsonify(
        {
            "base_price": float(base_price),
            "addons_total": float(addons_total),
            "subtotal": float(subtotal),
            "discount": float(discount),
            "subtotal_after_discount": float(subtotal_after_discount),
            "tax": float(tax),
            "tax_rate": float(tax_rate),
            "total": float(total),
            "currency": "USD",
        }
    )
