"""
Admin routes for BEEASY2025
Comprehensive admin panel for managing registrations, payments, tickets, and event operations
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps
from io import BytesIO

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_

from app.extensions import db
from app.forms import (
    AddOnItemForm,
    AdminPromoCodeForm,
    BoothAssignmentForm,
    BulkEmailForm,
    ContactReplyForm,
    EditAttendeeForm,
    EditExhibitorForm,
    ExchangeRateForm,
    ExhibitorPackageForm,
    PaymentVerificationForm,
    RefundForm,
    SendEmailForm,
    TicketPriceForm,
    UserForm,
)
from app.models import (
    AddOnItem,
    AddOnPurchase,
    AttendeeRegistration,
    AttendeeTicketType,
    EmailLog,
    ExchangeRate,
    ExhibitorPackage,
    ExhibitorPackagePrice,
    ExhibitorRegistration,
    Payment,
    PaymentMethod,
    PaymentStatus,
    PromoCode,
    PromoCodeUsage,
    Registration,
    RegistrationStatus,
    TicketPrice,
    User,
    UserRole,
)
from app.services.badge_service import BadgeService
from app.services.registration_service import RegistrationService

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ============================================
# DECORATORS
# ============================================


def admin_required(f):
    """Decorator to require admin or staff role"""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access the admin panel.", "error")
            return redirect(url_for("auth.login", next=request.url))

        if current_user.role not in [
            UserRole.ADMIN,
            UserRole.STAFF,
            UserRole.ORGANIZER,
        ]:
            flash("You do not have permission to access this page.", "error")
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


def admin_only(f):
    """Decorator to require admin role only"""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access the admin panel.", "error")
            return redirect(url_for("auth.login", next=request.url))

        if current_user.role != UserRole.ADMIN:
            flash("Only administrators can access this page.", "error")
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


# ============================================
# 1. DASHBOARD
# ============================================


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """Admin dashboard with overview metrics"""

    # Get key statistics
    total_registrations = Registration.query.filter_by(is_deleted=False).count()
    total_attendees = AttendeeRegistration.query.filter_by(is_deleted=False).count()
    total_exhibitors = ExhibitorRegistration.query.filter_by(is_deleted=False).count()

    confirmed_registrations = Registration.query.filter_by(
        status=RegistrationStatus.CONFIRMED, is_deleted=False
    ).count()

    pending_registrations = Registration.query.filter_by(
        status=RegistrationStatus.PENDING, is_deleted=False
    ).count()

    # Payment statistics
    total_revenue = db.session.query(func.sum(Payment.total_amount)).filter(
        Payment.payment_status == PaymentStatus.COMPLETED
    ).scalar() or Decimal("0.00")

    pending_payments = Payment.query.filter_by(
        payment_status=PaymentStatus.PENDING
    ).count()

    failed_payments = Payment.query.filter_by(
        payment_status=PaymentStatus.FAILED
    ).count()

    # Recent registrations (last 10)
    recent_registrations = (
        Registration.query.filter_by(is_deleted=False)
        .order_by(Registration.created_at.desc())
        .limit(10)
        .all()
    )

    # Checked-in count
    checked_in_count = AttendeeRegistration.query.filter_by(
        checked_in=True, is_deleted=False
    ).count()

    # Booth assignments
    assigned_booths = ExhibitorRegistration.query.filter_by(
        booth_assigned=True, is_deleted=False
    ).count()

    unassigned_booths = ExhibitorRegistration.query.filter_by(
        booth_assigned=False, is_deleted=False, status=RegistrationStatus.CONFIRMED
    ).count()

    stats = {
        "total_registrations": total_registrations,
        "total_attendees": total_attendees,
        "total_exhibitors": total_exhibitors,
        "confirmed_registrations": confirmed_registrations,
        "pending_registrations": pending_registrations,
        "total_revenue": total_revenue,
        "pending_payments": pending_payments,
        "failed_payments": failed_payments,
        "checked_in_count": checked_in_count,
        "assigned_booths": assigned_booths,
        "unassigned_booths": unassigned_booths,
    }

    return render_template(
        "admin/dashboard.html", stats=stats, recent_registrations=recent_registrations
    )


# ============================================
# 2. REGISTRATIONS - ATTENDEES
# ============================================


@admin_bp.route("/registrations/attendees")
@admin_required
def list_attendees():
    """List all attendee registrations with filters"""

    # Get filter parameters
    status_filter = request.args.get("status")
    ticket_type_filter = request.args.get("ticket_type")
    search_query = request.args.get("search", "").strip()
    checked_in_filter = request.args.get("checked_in")
    page = request.args.get("page", 1, type=int)
    per_page = 50

    # Build query
    query = AttendeeRegistration.query.filter_by(is_deleted=False)

    # Apply filters
    if status_filter:
        try:
            status_enum = RegistrationStatus(status_filter)
            query = query.filter_by(status=status_enum)
        except ValueError:
            pass

    if ticket_type_filter:
        try:
            ticket_enum = AttendeeTicketType(ticket_type_filter)
            query = query.filter_by(ticket_type=ticket_enum)
        except ValueError:
            pass

    if checked_in_filter:
        checked_in_value = checked_in_filter.lower() == "true"
        query = query.filter_by(checked_in=checked_in_value)

    if search_query:
        query = query.filter(
            or_(
                AttendeeRegistration.first_name.ilike(f"%{search_query}%"),
                AttendeeRegistration.last_name.ilike(f"%{search_query}%"),
                AttendeeRegistration.email.ilike(f"%{search_query}%"),
                AttendeeRegistration.reference_number.ilike(f"%{search_query}%"),
            )
        )

    # Order by most recent
    query = query.order_by(AttendeeRegistration.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    attendees = pagination.items

    return render_template(
        "admin/registrations/attendees/list.html",
        attendees=attendees,
        pagination=pagination,
        status_filter=status_filter,
        ticket_type_filter=ticket_type_filter,
        checked_in_filter=checked_in_filter,
        search_query=search_query,
    )


@admin_bp.route("/registrations/attendees/<int:id>")
@admin_required
def view_attendee(id):
    """View attendee registration details"""
    attendee = AttendeeRegistration.query.get_or_404(id)

    if attendee.is_deleted:
        flash("This registration has been deleted.", "error")
        return redirect(url_for("admin.list_attendees"))

    # Get payment history
    payments = (
        Payment.query.filter_by(registration_id=id)
        .order_by(Payment.created_at.desc())
        .all()
    )

    # Get email logs
    email_logs = (
        EmailLog.query.filter_by(registration_id=id)
        .order_by(EmailLog.sent_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/registrations/attendees/detail.html",
        attendee=attendee,
        payments=payments,
        email_logs=email_logs,
    )


@admin_bp.route("/registrations/attendees/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_attendee(id):
    """Edit attendee registration"""
    attendee = AttendeeRegistration.query.get_or_404(id)

    if attendee.is_deleted:
        flash("This registration has been deleted.", "error")
        return redirect(url_for("admin.list_attendees"))

    form = EditAttendeeForm(obj=attendee)

    if form.validate_on_submit():
        try:
            # Update fields
            form.populate_obj(attendee)
            attendee.updated_at = datetime.now()

            db.session.commit()

            flash("Attendee registration updated successfully.", "success")
            return redirect(url_for("admin.view_attendee", id=id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating attendee {id}: {str(e)}")
            flash("Error updating attendee registration.", "error")

    return render_template(
        "admin/registrations/attendees/edit.html", attendee=attendee, form=form
    )


@admin_bp.route("/registrations/attendees/<int:id>/cancel", methods=["POST"])
@admin_required
def cancel_attendee(id):
    """Cancel attendee registration"""
    attendee = AttendeeRegistration.query.get_or_404(id)

    if attendee.is_deleted:
        flash("This registration is already deleted.", "error")
        return redirect(url_for("admin.list_attendees"))

    try:
        attendee.status = RegistrationStatus.CANCELLED
        attendee.updated_at = datetime.now()

        # Add admin note
        if not attendee.admin_notes:
            attendee.admin_notes = ""
        attendee.admin_notes += f"\n[{datetime.now()}] Cancelled by {current_user.name}"

        db.session.commit()

        flash("Attendee registration cancelled successfully.", "success")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling attendee {id}: {str(e)}")
        flash("Error cancelling registration.", "error")

    return redirect(url_for("admin.view_attendee", id=id))


@admin_bp.route("/registrations/attendees/<int:id>/check-in", methods=["POST"])
@admin_required
def checkin_attendee(id):
    """Mark attendee as checked in"""
    attendee = AttendeeRegistration.query.get_or_404(id)

    try:
        attendee.check_in(checked_in_by=current_user.name)
        db.session.commit()

        flash("Attendee checked in successfully.", "success")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "message": "Checked in successfully"})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error checking in attendee {id}: {str(e)}")
        flash("Error during check-in.", "error")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": str(e)}), 400

    return redirect(url_for("admin.view_attendee", id=id))


@admin_bp.route("/registrations/attendees/export")
@admin_required
def export_attendees():
    """Export attendees to CSV"""
    import csv
    from io import StringIO

    # Get all attendees (with same filters as list)
    status_filter = request.args.get("status")
    ticket_type_filter = request.args.get("ticket_type")

    query = AttendeeRegistration.query.filter_by(is_deleted=False)

    if status_filter:
        try:
            status_enum = RegistrationStatus(status_filter)
            query = query.filter_by(status=status_enum)
        except ValueError:
            pass

    if ticket_type_filter:
        try:
            ticket_enum = AttendeeTicketType(ticket_type_filter)
            query = query.filter_by(ticket_type=ticket_enum)
        except ValueError:
            pass

    attendees = query.order_by(AttendeeRegistration.created_at.desc()).all()

    # Create CSV
    si = StringIO()
    writer = csv.writer(si)

    # Header
    writer.writerow(
        [
            "Reference Number",
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "Organization",
            "Job Title",
            "Country",
            "City",
            "Ticket Type",
            "Status",
            "Checked In",
            "Created At",
            "Confirmed At",
        ]
    )

    # Data rows
    for attendee in attendees:
        writer.writerow(
            [
                attendee.reference_number,
                attendee.first_name,
                attendee.last_name,
                attendee.email,
                attendee.full_phone or "",
                attendee.organization or "",
                attendee.job_title or "",
                attendee.country or "",
                attendee.city or "",
                attendee.ticket_type.value if attendee.ticket_type else "",
                attendee.status.value,
                "Yes" if attendee.checked_in else "No",
                attendee.created_at.strftime("%Y-%m-%d %H:%M"),
                attendee.confirmed_at.strftime("%Y-%m-%d %H:%M")
                if attendee.confirmed_at
                else "",
            ]
        )

    # Create response
    output = BytesIO()
    output.write(si.getvalue().encode("utf-8"))
    output.seek(0)

    filename = f"attendees_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return send_file(
        output, mimetype="text/csv", as_attachment=True, download_name=filename
    )


# ============================================
# 2. REGISTRATIONS - EXHIBITORS
# ============================================


@admin_bp.route("/registrations/exhibitors")
@admin_required
def list_exhibitors():
    """List all exhibitor registrations with filters"""

    # Get filter parameters
    status_filter = request.args.get("status")
    package_filter = request.args.get("package")
    search_query = request.args.get("search", "").strip()
    booth_assigned_filter = request.args.get("booth_assigned")
    page = request.args.get("page", 1, type=int)
    per_page = 50

    # Build query
    query = ExhibitorRegistration.query.filter_by(is_deleted=False)

    # Apply filters
    if status_filter:
        try:
            status_enum = RegistrationStatus(status_filter)
            query = query.filter_by(status=status_enum)
        except ValueError:
            pass

    if package_filter:
        try:
            package_enum = ExhibitorPackage(package_filter)
            query = query.filter_by(package_type=package_enum)
        except ValueError:
            pass

    if booth_assigned_filter:
        booth_value = booth_assigned_filter.lower() == "true"
        query = query.filter_by(booth_assigned=booth_value)

    if search_query:
        query = query.filter(
            or_(
                ExhibitorRegistration.company_legal_name.ilike(f"%{search_query}%"),
                ExhibitorRegistration.first_name.ilike(f"%{search_query}%"),
                ExhibitorRegistration.last_name.ilike(f"%{search_query}%"),
                ExhibitorRegistration.email.ilike(f"%{search_query}%"),
                ExhibitorRegistration.reference_number.ilike(f"%{search_query}%"),
                ExhibitorRegistration.booth_number.ilike(f"%{search_query}%"),
            )
        )

    # Order by most recent
    query = query.order_by(ExhibitorRegistration.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    exhibitors = pagination.items

    return render_template(
        "admin/registrations/exhibitors/list.html",
        exhibitors=exhibitors,
        pagination=pagination,
        status_filter=status_filter,
        package_filter=package_filter,
        booth_assigned_filter=booth_assigned_filter,
        search_query=search_query,
    )


@admin_bp.route("/registrations/exhibitors/<int:id>")
@admin_required
def view_exhibitor(id):
    """View exhibitor registration details"""
    exhibitor = ExhibitorRegistration.query.get_or_404(id)

    if exhibitor.is_deleted:
        flash("This registration has been deleted.", "error")
        return redirect(url_for("admin.list_exhibitors"))

    # Get payment history
    payments = (
        Payment.query.filter_by(registration_id=id)
        .order_by(Payment.created_at.desc())
        .all()
    )

    # Get email logs
    email_logs = (
        EmailLog.query.filter_by(registration_id=id)
        .order_by(EmailLog.sent_at.desc())
        .limit(10)
        .all()
    )

    # Get add-ons
    addons = AddOnPurchase.query.filter_by(registration_id=id).all()

    return render_template(
        "admin/registrations/exhibitors/detail.html",
        exhibitor=exhibitor,
        payments=payments,
        email_logs=email_logs,
        addons=addons,
    )


@admin_bp.route("/registrations/exhibitors/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_exhibitor(id):
    """Edit exhibitor registration"""
    exhibitor = ExhibitorRegistration.query.get_or_404(id)

    if exhibitor.is_deleted:
        flash("This registration has been deleted.", "error")
        return redirect(url_for("admin.list_exhibitors"))

    form = EditExhibitorForm(obj=exhibitor)

    if form.validate_on_submit():
        try:
            # Update fields
            form.populate_obj(exhibitor)
            exhibitor.updated_at = datetime.now()

            db.session.commit()

            flash("Exhibitor registration updated successfully.", "success")
            return redirect(url_for("admin.view_exhibitor", id=id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating exhibitor {id}: {str(e)}")
            flash("Error updating exhibitor registration.", "error")

    return render_template(
        "admin/registrations/exhibitors/edit.html", exhibitor=exhibitor, form=form
    )


@admin_bp.route("/registrations/exhibitors/<int:id>/assign-booth", methods=["POST"])
@admin_required
def assign_booth(id):
    """Assign booth number to exhibitor"""
    exhibitor = ExhibitorRegistration.query.get_or_404(id)

    form = BoothAssignmentForm()

    if form.validate_on_submit():
        try:
            booth_number = form.booth_number.data.strip().upper()

            # Check if booth number is already assigned
            existing = (
                ExhibitorRegistration.query.filter_by(
                    booth_number=booth_number, booth_assigned=True, is_deleted=False
                )
                .filter(ExhibitorRegistration.id != id)
                .first()
            )

            if existing:
                flash(
                    f"Booth {booth_number} is already assigned to {existing.company_legal_name}.",
                    "error",
                )
                return redirect(url_for("admin.view_exhibitor", id=id))

            # Assign booth
            exhibitor.assign_booth(booth_number, assigned_by=current_user.name)

            # Add note if provided
            if form.notes.data:
                if not exhibitor.admin_notes:
                    exhibitor.admin_notes = ""
                exhibitor.admin_notes += (
                    f"\n[{datetime.now()}] Booth Assignment: {form.notes.data}"
                )

            db.session.commit()

            flash(f"Booth {booth_number} assigned successfully.", "success")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error assigning booth to exhibitor {id}: {str(e)}")
            flash("Error assigning booth.", "error")

    return redirect(url_for("admin.view_exhibitor", id=id))


@admin_bp.route("/registrations/exhibitors/export")
@admin_required
def export_exhibitors():
    """Export exhibitors to CSV"""
    import csv
    from io import StringIO

    # Get all exhibitors (with same filters as list)
    status_filter = request.args.get("status")
    package_filter = request.args.get("package")

    query = ExhibitorRegistration.query.filter_by(is_deleted=False)

    if status_filter:
        try:
            status_enum = RegistrationStatus(status_filter)
            query = query.filter_by(status=status_enum)
        except ValueError:
            pass

    if package_filter:
        try:
            package_enum = ExhibitorPackage(package_filter)
            query = query.filter_by(package_type=package_enum)
        except ValueError:
            pass

    exhibitors = query.order_by(ExhibitorRegistration.created_at.desc()).all()

    # Create CSV
    si = StringIO()
    writer = csv.writer(si)

    # Header
    writer.writerow(
        [
            "Reference Number",
            "Company Name",
            "Contact Name",
            "Email",
            "Phone",
            "Country",
            "Website",
            "Package Type",
            "Booth Number",
            "Booth Assigned",
            "Status",
            "Contract Signed",
            "Created At",
        ]
    )

    # Data rows
    for exhibitor in exhibitors:
        writer.writerow(
            [
                exhibitor.reference_number,
                exhibitor.company_legal_name,
                f"{exhibitor.first_name} {exhibitor.last_name}",
                exhibitor.email,
                exhibitor.full_phone or "",
                exhibitor.company_country or "",
                exhibitor.company_website or "",
                exhibitor.package_type.value if exhibitor.package_type else "",
                exhibitor.booth_number or "",
                "Yes" if exhibitor.booth_assigned else "No",
                exhibitor.status.value,
                "Yes" if exhibitor.contract_signed else "No",
                exhibitor.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )

    # Create response
    output = BytesIO()
    output.write(si.getvalue().encode("utf-8"))
    output.seek(0)

    filename = f"exhibitors_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return send_file(
        output, mimetype="text/csv", as_attachment=True, download_name=filename
    )


# ============================================
# 3. PAYMENTS MODULE
# ============================================


@admin_bp.route("/payments")
@admin_required
def list_payments():
    """List all payment transactions"""

    # Get filter parameters
    status_filter = request.args.get("status")
    method_filter = request.args.get("method")
    search_query = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 50

    # Build query
    query = Payment.query

    # Apply filters
    if status_filter:
        try:
            status_enum = PaymentStatus(status_filter)
            query = query.filter_by(payment_status=status_enum)
        except ValueError:
            pass

    if method_filter:
        try:
            method_enum = PaymentMethod(method_filter)
            query = query.filter_by(payment_method=method_enum)
        except ValueError:
            pass

    if search_query:
        # Join with Registration to search
        query = query.join(Registration).filter(
            or_(
                Payment.payment_reference.ilike(f"%{search_query}%"),
                Payment.invoice_number.ilike(f"%{search_query}%"),
                Payment.transaction_id.ilike(f"%{search_query}%"),
                Registration.reference_number.ilike(f"%{search_query}%"),
                Registration.email.ilike(f"%{search_query}%"),
            )
        )

    # Order by most recent
    query = query.order_by(Payment.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    payments = pagination.items

    return render_template(
        "admin/payments/list.html",
        payments=payments,
        pagination=pagination,
        status_filter=status_filter,
        method_filter=method_filter,
        search_query=search_query,
    )


@admin_bp.route("/payments/pending")
@admin_required
def pending_payments():
    """List payments pending verification"""

    page = request.args.get("page", 1, type=int)
    per_page = 50

    query = Payment.query.filter_by(payment_status=PaymentStatus.PENDING).order_by(
        Payment.created_at.desc()
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    payments = pagination.items

    return render_template(
        "admin/payments/pending.html", payments=payments, pagination=pagination
    )


@admin_bp.route("/payments/failed")
@admin_required
def failed_payments():
    """List failed payments"""

    page = request.args.get("page", 1, type=int)
    per_page = 50

    query = Payment.query.filter_by(payment_status=PaymentStatus.FAILED).order_by(
        Payment.payment_failed_at.desc()
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    payments = pagination.items

    return render_template(
        "admin/payments/failed.html", payments=payments, pagination=pagination
    )


@admin_bp.route("/payments/<int:id>")
@admin_required
def view_payment(id):
    """View payment details"""
    payment = Payment.query.get_or_404(id)

    # Get associated registration
    registration = Registration.query.get(payment.registration_id)

    # Get refund form if needed
    refund_form = RefundForm()
    verification_form = PaymentVerificationForm()

    return render_template(
        "admin/payments/detail.html",
        payment=payment,
        registration=registration,
        refund_form=refund_form,
        verification_form=verification_form,
    )


@admin_bp.route("/payments/<int:id>/verify", methods=["POST"])
@admin_required
def verify_payment(id):
    """Manually verify payment"""
    payment = Payment.query.get_or_404(id)

    form = PaymentVerificationForm()

    if form.validate_on_submit():
        try:
            # Mark payment as completed
            payment.mark_as_completed(transaction_id=form.transaction_id.data)
            payment.payment_notes = form.payment_notes.data
            payment.verified_by = current_user.name
            payment.verified_at = datetime.now()

            # Update registration status
            registration = Registration.query.get(payment.registration_id)
            if registration and registration.is_fully_paid():
                registration.status = RegistrationStatus.CONFIRMED
                registration.confirmed_at = datetime.now()

            db.session.commit()

            flash("Payment verified successfully.", "success")
            logger.info(f"Payment {id} verified by {current_user.name}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error verifying payment {id}: {str(e)}")
            flash("Error verifying payment.", "error")

    return redirect(url_for("admin.view_payment", id=id))


@admin_bp.route("/payments/<int:id>/refund", methods=["GET", "POST"])
@admin_required
def process_refund(id):
    """Process payment refund"""
    payment = Payment.query.get_or_404(id)

    if not payment.is_paid:
        flash("Cannot refund a payment that is not completed.", "error")
        return redirect(url_for("admin.view_payment", id=id))

    form = RefundForm()

    if form.validate_on_submit():
        try:
            refund_amount = Decimal(str(form.refund_amount.data))

            # Validate refund amount
            if refund_amount > payment.net_amount:
                flash("Refund amount cannot exceed the net payment amount.", "error")
                return render_template(
                    "admin/payments/refund.html", payment=payment, form=form
                )

            # Process refund
            payment.process_refund(
                amount=refund_amount,
                reason=form.refund_reason.data,
                refunded_by=current_user.name,
            )

            if form.refund_reference.data:
                payment.refund_reference = form.refund_reference.data

            # Update registration status if fully refunded
            if payment.payment_status == PaymentStatus.REFUNDED:
                registration = Registration.query.get(payment.registration_id)
                if registration:
                    registration.status = RegistrationStatus.REFUNDED

            db.session.commit()

            flash(
                f"Refund of {payment.currency} {refund_amount} processed successfully.",
                "success",
            )
            logger.info(
                f"Payment {id} refunded by {current_user.name}: {refund_amount}"
            )

            return redirect(url_for("admin.view_payment", id=id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing refund for payment {id}: {str(e)}")
            flash(f"Error processing refund: {str(e)}", "error")

    return render_template("admin/payments/refund.html", payment=payment, form=form)


@admin_bp.route("/payments/export")
@admin_required
def export_payments():
    """Export payments to CSV"""
    import csv
    from io import StringIO

    # Get filters
    status_filter = request.args.get("status")

    query = Payment.query.join(Registration)

    if status_filter:
        try:
            status_enum = PaymentStatus(status_filter)
            query = query.filter(Payment.payment_status == status_enum)
        except ValueError:
            pass

    payments = query.order_by(Payment.created_at.desc()).all()

    # Create CSV
    si = StringIO()
    writer = csv.writer(si)

    # Header
    writer.writerow(
        [
            "Payment Reference",
            "Invoice Number",
            "Registration Reference",
            "Email",
            "Amount",
            "Currency",
            "Payment Method",
            "Status",
            "Transaction ID",
            "Created At",
            "Completed At",
        ]
    )

    # Data rows
    for payment in payments:
        writer.writerow(
            [
                payment.payment_reference,
                payment.invoice_number or "",
                payment.registration.reference_number,
                payment.registration.email,
                float(payment.total_amount),
                payment.currency,
                payment.payment_method.value if payment.payment_method else "",
                payment.payment_status.value,
                payment.transaction_id or "",
                payment.created_at.strftime("%Y-%m-%d %H:%M"),
                payment.payment_completed_at.strftime("%Y-%m-%d %H:%M")
                if payment.payment_completed_at
                else "",
            ]
        )

    # Create response
    output = BytesIO()
    output.write(si.getvalue().encode("utf-8"))
    output.seek(0)

    filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return send_file(
        output, mimetype="text/csv", as_attachment=True, download_name=filename
    )


# ============================================
# 4. EVENT MANAGEMENT - TICKETS
# ============================================


@admin_bp.route("/tickets")
@admin_required
def list_tickets():
    """List all ticket types"""
    tickets = TicketPrice.query.order_by(TicketPrice.price).all()
    return render_template("admin/tickets/list.html", tickets=tickets)


@admin_bp.route("/tickets/create", methods=["GET", "POST"])
@admin_required
def create_ticket():
    """Create new ticket type"""
    form = TicketPriceForm()

    if form.validate_on_submit():
        try:
            ticket = TicketPrice()
            form.populate_obj(ticket)
            ticket.created_at = datetime.now()

            db.session.add(ticket)
            db.session.commit()

            flash("Ticket type created successfully.", "success")
            return redirect(url_for("admin.list_tickets"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating ticket: {str(e)}")
            flash("Error creating ticket type.", "error")

    return render_template("admin/tickets/form.html", form=form, mode="create")


@admin_bp.route("/tickets/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_ticket(id):
    """Edit ticket type"""
    ticket = TicketPrice.query.get_or_404(id)
    form = TicketPriceForm(obj=ticket)

    if form.validate_on_submit():
        try:
            form.populate_obj(ticket)
            ticket.updated_at = datetime.now()

            db.session.commit()

            flash("Ticket type updated successfully.", "success")
            return redirect(url_for("admin.list_tickets"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating ticket {id}: {str(e)}")
            flash("Error updating ticket type.", "error")

    return render_template(
        "admin/tickets/form.html", form=form, ticket=ticket, mode="edit"
    )


@admin_bp.route("/tickets/<int:id>/toggle", methods=["POST"])
@admin_required
def toggle_ticket_status(id):
    """Toggle ticket active status"""
    ticket = TicketPrice.query.get_or_404(id)

    try:
        ticket.is_active = not ticket.is_active
        db.session.commit()

        status = "activated" if ticket.is_active else "deactivated"
        flash(f"Ticket type {status} successfully.", "success")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "is_active": ticket.is_active})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling ticket {id}: {str(e)}")
        flash("Error updating ticket status.", "error")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": str(e)}), 400

    return redirect(url_for("admin.list_tickets"))


# ============================================
# 4. EVENT MANAGEMENT - PACKAGES
# ============================================


@admin_bp.route("/packages")
@admin_required
def list_packages():
    """List all exhibitor packages"""
    packages = ExhibitorPackagePrice.query.order_by(ExhibitorPackagePrice.price).all()
    return render_template("admin/packages/list.html", packages=packages)


@admin_bp.route("/packages/create", methods=["GET", "POST"])
@admin_required
def create_package():
    """Create new exhibitor package"""
    form = ExhibitorPackageForm()

    if form.validate_on_submit():
        try:
            package = ExhibitorPackagePrice()
            form.populate_obj(package)
            package.created_at = datetime.now()

            db.session.add(package)
            db.session.commit()

            flash("Package created successfully.", "success")
            return redirect(url_for("admin.list_packages"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating package: {str(e)}")
            flash("Error creating package.", "error")

    return render_template("admin/packages/form.html", form=form, mode="create")


@admin_bp.route("/packages/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_package(id):
    """Edit exhibitor package"""
    package = ExhibitorPackagePrice.query.get_or_404(id)
    form = ExhibitorPackageForm(obj=package)

    if form.validate_on_submit():
        try:
            form.populate_obj(package)
            package.updated_at = datetime.now()

            db.session.commit()

            flash("Package updated successfully.", "success")
            return redirect(url_for("admin.list_packages"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating package {id}: {str(e)}")
            flash("Error updating package.", "error")

    return render_template(
        "admin/packages/form.html", form=form, package=package, mode="edit"
    )


@admin_bp.route("/packages/<int:id>/toggle", methods=["POST"])
@admin_required
def toggle_package_status(id):
    """Toggle package active status"""
    package = ExhibitorPackagePrice.query.get_or_404(id)

    try:
        package.is_active = not package.is_active
        db.session.commit()

        status = "activated" if package.is_active else "deactivated"
        flash(f"Package {status} successfully.", "success")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "is_active": package.is_active})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling package {id}: {str(e)}")
        flash("Error updating package status.", "error")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": str(e)}), 400

    return redirect(url_for("admin.list_packages"))


# ============================================
# 4. EVENT MANAGEMENT - ADD-ONS
# ============================================


@admin_bp.route("/addons")
@admin_required
def list_addons():
    """List all add-on items"""
    addons = AddOnItem.query.order_by(AddOnItem.name).all()
    return render_template("admin/addons/list.html", addons=addons)


@admin_bp.route("/addons/create", methods=["GET", "POST"])
@admin_required
def create_addon():
    """Create new add-on item"""
    form = AddOnItemForm()

    if form.validate_on_submit():
        try:
            addon = AddOnItem()
            form.populate_obj(addon)
            addon.created_at = datetime.now()

            db.session.add(addon)
            db.session.commit()

            flash("Add-on item created successfully.", "success")
            return redirect(url_for("admin.list_addons"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating add-on: {str(e)}")
            flash("Error creating add-on item.", "error")

    return render_template("admin/addons/form.html", form=form, mode="create")


@admin_bp.route("/addons/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_addon(id):
    """Edit add-on item"""
    addon = AddOnItem.query.get_or_404(id)
    form = AddOnItemForm(obj=addon)

    if form.validate_on_submit():
        try:
            form.populate_obj(addon)
            addon.updated_at = datetime.now()

            db.session.commit()

            flash("Add-on item updated successfully.", "success")
            return redirect(url_for("admin.list_addons"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating add-on {id}: {str(e)}")
            flash("Error updating add-on item.", "error")

    return render_template(
        "admin/addons/form.html", form=form, addon=addon, mode="edit"
    )


@admin_bp.route("/addons/<int:id>/delete", methods=["POST"])
@admin_required
def delete_addon(id):
    """Delete add-on item"""
    addon = AddOnItem.query.get_or_404(id)

    try:
        db.session.delete(addon)
        db.session.commit()

        flash("Add-on item deleted successfully.", "success")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting add-on {id}: {str(e)}")
        flash("Error deleting add-on item. It may be in use.", "error")

    return redirect(url_for("admin.list_addons"))


# ============================================
# 4. EVENT MANAGEMENT - PROMO CODES
# ============================================


@admin_bp.route("/promo-codes")
@admin_required
def list_promo_codes():
    """List all promo codes"""
    promo_codes = PromoCode.query.order_by(PromoCode.created_at.desc()).all()
    return render_template("admin/promo_codes/list.html", promo_codes=promo_codes)


@admin_bp.route("/promo-codes/create", methods=["GET", "POST"])
@admin_required
def create_promo_code():
    """Create new promo code"""
    form = AdminPromoCodeForm()

    if form.validate_on_submit():
        try:
            promo_code = PromoCode()
            form.populate_obj(promo_code)
            promo_code.code = promo_code.code.upper()
            promo_code.created_by = current_user.name
            promo_code.created_at = datetime.now()

            db.session.add(promo_code)
            db.session.commit()

            flash(f'Promo code "{promo_code.code}" created successfully.', "success")
            return redirect(url_for("admin.list_promo_codes"))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating promo code: {str(e)}")
            flash("Error creating promo code.", "error")

    return render_template("admin/promo_codes/form.html", form=form, mode="create")


# ============================================
# 5. EXHIBITOR OPERATIONS - BOOTH MANAGEMENT
# ============================================


@admin_bp.route("/exhibitors/booths")
@admin_required
def booth_management():
    """Booth assignment management interface"""

    # Get all confirmed exhibitors
    exhibitors = (
        ExhibitorRegistration.query.filter_by(
            status=RegistrationStatus.CONFIRMED, is_deleted=False
        )
        .order_by(ExhibitorRegistration.created_at)
        .all()
    )

    # Separate assigned and unassigned
    assigned = [e for e in exhibitors if e.booth_assigned]
    unassigned = [e for e in exhibitors if not e.booth_assigned]

    form = BoothAssignmentForm()

    return render_template(
        "admin/exhibitors/booths.html",
        assigned_exhibitors=assigned,
        unassigned_exhibitors=unassigned,
        form=form,
    )


# ============================================
# 6. CHECK-IN & BADGES
# ============================================


@admin_bp.route("/checkin", methods=["GET", "POST"])
@admin_required
def checkin():
    """Unified check-in interface for attendees and exhibitors"""

    if request.method == "POST":
        # Handle QR code scan or manual check-in
        reference = request.form.get("reference_number", "").strip()
        registration_type = request.form.get(
            "type", "attendee"
        )  # attendee or exhibitor

        if reference:
            # Try to find registration (attendee or exhibitor)
            registration = Registration.query.filter_by(
                reference_number=reference, is_deleted=False
            ).first()

            if registration:
                if registration.checked_in:
                    flash(
                        f"{registration.name} is already checked in.",
                        "info",
                    )
                else:
                    registration.check_in(checked_in_by=current_user.name)
                    db.session.commit()
                    reg_type = (
                        "Attendee"
                        if isinstance(registration, AttendeeRegistration)
                        else "Exhibitor"
                    )
                    flash(
                        f"{reg_type} {registration.name} checked in successfully!",
                        "success",
                    )
            else:
                flash("Registration not found with that reference number.", "error")

    # Get recent check-ins for both attendees and exhibitors
    recent_attendee_checkins = (
        AttendeeRegistration.query.filter_by(checked_in=True, is_deleted=False)
        .order_by(AttendeeRegistration.checked_in_at.desc())
        .limit(10)
        .all()
    )

    recent_exhibitor_checkins = (
        ExhibitorRegistration.query.filter_by(checked_in=True, is_deleted=False)
        .order_by(ExhibitorRegistration.checked_in_at.desc())
        .limit(10)
        .all()
    )

    # Stats for attendees
    total_confirmed_attendees = AttendeeRegistration.query.filter_by(
        status=RegistrationStatus.CONFIRMED, is_deleted=False
    ).count()

    checked_in_attendees = AttendeeRegistration.query.filter_by(
        checked_in=True, is_deleted=False
    ).count()

    # Stats for exhibitors
    total_confirmed_exhibitors = ExhibitorRegistration.query.filter_by(
        status=RegistrationStatus.CONFIRMED, is_deleted=False
    ).count()

    checked_in_exhibitors = ExhibitorRegistration.query.filter_by(
        checked_in=True, is_deleted=False
    ).count()

    return render_template(
        "admin/checkin/index.html",
        recent_attendee_checkins=recent_attendee_checkins,
        recent_exhibitor_checkins=recent_exhibitor_checkins,
        total_confirmed_attendees=total_confirmed_attendees,
        checked_in_attendees=checked_in_attendees,
        total_confirmed_exhibitors=total_confirmed_exhibitors,
        checked_in_exhibitors=checked_in_exhibitors,
    )


@admin_bp.route("/badges/generate", methods=["POST"])
@admin_required
def generate_badges():
    """Bulk badge generation"""

    registration_ids = request.form.getlist("registration_ids")

    if not registration_ids:
        flash("No registrations selected for badge generation.", "error")
        return redirect(request.referrer or url_for("admin.dashboard"))

    try:
        generated_count = 0

        for reg_id in registration_ids:
            registration = Registration.query.get(int(reg_id))
            if registration and not registration.qr_code_image_url:
                # Generate QR code using BadgeService
                success = BadgeService.generate_qr_code(registration)
                if success:
                    generated_count += 1

        db.session.commit()

        flash(f"{generated_count} badges generated successfully.", "success")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating badges: {str(e)}")
        flash("Error generating badges.", "error")

    return redirect(request.referrer or url_for("admin.dashboard"))


# ============================================
# 7. COMMUNICATIONS - EMAIL LOGS
# ============================================


@admin_bp.route("/emails")
@admin_required
def email_logs():
    """View email tracking logs"""

    # Get filter parameters
    email_type_filter = request.args.get("type")
    status_filter = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = 50

    query = EmailLog.query

    if email_type_filter:
        query = query.filter_by(email_type=email_type_filter)

    if status_filter:
        query = query.filter_by(status=status_filter)

    query = query.order_by(EmailLog.sent_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    emails = pagination.items

    return render_template(
        "admin/emails/logs.html",
        emails=emails,
        pagination=pagination,
        email_type_filter=email_type_filter,
        status_filter=status_filter,
    )


@admin_bp.route("/communications/bulk", methods=["GET", "POST"])
@admin_required
def bulk_email():
    """Send bulk emails to registrants"""
    form = BulkEmailForm()

    if form.validate_on_submit():
        try:
            recipient_type = form.recipient_type.data

            # Build recipient query based on type
            if recipient_type == "all_attendees":
                recipients = AttendeeRegistration.query.filter_by(
                    is_deleted=False
                ).all()
            elif recipient_type == "all_exhibitors":
                recipients = ExhibitorRegistration.query.filter_by(
                    is_deleted=False
                ).all()
            elif recipient_type == "confirmed_attendees":
                recipients = AttendeeRegistration.query.filter_by(
                    status=RegistrationStatus.CONFIRMED, is_deleted=False
                ).all()
            elif recipient_type == "confirmed_exhibitors":
                recipients = ExhibitorRegistration.query.filter_by(
                    status=RegistrationStatus.CONFIRMED, is_deleted=False
                ).all()
            elif recipient_type == "pending_payment":
                recipients = Registration.query.filter_by(
                    status=RegistrationStatus.PENDING, is_deleted=False
                ).all()
            elif recipient_type == "checked_in":
                recipients = AttendeeRegistration.query.filter_by(
                    checked_in=True, is_deleted=False
                ).all()
            else:
                recipients = []

            # Send test email first if requested
            if form.send_test.data and form.test_email.data:
                # TODO: Implement test email sending
                flash(f"Test email would be sent to {form.test_email.data}", "info")
                return render_template("admin/communications/bulk.html", form=form)

            # Queue bulk emails (would integrate with email service)
            recipient_count = len(recipients)

            # TODO: Implement actual bulk email sending
            # For now, just show confirmation
            flash(f"Bulk email queued for {recipient_count} recipients.", "success")
            logger.info(
                f"Bulk email queued by {current_user.name} to {recipient_count} {recipient_type}"
            )

            return redirect(url_for("admin.email_logs"))

        except Exception as e:
            logger.error(f"Error sending bulk email: {str(e)}")
            flash("Error queuing bulk email.", "error")

    return render_template("admin/communications/bulk.html", form=form)


@admin_bp.route("/contact-messages")
@admin_required
def list_contact_messages():
    """List all contact form submissions"""
    from app.models.contact import ContactMessage

    # Filters
    status_filter = request.args.get("status")
    inquiry_type_filter = request.args.get("inquiry_type")
    priority_filter = request.args.get("priority")
    search = request.args.get("search", "").strip()

    query = ContactMessage.query.filter_by(is_deleted=False)

    # Apply filters
    if status_filter:
        query = query.filter_by(status=status_filter)
    if inquiry_type_filter:
        query = query.filter_by(inquiry_type=inquiry_type_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    if search:
        query = query.filter(
            db.or_(
                ContactMessage.reference_number.ilike(f"%{search}%"),
                ContactMessage.first_name.ilike(f"%{search}%"),
                ContactMessage.last_name.ilike(f"%{search}%"),
                ContactMessage.email.ilike(f"%{search}%"),
                ContactMessage.subject.ilike(f"%{search}%"),
            )
        )

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    messages = query.order_by(ContactMessage.submitted_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get counts for stats
    total_new = ContactMessage.query.filter_by(status="new", is_deleted=False).count()
    total_in_progress = ContactMessage.query.filter_by(
        status="in_progress", is_deleted=False
    ).count()
    total_resolved = ContactMessage.query.filter_by(
        status="resolved", is_deleted=False
    ).count()

    return render_template(
        "admin/contact_messages/list.html",
        messages=messages,
        total_new=total_new,
        total_in_progress=total_in_progress,
        total_resolved=total_resolved,
        status_filter=status_filter,
        inquiry_type_filter=inquiry_type_filter,
        priority_filter=priority_filter,
        search=search,
    )


@admin_bp.route("/contact-messages/<int:id>")
@admin_required
def view_contact_message(id):
    """View contact message details"""
    from app.models.contact import ContactMessage

    message = ContactMessage.query.get_or_404(id)

    # Mark as read if new
    if message.is_new:
        message.mark_as_read()
        db.session.commit()

    return render_template("admin/contact_messages/detail.html", message=message)


@admin_bp.route("/contact-messages/<int:id>/respond", methods=["GET", "POST"])
@admin_required
def respond_contact_message(id):
    """Respond to contact message"""
    from app.models.contact import ContactMessage

    message = ContactMessage.query.get_or_404(id)
    form = ContactReplyForm()

    if form.validate_on_submit():
        try:
            # Send response email
            from flask_mail import Message as EmailMessage

            msg = EmailMessage(
                subject=f"Re: {message.subject}",
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                recipients=[message.email],
                reply_to=current_app.config.get("CONTACT_EMAIL", "info@beeseasy.org"),
            )

            # Create email context
            email_context = {
                "message": message,
                "response": form.response.data,
                "admin_name": current_user.name,
                "reference_number": message.reference_number,
            }

            msg.html = render_template("emails/contact_response.html", **email_context)
            msg.body = f"""
