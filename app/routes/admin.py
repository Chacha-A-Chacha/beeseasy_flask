"""
Admin routes for BEEASY2025
Comprehensive admin panel for managing registrations, payments, tickets, and event operations
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps
from io import BytesIO
from pathlib import Path

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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.extensions import db
from app.forms import (
    AddOnItemForm,
    AdminPromoCodeForm,
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

    # Checked-in count (using DailyCheckIn model)
    from app.models import DailyCheckIn

    checked_in_count = (
        db.session.query(func.count(func.distinct(DailyCheckIn.registration_id)))
        .join(
            AttendeeRegistration,
            DailyCheckIn.registration_id == AttendeeRegistration.id,
        )
        .filter(AttendeeRegistration.is_deleted == False)
        .scalar()
        or 0
    )

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
        # Filter by check-in status using DailyCheckIn model
        from app.models import DailyCheckIn

        checked_in_value = checked_in_filter.lower() == "true"
        if checked_in_value:
            # Show only those who have at least one check-in
            query = query.join(
                DailyCheckIn, AttendeeRegistration.id == DailyCheckIn.registration_id
            )
        else:
            # Show only those who have no check-ins
            query = query.outerjoin(
                DailyCheckIn, AttendeeRegistration.id == DailyCheckIn.registration_id
            ).filter(DailyCheckIn.id == None)

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
            flash("Something went wrong while updating the attendee registration. Please try again.", "error")

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
        flash("Could not cancel the registration. Please try again.", "error")

    return redirect(url_for("admin.view_attendee", id=id))


@admin_bp.route("/registrations/attendees/<int:id>/check-in", methods=["POST"])
@admin_required
def checkin_attendee(id):
    """Mark attendee as checked in for today"""
    from datetime import date

    attendee = AttendeeRegistration.query.get_or_404(id)

    try:
        # Check in for today's date
        today = date.today()
        attendee.check_in_for_day(
            event_date=today, checked_in_by=current_user.name, check_in_method="manual"
        )
        db.session.commit()

        flash(
            f"Attendee checked in successfully for {today.strftime('%Y-%m-%d')}.",
            "success",
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "message": "Checked in successfully"})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error checking in attendee {id}: {str(e)}")
        flash("Check-in failed. Please try again.", "error")

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
        # Check if attendee has any check-ins
        has_checked_in = len(attendee.daily_checkins) > 0
        writer.writerow(
            [
                attendee.reference_number,
                attendee.first_name,
                attendee.last_name,
                attendee.email,
                attendee.full_phone or "",
                attendee.organization or "",
                attendee.job_title or "",
                attendee.country_name or "",
                attendee.city or "",
                attendee.ticket_type.value if attendee.ticket_type else "",
                attendee.status.value,
                "Yes" if has_checked_in else "No",
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
            flash("Something went wrong while updating the exhibitor registration. Please try again.", "error")

    return render_template(
        "admin/registrations/exhibitors/edit.html", exhibitor=exhibitor, form=form
    )


@admin_bp.route("/registrations/exhibitors/<int:id>/assign-booth", methods=["POST"])
@admin_required
def assign_booth(id):
    """Assign booth number to exhibitor"""
    exhibitor = ExhibitorRegistration.query.get_or_404(id)

    booth_number = (request.form.get("booth_number") or "").strip().upper()

    if not booth_number:
        flash("Booth number is required.", "error")
        return redirect(request.referrer or url_for("admin.booth_management"))

    try:
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
            return redirect(request.referrer or url_for("admin.booth_management"))

        # Assign booth
        exhibitor.assign_booth(booth_number, assigned_by=current_user.name)

        # Add note if provided
        notes = request.form.get("notes")
        if notes:
            if not exhibitor.admin_notes:
                exhibitor.admin_notes = ""
            exhibitor.admin_notes += (
                f"\n[{datetime.now()}] Booth Assignment: {notes}"
            )

        db.session.commit()

        flash(f"Booth {booth_number} assigned successfully.", "success")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error assigning booth to exhibitor {id}: {str(e)}")
        flash("Could not assign the booth. Please try again.", "error")

    return redirect(request.referrer or url_for("admin.booth_management"))


@admin_bp.route("/registrations/exhibitors/<int:id>/unassign-booth", methods=["POST"])
@admin_required
def unassign_booth(id):
    """Remove booth assignment from exhibitor"""
    exhibitor = ExhibitorRegistration.query.get_or_404(id)

    if not exhibitor.booth_assigned:
        flash("This exhibitor does not have a booth assigned.", "error")
        return redirect(request.referrer or url_for("admin.booth_management"))

    try:
        old_booth = exhibitor.booth_number
        exhibitor.booth_number = None
        exhibitor.booth_assigned = False
        exhibitor.booth_assigned_at = None
        exhibitor.booth_assigned_by = None

        if not exhibitor.admin_notes:
            exhibitor.admin_notes = ""
        exhibitor.admin_notes += (
            f"\n[{datetime.now()}] Booth Unassigned: {old_booth} by {current_user.name}"
        )

        db.session.commit()
        flash(f"Booth {old_booth} unassigned from {exhibitor.company_legal_name}.", "success")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unassigning booth from exhibitor {id}: {str(e)}")
        flash("Could not unassign the booth. Please try again.", "error")

    return redirect(request.referrer or url_for("admin.booth_management"))


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
                exhibitor.company_country_name or "",
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
    """Manually verify payment (bank transfer / invoice)"""
    payment = Payment.query.get_or_404(id)

    form = PaymentVerificationForm()

    if form.validate_on_submit():
        try:
            payment.payment_notes = form.payment_notes.data
            payment.verified_by = current_user.name
            payment.verified_at = datetime.now()
            db.session.flush()

            success, message = RegistrationService.process_payment_completion(
                payment_id=payment.id,
                transaction_id=form.transaction_id.data,
                payment_method=payment.payment_method or PaymentMethod.BANK_TRANSFER,
            )

            if success:
                flash("Payment verified — confirmation email and badge sent.", "success")
                logger.info(f"Payment {id} manually verified by {current_user.name}")
            else:
                flash(f"Payment marked complete but post-processing issue: {message}", "warning")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error verifying payment {id}: {str(e)}")
            flash("Could not verify the payment. Please try again.", "error")

    return redirect(url_for("admin.view_payment", id=id))


@admin_bp.route("/payments/<int:id>/verify-dpo", methods=["POST"])
@admin_required
def verify_dpo_payment(id):
    """Check payment status with DPO gateway and complete if paid"""
    from app.services.dpo_service import dpo_service

    payment = Payment.query.get_or_404(id)

    if not payment.dpo_trans_token:
        flash("This payment has no DPO transaction token.", "error")
        return redirect(url_for("admin.view_payment", id=id))

    if payment.payment_status == PaymentStatus.COMPLETED:
        flash("This payment is already completed.", "info")
        return redirect(url_for("admin.view_payment", id=id))

    try:
        verification = dpo_service.verify_token(payment.dpo_trans_token)
        payment.update_from_dpo_verification(verification)
        db.session.commit()

        if verification.get("success"):
            success, message = RegistrationService.process_payment_completion(
                payment_id=payment.id,
                transaction_id=verification.get("trans_ref", ""),
                payment_method=PaymentMethod.MOBILE_MONEY
                if payment.payment_method == PaymentMethod.MOBILE_MONEY
                else PaymentMethod.CARD,
            )
            if success:
                flash("DPO confirmed payment — registration confirmed, badge and email sent.", "success")
            else:
                flash(f"DPO confirmed payment but post-processing issue: {message}", "warning")

            logger.info(f"DPO payment {id} verified by admin {current_user.name}: PAID")
        else:
            status = verification.get("status", "Unknown")
            dpo_msg = verification.get("message", verification.get("error", ""))
            flash(f"DPO status: {status}. {dpo_msg}", "warning")
            logger.info(f"DPO payment {id} checked by admin {current_user.name}: {status}")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error verifying DPO payment {id}: {str(e)}", exc_info=True)
        flash("Could not reach DPO gateway. Please try again.", "error")

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
            # Convert string value to enum
            ticket.ticket_type = AttendeeTicketType(form.ticket_type.data)
            ticket.version = 1
            ticket.created_at = datetime.now()

            db.session.add(ticket)
            db.session.commit()

            flash("Ticket type created successfully.", "success")
            return redirect(url_for("admin.list_tickets"))

        except IntegrityError:
            db.session.rollback()
            flash("A ticket with this type already exists. Please edit the existing one instead.", "error")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating ticket: {str(e)}")
            flash("Could not create the ticket. Please try again.", "error")

    return render_template("admin/tickets/form.html", form=form, mode="create")


@admin_bp.route("/tickets/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_ticket(id):
    """Edit ticket type"""
    ticket = TicketPrice.query.get_or_404(id)
    form = TicketPriceForm(obj=ticket)

    # Fix enum→string so the SelectField displays the correct value
    if request.method == "GET" and ticket.ticket_type:
        form.ticket_type.data = ticket.ticket_type.value

    if form.validate_on_submit():
        try:
            # Preserve the original ticket_type — it must not change after creation
            original_type = ticket.ticket_type
            form.populate_obj(ticket)
            ticket.ticket_type = original_type
            ticket.version = (ticket.version or 0) + 1
            ticket.updated_at = datetime.now()

            db.session.commit()

            flash("Ticket type updated successfully.", "success")
            return redirect(url_for("admin.list_tickets"))

        except StaleDataError:
            db.session.rollback()
            logger.warning(f"Concurrent edit conflict on ticket {id}")
            flash("This ticket was modified by another process. Please review and try again.", "warning")
        except IntegrityError:
            db.session.rollback()
            flash("A ticket with this type already exists. Each ticket type must be unique.", "error")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating ticket {id}: {str(e)}")
            flash("Could not update the ticket. Please try again.", "error")

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
        flash("Could not update the ticket status. Please try again.", "error")

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

        except IntegrityError:
            db.session.rollback()
            flash("A package with this type already exists. Please edit the existing one instead.", "error")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating package: {str(e)}")
            flash("Could not create the package. Please try again.", "error")

    return render_template("admin/packages/form.html", form=form, mode="create")


@admin_bp.route("/packages/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_package(id):
    """Edit exhibitor package"""
    package = ExhibitorPackagePrice.query.get_or_404(id)
    form = ExhibitorPackageForm(obj=package)

    # Fix enum→string so the SelectField displays the correct value
    if request.method == "GET" and package.package_type:
        form.package_type.data = package.package_type.value

    if form.validate_on_submit():
        try:
            # Save package_type before populate_obj overwrites it with a string
            original_package_type = package.package_type
            form.populate_obj(package)
            # Restore the original enum — package_type shouldn't change on edit
            package.package_type = original_package_type
            package.version = (package.version or 0) + 1
            package.updated_at = datetime.now()

            db.session.commit()

            flash("Package updated successfully.", "success")
            return redirect(url_for("admin.list_packages"))

        except StaleDataError:
            db.session.rollback()
            logger.warning(f"Concurrent edit conflict on package {id}")
            flash("This package was modified by another process. Please review and try again.", "warning")
        except IntegrityError:
            db.session.rollback()
            flash("A package with this type already exists. Each package type must be unique.", "error")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating package {id}: {str(e)}")
            flash("Could not update the package. Please try again.", "error")

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
        flash("Could not update the package status. Please try again.", "error")

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
            flash("Could not create the add-on item. Please try again.", "error")

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
            flash("Could not update the add-on item. Please try again.", "error")

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
        flash("Could not delete the add-on item. It may be in use by a registration.", "error")

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
            flash("Could not create the promo code. The code may already exist.", "error")

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

    return render_template(
        "admin/booths/list.html",
        assigned_exhibitors=assigned,
        unassigned_exhibitors=unassigned,
    )


# ============================================
# 6. CHECK-IN & BADGES
# ============================================


@admin_bp.route("/checkin", methods=["GET", "POST"])
@admin_required
def checkin():
    """Unified check-in interface for attendees and exhibitors"""
    from datetime import date

    from app.models import DailyCheckIn

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
                # Check if already checked in TODAY
                today = date.today()
                already_checked_in_today = registration.is_checked_in_for_day(today)

                if already_checked_in_today:
                    flash(
                        f"{registration.computed_full_name} is already checked in for today.",
                        "info",
                    )
                else:
                    registration.check_in_for_day(
                        event_date=today,
                        checked_in_by=current_user.name,
                        check_in_method="manual",
                    )
                    db.session.commit()
                    reg_type = (
                        "Attendee"
                        if isinstance(registration, AttendeeRegistration)
                        else "Exhibitor"
                    )
                    flash(
                        f"{reg_type} {registration.computed_full_name} checked in successfully for {today.strftime('%Y-%m-%d')}!",
                        "success",
                    )
            else:
                flash("Registration not found with that reference number.", "error")

    # Get recent check-ins for both attendees and exhibitors (using DailyCheckIn)
    recent_attendee_checkins_query = (
        db.session.query(AttendeeRegistration, DailyCheckIn)
        .join(DailyCheckIn, AttendeeRegistration.id == DailyCheckIn.registration_id)
        .filter(AttendeeRegistration.is_deleted == False)
        .order_by(DailyCheckIn.checked_in_at.desc())
        .limit(10)
        .all()
    )
    recent_attendee_checkins = [att for att, _ in recent_attendee_checkins_query]

    recent_exhibitor_checkins_query = (
        db.session.query(ExhibitorRegistration, DailyCheckIn)
        .join(DailyCheckIn, ExhibitorRegistration.id == DailyCheckIn.registration_id)
        .filter(ExhibitorRegistration.is_deleted == False)
        .order_by(DailyCheckIn.checked_in_at.desc())
        .limit(10)
        .all()
    )
    recent_exhibitor_checkins = [exh for exh, _ in recent_exhibitor_checkins_query]

    # Stats for attendees
    total_confirmed_attendees = AttendeeRegistration.query.filter_by(
        status=RegistrationStatus.CONFIRMED, is_deleted=False
    ).count()

    checked_in_attendees = (
        db.session.query(func.count(func.distinct(DailyCheckIn.registration_id)))
        .join(
            AttendeeRegistration,
            DailyCheckIn.registration_id == AttendeeRegistration.id,
        )
        .filter(AttendeeRegistration.is_deleted == False)
        .scalar()
        or 0
    )

    # Stats for exhibitors
    total_confirmed_exhibitors = ExhibitorRegistration.query.filter_by(
        status=RegistrationStatus.CONFIRMED, is_deleted=False
    ).count()

    checked_in_exhibitors = (
        db.session.query(func.count(func.distinct(DailyCheckIn.registration_id)))
        .join(
            ExhibitorRegistration,
            DailyCheckIn.registration_id == ExhibitorRegistration.id,
        )
        .filter(ExhibitorRegistration.is_deleted == False)
        .scalar()
        or 0
    )

    return render_template(
        "admin/checkin/index.html",
        recent_attendee_checkins=recent_attendee_checkins,
        recent_exhibitor_checkins=recent_exhibitor_checkins,
        total_confirmed_attendees=total_confirmed_attendees,
        checked_in_attendees=checked_in_attendees,
        total_confirmed_exhibitors=total_confirmed_exhibitors,
        checked_in_exhibitors=checked_in_exhibitors,
    )


@admin_bp.route("/badges")
@admin_required
def list_badges():
    """Badge management - view and generate badges for confirmed registrations"""
    type_filter = request.args.get("type", "all")
    badge_filter = request.args.get("badge_status", "all")
    search_query = request.args.get("search", "").strip()

    # Get confirmed registrations
    query = Registration.query.filter_by(
        status=RegistrationStatus.CONFIRMED, is_deleted=False
    )

    if type_filter == "attendee":
        query = query.filter_by(registration_type="attendee")
    elif type_filter == "exhibitor":
        query = query.filter_by(registration_type="exhibitor")

    if badge_filter == "generated":
        query = query.filter(Registration.qr_code_image_url.isnot(None))
    elif badge_filter == "pending":
        query = query.filter(Registration.qr_code_image_url.is_(None))

    if search_query:
        query = query.filter(
            or_(
                Registration.first_name.ilike(f"%{search_query}%"),
                Registration.last_name.ilike(f"%{search_query}%"),
                Registration.email.ilike(f"%{search_query}%"),
                Registration.reference_number.ilike(f"%{search_query}%"),
            )
        )

    registrations = query.order_by(Registration.created_at.desc()).all()

    # Stats
    total_confirmed = Registration.query.filter_by(
        status=RegistrationStatus.CONFIRMED, is_deleted=False
    ).count()
    badges_generated = Registration.query.filter(
        Registration.status == RegistrationStatus.CONFIRMED,
        Registration.is_deleted == False,
        Registration.qr_code_image_url.isnot(None),
    ).count()

    return render_template(
        "admin/badges/list.html",
        registrations=registrations,
        type_filter=type_filter,
        badge_filter=badge_filter,
        search_query=search_query,
        total_confirmed=total_confirmed,
        badges_generated=badges_generated,
    )


@admin_bp.route("/badges/generate", methods=["POST"])
@admin_required
def generate_badges():
    """Bulk badge generation"""

    registration_ids = request.form.getlist("registration_ids")

    if not registration_ids:
        flash("No registrations selected for badge generation.", "error")
        return redirect(url_for("admin.list_badges"))

    try:
        generated_count = 0

        for reg_id in registration_ids:
            registration = Registration.query.get(int(reg_id))
            if registration and not registration.qr_code_image_url:
                # Generate badge using BadgeService
                success, msg, badge_url = BadgeService.generate_badge(registration.id)
                if success:
                    generated_count += 1

        db.session.commit()

        flash(f"{generated_count} badges generated successfully.", "success")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating badges: {str(e)}")
        flash("Could not generate badges. Please try again.", "error")

    return redirect(url_for("admin.list_badges"))


@admin_bp.route("/badges/<int:id>/email", methods=["POST"])
@admin_required
def email_badge(id):
    """Email badge PDF to registrant"""
    from flask_mail import Message as EmailMessage

    from app.extensions import mail

    registration = Registration.query.get_or_404(id)

    if not registration.qr_code_image_url:
        flash("Badge has not been generated yet. Generate it first.", "error")
        return redirect(url_for("admin.list_badges"))

    # Resolve PDF file path
    badge_path = Path(current_app.root_path) / registration.qr_code_image_url.lstrip("/")

    if not badge_path.exists():
        flash("Badge file not found. Try regenerating the badge.", "error")
        return redirect(url_for("admin.list_badges"))

    try:
        download_url = url_for(
            "main.download_badge",
            reference=registration.reference_number,
            _external=True,
        )

        msg = EmailMessage(
            subject="Your Event Badge — Pollination Africa Summit",
            sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
            recipients=[registration.email],
        )

        msg.html = render_template(
            "emails/badge_delivery.html",
            registration=registration,
            download_url=download_url,
        )

        msg.body = (
            f"Dear {registration.computed_full_name},\n\n"
            f"Your badge for Pollination Africa Summit is attached to this email.\n"
            f"Print it or save it on your phone for event check-in.\n\n"
            f"Reference: {registration.reference_number}\n\n"
            f"You can also download your badge here: {download_url}\n\n"
            f"Best regards,\n"
            f"Pollination Africa Summit Team"
        )

        # Attach PDF
        with open(badge_path, "rb") as f:
            msg.attach(
                filename=f"{registration.reference_number}_badge.pdf",
                content_type="application/pdf",
                data=f.read(),
            )

        mail.send(msg)

        EmailLog.log(
            recipient_email=registration.email,
            recipient_name=registration.computed_full_name,
            subject="Your Event Badge — Pollination Africa Summit",
            email_type="badge_delivery",
            registration_id=registration.id,
            template_name="badge_delivery",
        )

        flash(f"Badge emailed to {registration.email}.", "success")
        logger.info(
            f"Badge emailed to {registration.email} for {registration.reference_number} by {current_user.name}"
        )

    except Exception as e:
        logger.error(f"Error emailing badge for registration {id}: {str(e)}")
        flash("Could not send the badge email. Please check email settings and try again.", "error")

    return redirect(url_for("admin.list_badges"))


# ============================================
# 7. COMMUNICATIONS - EMAIL LOGS
# ============================================


@admin_bp.route("/emails")
@admin_required
def email_logs():
    """View email tracking logs"""

    # Get filter parameters
    email_type_filter = request.args.get("email_type")
    status_filter = request.args.get("status")
    search_query = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 50

    query = EmailLog.query

    if email_type_filter:
        query = query.filter_by(email_type=email_type_filter)

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search_query:
        query = query.filter(
            db.or_(
                EmailLog.recipient_email.ilike(f"%{search_query}%"),
                EmailLog.subject.ilike(f"%{search_query}%"),
                EmailLog.recipient_name.ilike(f"%{search_query}%"),
            )
        )

    query = query.order_by(EmailLog.sent_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    emails = pagination.items

    return render_template(
        "admin/emails/logs.html",
        emails=emails,
        pagination=pagination,
        email_type_filter=email_type_filter,
        status_filter=status_filter,
        search_query=search_query,
    )


@admin_bp.route("/communications/bulk", methods=["GET", "POST"])
@admin_required
def bulk_email():
    """Send bulk emails to registrants"""
    import re

    from flask_mail import Message as EmailMessage

    from app.extensions import mail

    form = BulkEmailForm()

    if form.validate_on_submit():
        try:
            recipient_type = form.recipient_type.data

            # Build recipient query based on type
            recipient_queries = {
                "all_attendees": lambda: AttendeeRegistration.query.filter_by(
                    is_deleted=False
                ).all(),
                "all_exhibitors": lambda: ExhibitorRegistration.query.filter_by(
                    is_deleted=False
                ).all(),
                "confirmed_attendees": lambda: AttendeeRegistration.query.filter_by(
                    status=RegistrationStatus.CONFIRMED, is_deleted=False
                ).all(),
                "confirmed_exhibitors": lambda: ExhibitorRegistration.query.filter_by(
                    status=RegistrationStatus.CONFIRMED, is_deleted=False
                ).all(),
                "pending_payment": lambda: Registration.query.filter_by(
                    status=RegistrationStatus.PENDING, is_deleted=False
                ).all(),
                "checked_in": lambda: AttendeeRegistration.query.filter_by(
                    checked_in=True, is_deleted=False
                ).all(),
            }

            query_fn = recipient_queries.get(recipient_type)
            recipients = query_fn() if query_fn else []

            if not recipients:
                flash("No recipients found for the selected group.", "error")
                return render_template("admin/communications/bulk.html", form=form)

            subject = form.subject.data.strip()
            message_text = form.message.data.strip()
            # Convert plain text line breaks to HTML paragraphs
            paragraphs = message_text.split("\n\n")
            message_html = "".join(
                f"<p>{re.sub(chr(10), '<br />', p.strip())}</p>"
                for p in paragraphs
                if p.strip()
            )

            # Send test email first if requested
            if form.send_test.data and form.test_email.data:
                test_email = form.test_email.data.strip()
                try:
                    msg = EmailMessage(
                        subject=f"[TEST] {subject}",
                        sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                        recipients=[test_email],
                    )
                    msg.html = render_template(
                        "emails/bulk_notification.html",
                        subject=subject,
                        recipient_name="Test Recipient",
                        recipient_email=test_email,
                        message_html=message_html,
                    )
                    msg.body = render_template(
                        "emails/bulk_notification.txt",
                        subject=subject,
                        recipient_name="Test Recipient",
                        recipient_email=test_email,
                        message_text=message_text,
                    )
                    mail.send(msg)
                    flash(f"Test email sent to {test_email}. Review it before sending to all {len(recipients)} recipients.", "success")
                except Exception as e:
                    logger.error(f"Test email failed: {str(e)}")
                    flash(f"Test email failed: {str(e)}", "error")
                return render_template("admin/communications/bulk.html", form=form)

            # Confirmation step — require explicit confirm parameter
            if not request.form.get("confirmed"):
                return render_template(
                    "admin/communications/bulk.html",
                    form=form,
                    confirm_send=True,
                    recipient_count=len(recipients),
                    recipient_type_label=dict(form.recipient_type.choices).get(recipient_type, recipient_type),
                )

            # Send bulk emails
            sent_count = 0
            fail_count = 0

            for recipient in recipients:
                try:
                    name = recipient.computed_full_name
                    email = recipient.email

                    msg = EmailMessage(
                        subject=subject,
                        sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                        recipients=[email],
                    )
                    msg.html = render_template(
                        "emails/bulk_notification.html",
                        subject=subject,
                        recipient_name=name,
                        recipient_email=email,
                        message_html=message_html,
                    )
                    msg.body = render_template(
                        "emails/bulk_notification.txt",
                        subject=subject,
                        recipient_name=name,
                        recipient_email=email,
                        message_text=message_text,
                    )
                    mail.send(msg)

                    EmailLog.log(
                        recipient_email=email,
                        recipient_name=name,
                        subject=subject,
                        email_type="bulk",
                        registration_id=recipient.id,
                        template_name="bulk_notification",
                    )
                    sent_count += 1

                except Exception as e:
                    fail_count += 1
                    logger.error(f"Bulk email failed for {recipient.email}: {str(e)}")
                    EmailLog.log(
                        recipient_email=recipient.email,
                        recipient_name=recipient.computed_full_name,
                        subject=subject,
                        email_type="bulk",
                        registration_id=recipient.id,
                        template_name="bulk_notification",
                        status="failed",
                        error_message=str(e),
                    )

            flash(
                f"Bulk email sent to {sent_count} recipients."
                + (f" {fail_count} failed." if fail_count else ""),
                "success" if fail_count == 0 else "warning",
            )
            logger.info(
                f"Bulk email sent by {current_user.name}: {sent_count} sent, {fail_count} failed ({recipient_type})"
            )

            return redirect(url_for("admin.email_logs"))

        except Exception as e:
            logger.error(f"Error sending bulk email: {str(e)}")
            flash("Could not send bulk email. Please check email settings and try again.", "error")

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
        pagination=messages,
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

            from app.extensions import mail

            msg = EmailMessage(
                subject=f"Re: {message.subject}",
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                recipients=[message.email],
                reply_to=current_app.config.get("CONTACT_EMAIL", "info@beeseasy.org"),
            )

            reply_text = form.reply_message.data

            # Create email context
            email_context = {
                "message": message,
                "response": reply_text,
                "admin_name": current_user.name,
                "reference_number": message.reference_number,
            }

            msg.html = render_template("emails/contact_response.html", **email_context)
            msg.body = f"""