Dear {message.first_name},

Thank you for contacting us regarding "{message.subject}".

{form.response.data}

Reference Number: {message.reference_number}

Best regards,
{current_user.name}
Bee East Africa Symposium Team

---
This is a response to your inquiry submitted on {message.submitted_at.strftime("%B %d, %Y")}
            """

            mail.send(msg)

            # Update message status
            message.mark_as_resolved(
                resolved_by=current_user.name,
                response_message=form.response.data,
                notes=form.internal_notes.data,
            )
            db.session.commit()

            flash(f"Response sent to {message.email}", "success")
            logger.info(
                f"Contact message {message.reference_number} responded to by {current_user.name}"
            )

            return redirect(url_for("admin.view_contact_message", id=id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error responding to contact message {id}: {str(e)}")
            flash("Error sending response.", "error")

    return render_template(
        "admin/contact_messages/respond.html", message=message, form=form
    )


@admin_bp.route("/contact-messages/<int:id>/assign", methods=["POST"])
@admin_required
def assign_contact_message(id):
    """Assign contact message to admin user"""
    from app.models.contact import ContactMessage

    message = ContactMessage.query.get_or_404(id)

    try:
        message.assign_to(current_user.name)
        db.session.commit()
        flash(f"Message assigned to {current_user.name}", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error assigning contact message {id}: {str(e)}")
        flash("Error assigning message.", "error")

    return redirect(url_for("admin.view_contact_message", id=id))


@admin_bp.route("/contact-messages/<int:id>/priority", methods=["POST"])
@admin_required
def set_contact_priority(id):
    """Set contact message priority"""
    from app.models.contact import ContactMessage

    message = ContactMessage.query.get_or_404(id)
    priority = request.form.get("priority")

    if priority not in ["low", "normal", "high", "urgent"]:
        flash("Invalid priority level.", "error")
        return redirect(url_for("admin.view_contact_message", id=id))

    try:
        message.set_priority(priority)
        db.session.commit()
        flash(f"Priority set to {priority}", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error setting priority for contact message {id}: {str(e)}")
        flash("Error setting priority.", "error")

    return redirect(url_for("admin.view_contact_message", id=id))


@admin_bp.route("/contact-messages/<int:id>/delete", methods=["POST"])
@admin_required
def delete_contact_message(id):
    """Soft delete contact message"""
    from app.models.contact import ContactMessage

    message = ContactMessage.query.get_or_404(id)

    try:
        message.is_deleted = True
        message.deleted_at = datetime.now()
        db.session.commit()
        flash("Contact message deleted.", "success")
        logger.info(
            f"Contact message {message.reference_number} deleted by {current_user.name}"
        )
        return redirect(url_for("admin.list_contact_messages"))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting contact message {id}: {str(e)}")
        flash("Error deleting message.", "error")
        return redirect(url_for("admin.view_contact_message", id=id))


# ============================================
# 8. REPORTS
# ============================================


@admin_bp.route("/reports/registrations")
@admin_required
def registration_report():
    """Registration analytics and reports"""

    # Date range filters
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = Registration.query.filter_by(is_deleted=False)

    if date_from:
        from_date = datetime.strptime(date_from, "%Y-%m-%d")
        query = query.filter(Registration.created_at >= from_date)

    if date_to:
        to_date = datetime.strptime(date_to, "%Y-%m-%d")
        to_date = to_date.replace(hour=23, minute=59, second=59)
        query = query.filter(Registration.created_at <= to_date)

    # Get statistics
    total_registrations = query.count()

    # By status
    status_breakdown = (
        db.session.query(Registration.status, func.count(Registration.id))
        .filter(Registration.is_deleted == False)
        .group_by(Registration.status)
        .all()
    )

    # By type
    type_breakdown = (
        db.session.query(Registration.registration_type, func.count(Registration.id))
        .filter(Registration.is_deleted == False)
        .group_by(Registration.registration_type)
        .all()
    )

    # By ticket type (attendees)
    ticket_breakdown = (
        db.session.query(
            AttendeeRegistration.ticket_type, func.count(AttendeeRegistration.id)
        )
        .filter(AttendeeRegistration.is_deleted == False)
        .group_by(AttendeeRegistration.ticket_type)
        .all()
    )

    # By package (exhibitors)
    package_breakdown = (
        db.session.query(
            ExhibitorRegistration.package_type, func.count(ExhibitorRegistration.id)
        )
        .filter(ExhibitorRegistration.is_deleted == False)
        .group_by(ExhibitorRegistration.package_type)
        .all()
    )

    # Registrations over time (by day)
    daily_registrations = (
        db.session.query(
            func.date(Registration.created_at).label("date"),
            func.count(Registration.id).label("count"),
        )
        .filter(Registration.is_deleted == False)
        .group_by(func.date(Registration.created_at))
        .order_by(func.date(Registration.created_at))
        .all()
    )

    return render_template(
        "admin/reports/registrations.html",
        total_registrations=total_registrations,
        status_breakdown=status_breakdown,
        type_breakdown=type_breakdown,
        ticket_breakdown=ticket_breakdown,
        package_breakdown=package_breakdown,
        daily_registrations=daily_registrations,
        date_from=date_from,
        date_to=date_to,
    )


@admin_bp.route("/reports/revenue")
@admin_required
def revenue_report():
    """Revenue analytics"""

    # Total revenue
    total_revenue = db.session.query(func.sum(Payment.total_amount)).filter(
        Payment.payment_status == PaymentStatus.COMPLETED
    ).scalar() or Decimal("0.00")

    # By payment method
    method_breakdown = (
        db.session.query(
            Payment.payment_method,
            func.sum(Payment.total_amount),
            func.count(Payment.id),
        )
        .filter(Payment.payment_status == PaymentStatus.COMPLETED)
        .group_by(Payment.payment_method)
        .all()
    )

    # By registration type
    type_revenue = (
        db.session.query(Registration.registration_type, func.sum(Payment.total_amount))
        .join(Payment)
        .filter(Payment.payment_status == PaymentStatus.COMPLETED)
        .group_by(Registration.registration_type)
        .all()
    )

    # Revenue over time
    daily_revenue = (
        db.session.query(
            func.date(Payment.payment_completed_at).label("date"),
            func.sum(Payment.total_amount).label("revenue"),
        )
        .filter(Payment.payment_status == PaymentStatus.COMPLETED)
        .group_by(func.date(Payment.payment_completed_at))
        .order_by(func.date(Payment.payment_completed_at))
        .all()
    )

    return render_template(
        "admin/reports/revenue.html",
        total_revenue=total_revenue,
        method_breakdown=method_breakdown,
        type_revenue=type_revenue,
        daily_revenue=daily_revenue,
    )


# ============================================
# 9. SETTINGS - USER MANAGEMENT
# ============================================


@admin_bp.route("/users")
@admin_only
def list_users():
    """List all admin users"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users/list.html", users=users)