Dear {message.first_name},

Thank you for contacting us regarding "{message.subject}".

{reply_text}

Reference Number: {message.reference_number}

Best regards,
{current_user.name}
Pollination Africa Summit Team

---
This is a response to your inquiry submitted on {message.submitted_at.strftime("%B %d, %Y")}
            """

            mail.send(msg)

            EmailLog.log(
                recipient_email=message.email,
                recipient_name=f"{message.first_name} {message.last_name}",
                subject=f"Re: {message.subject}",
                email_type="contact_response",
                template_name="contact_response",
            )

            # Update message status
            message.mark_as_resolved(
                resolved_by=current_user.name,
                response_message=reply_text,
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
            flash("Could not send the response. Please check email settings and try again.", "error")

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
        flash("Could not assign the message. Please try again.", "error")

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
        flash("Could not update the priority. Please try again.", "error")

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
        flash("Could not delete the message. Please try again.", "error")
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

    # Total revenue by currency
    total_by_currency = (
        db.session.query(
            Payment.currency,
            func.sum(Payment.total_amount),
        )
        .filter(Payment.payment_status == PaymentStatus.COMPLETED)
        .group_by(Payment.currency)
        .all()
    )

    # By payment method (with currency)
    method_breakdown = (
        db.session.query(
            Payment.payment_method,
            Payment.currency,
            func.sum(Payment.total_amount),
            func.count(Payment.id),
        )
        .filter(Payment.payment_status == PaymentStatus.COMPLETED)
        .group_by(Payment.payment_method, Payment.currency)
        .all()
    )

    # By registration type (with currency)
    type_revenue = (
        db.session.query(
            Registration.registration_type,
            Payment.currency,
            func.sum(Payment.total_amount),
        )
        .join(Payment)
        .filter(Payment.payment_status == PaymentStatus.COMPLETED)
        .group_by(Registration.registration_type, Payment.currency)
        .all()
    )

    # Revenue over time (with currency)
    daily_revenue = (
        db.session.query(
            func.date(Payment.payment_completed_at).label("date"),
            Payment.currency,
            func.sum(Payment.total_amount).label("revenue"),
        )
        .filter(Payment.payment_status == PaymentStatus.COMPLETED)
        .group_by(func.date(Payment.payment_completed_at), Payment.currency)
        .order_by(func.date(Payment.payment_completed_at))
        .all()
    )

    return render_template(
        "admin/reports/revenue.html",
        total_by_currency=total_by_currency,
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

            import secrets

            plain_password = form.password.data or secrets.token_urlsafe(12)
            user.set_password(plain_password)

            db.session.add(user)
            db.session.commit()

            # Email credentials to the new user
            try:
                from flask_mail import Message as EmailMessage

                login_url = url_for("auth.login", _external=True)
                html_body = render_template(
                    "emails/account_credentials.html",
                    user=user,
                    password=plain_password,
                    login_url=login_url,
                )
                msg = EmailMessage(
                    subject="Your Account Credentials - Pollination Africa Summit",
                    recipients=[user.email],
                    html=html_body,
                )
                mail = current_app.extensions["mail"]
                mail.send(msg)

                EmailLog.log(
                    recipient_email=user.email,
                    recipient_name=user.name,
                    subject=msg.subject,
                    email_type="account_credentials",
                    template_name="account_credentials",
                    status="sent",
                )
                flash("User created. Login credentials sent to their email.", "success")
            except Exception as mail_err:
                logger.error(f"Failed to email credentials to {user.email}: {mail_err}")
                flash(
                    "User created but failed to send credentials email. "
                    f"Temporary password: {plain_password}",
                    "warning",
                )

            return redirect(url_for("admin.list_users"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            flash("Could not create the user. The email may already be in use.", "error")

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
            flash("Could not update the user. Please try again.", "error")

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
        flash("Could not update the user status. Please try again.", "error")

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
            flash("Could not add the exchange rate. Please try again.", "error")

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
            flash("Could not update the promo code. Please try again.", "error")

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
        flash("Could not update the promo code status. Please try again.", "error")

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