@admin_bp.route("/users/create", methods=["GET", "POST"])
@admin_only
def create_user():
    """Create new admin user"""
    form = UserForm()

    if form.validate_on_submit():
        try:
            user = User()
            user.name = form.name.data
            user.email = form.email.data.lower()
            user.role = UserRole(form.role.data)
            user.is_active = form.is_active.data

            if form.password.data:
                user.set_password(form.password.data)
            else:
                # Generate random password if not provided
                import secrets

                temp_password = secrets.token_urlsafe(12)
                user.set_password(temp_password)
                flash(
                    f"Temporary password: {temp_password} (send this to the user)",
                    "info",
                )

            db.session.add(user)
            db.session.commit()

            flash("User created successfully.", "success")
            return redirect(url_for("admin.list_users"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            flash("Error creating user. Email may already exist.", "error")

    return render_template("admin/users/form.html", form=form, mode="create")


@admin_bp.route("/users/<int:id>/edit", methods=["GET", "POST"])
@admin_only
def edit_user(id):
    """Edit admin user"""
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)

    # Convert role enum to string for form
    if request.method == "GET":
        form.role.data = user.role.value

    if form.validate_on_submit():
        try:
            user.name = form.name.data
            user.email = form.email.data.lower()
            user.role = UserRole(form.role.data)
            user.is_active = form.is_active.data

            if form.password.data:
                user.set_password(form.password.data)

            db.session.commit()

            flash("User updated successfully.", "success")
            return redirect(url_for("admin.list_users"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user {id}: {str(e)}")
            flash("Error updating user.", "error")

    return render_template("admin/users/form.html", form=form, user=user, mode="edit")


@admin_bp.route("/users/<int:id>/toggle", methods=["POST"])
@admin_only
def toggle_user_status(id):
    """Toggle user active status"""
    user = User.query.get_or_404(id)

    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("admin.list_users"))

    try:
        user.is_active = not user.is_active
        db.session.commit()

        status = "activated" if user.is_active else "deactivated"
        flash(f"User {status} successfully.", "success")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling user {id}: {str(e)}")
        flash("Error updating user status.", "error")

    return redirect(url_for("admin.list_users"))


# ============================================
# 9. SETTINGS - EXCHANGE RATES
# ============================================


@admin_bp.route("/settings/exchange-rates", methods=["GET", "POST"])
@admin_required
def exchange_rates():
    """Manage currency exchange rates"""
    form = ExchangeRateForm()

    if form.validate_on_submit():
        try:
            rate = ExchangeRate()
            form.populate_obj(rate)
            rate.created_by = current_user.name
            rate.created_at = datetime.now()

            db.session.add(rate)
            db.session.commit()

            flash("Exchange rate added successfully.", "success")
            return redirect(url_for("admin.exchange_rates"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding exchange rate: {str(e)}")
            flash("Error adding exchange rate.", "error")

    # Get all current rates
    rates = ExchangeRate.query.order_by(ExchangeRate.effective_date.desc()).all()

    return render_template("admin/settings/exchange.html", form=form, rates=rates)


@admin_bp.route("/promo-codes/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_promo_code(id):
    """Edit promo code"""
    promo_code = PromoCode.query.get_or_404(id)
    form = AdminPromoCodeForm(obj=promo_code)

    if form.validate_on_submit():
        try:
            form.populate_obj(promo_code)
            promo_code.code = promo_code.code.upper()
            promo_code.updated_at = datetime.now()

            db.session.commit()

            flash("Promo code updated successfully.", "success")
            return redirect(url_for("admin.list_promo_codes"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating promo code {id}: {str(e)}")
            flash("Error updating promo code.", "error")

    return render_template(
        "admin/promo_codes/form.html", form=form, promo_code=promo_code, mode="edit"
    )


@admin_bp.route("/promo-codes/<int:id>/usage")
@admin_required
def promo_code_usage(id):
    """View promo code usage statistics"""
    promo_code = PromoCode.query.get_or_404(id)

    # Get usage records
    usages = (
        PromoCodeUsage.query.filter_by(promo_code_id=id)
        .order_by(PromoCodeUsage.used_at.desc())
        .all()
    )

    # Calculate statistics
    total_discount = sum(Decimal(str(u.discount_amount)) for u in usages)

    return render_template(
        "admin/promo_codes/usage.html",
        promo_code=promo_code,
        usages=usages,
        total_discount=total_discount,
    )


@admin_bp.route("/promo-codes/<int:id>/toggle", methods=["POST"])
@admin_required
def toggle_promo_code(id):
    """Toggle promo code active status"""
    promo_code = PromoCode.query.get_or_404(id)

    try:
        promo_code.is_active = not promo_code.is_active
        db.session.commit()

        status = "activated" if promo_code.is_active else "deactivated"
        flash(f"Promo code {status} successfully.", "success")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "is_active": promo_code.is_active})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling promo code {id}: {str(e)}")
        flash("Error updating promo code status.", "error")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": str(e)}), 400

    return redirect(url_for("admin.list_promo_codes"))


# ============================================
# 10. SETTINGS - SYSTEM SETTINGS
# ============================================


@admin_bp.route("/settings")
@admin_only
def system_settings():
    """System settings dashboard (placeholder for future development)"""

    # Placeholder for system-wide settings
    # Future features could include:
    # - Event configuration (dates, venue, capacity limits)
    # - Email templates customization
    # - Payment gateway settings
    # - Notification preferences
    # - System maintenance mode
    # - API key management
    # - Branding and theme settings

    settings_sections = [
        {
            "name": "Event Configuration",
            "description": "Manage event dates, venue, and capacity settings",
            "status": "Coming Soon",
            "icon": "calendar",
        },
        {
            "name": "Email Templates",
            "description": "Customize automated email templates",
            "status": "Coming Soon",
            "icon": "envelope",
        },
        {
            "name": "Payment Settings",
            "description": "Configure payment gateways and options",
            "status": "Coming Soon",
            "icon": "credit-card",
        },
        {
            "name": "Notification Preferences",
            "description": "Manage system notifications and alerts",
            "status": "Coming Soon",
            "icon": "bell",
        },
        {
            "name": "Branding & Theme",
            "description": "Customize colors, logos, and branding",
            "status": "Coming Soon",
            "icon": "palette",
        },
        {
            "name": "API Management",
            "description": "Manage API keys and integrations",
            "status": "Coming Soon",
            "icon": "key",
        },
    ]

    return render_template(
        "admin/settings/system.html", settings_sections=settings_sections
    )
