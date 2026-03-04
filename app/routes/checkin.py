"""
Check-in Portal routes for event staff and organizers.
Provides a mobile-first interface for checking in attendees and exhibitors.
"""

import logging
from datetime import date, datetime
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app.extensions import db
from app.models import (
    AttendeeRegistration,
    ExhibitorRegistration,
    Registration,
    RegistrationStatus,
    UserRole,
)
from app.models.registration import DailyCheckIn
from app.services.badge_service import BadgeService

logger = logging.getLogger(__name__)

checkin_bp = Blueprint("checkin", __name__, url_prefix="/checkin")


# ============================================
# DECORATOR
# ============================================
def checkin_required(f):
    """Require check-in portal access (admin, staff, or organizer)."""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in [
            UserRole.ADMIN,
            UserRole.STAFF,
            UserRole.ORGANIZER,
        ]:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


# ============================================
# HELPERS
# ============================================
def get_checkin_stats():
    """Get today's check-in statistics."""
    today = date.today()

    total_confirmed_attendees = AttendeeRegistration.query.filter_by(
        status=RegistrationStatus.CONFIRMED, is_deleted=False
    ).count()

    checked_in_attendees = (
        db.session.query(func.count(func.distinct(DailyCheckIn.registration_id)))
        .join(
            AttendeeRegistration,
            DailyCheckIn.registration_id == AttendeeRegistration.id,
        )
        .filter(
            AttendeeRegistration.is_deleted == False,
            DailyCheckIn.event_date == today,
        )
        .scalar()
        or 0
    )

    total_confirmed_exhibitors = ExhibitorRegistration.query.filter_by(
        status=RegistrationStatus.CONFIRMED, is_deleted=False
    ).count()

    checked_in_exhibitors = (
        db.session.query(func.count(func.distinct(DailyCheckIn.registration_id)))
        .join(
            ExhibitorRegistration,
            DailyCheckIn.registration_id == ExhibitorRegistration.id,
        )
        .filter(
            ExhibitorRegistration.is_deleted == False,
            DailyCheckIn.event_date == today,
        )
        .scalar()
        or 0
    )

    return {
        "total_confirmed_attendees": total_confirmed_attendees,
        "checked_in_attendees": checked_in_attendees,
        "total_confirmed_exhibitors": total_confirmed_exhibitors,
        "checked_in_exhibitors": checked_in_exhibitors,
        "total_checked_in": checked_in_attendees + checked_in_exhibitors,
        "total_expected": total_confirmed_attendees + total_confirmed_exhibitors,
    }


def get_recent_checkins(limit=10):
    """Get recent check-ins for today."""
    today = date.today()

    recent = (
        db.session.query(DailyCheckIn, Registration)
        .join(Registration, DailyCheckIn.registration_id == Registration.id)
        .filter(
            DailyCheckIn.event_date == today,
            Registration.is_deleted == False,
        )
        .order_by(DailyCheckIn.checked_in_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for checkin, registration in recent:
        reg_type = (
            "Attendee"
            if isinstance(registration, AttendeeRegistration)
            else "Exhibitor"
        )
        results.append(
            {
                "id": registration.id,
                "name": registration.computed_full_name,
                "type": reg_type,
                "reference": registration.reference_number,
                "time": checkin.checked_in_at.strftime("%I:%M %p"),
                "checked_in_by": checkin.checked_in_by or "-",
            }
        )

    return results


# ============================================
# PAGES
# ============================================
@checkin_bp.route("/")
@checkin_required
def dashboard():
    """Check-in portal dashboard with today's stats."""
    stats = get_checkin_stats()
    recent = get_recent_checkins(5)

    return render_template(
        "checkin/dashboard.html",
        stats=stats,
        recent_checkins=recent,
    )


@checkin_bp.route("/scan", methods=["GET", "POST"])
@checkin_required
def scan():
    """QR scanner and manual reference entry page."""
    result = None

    if request.method == "POST":
        reference = request.form.get("reference_number", "").strip()
        if reference:
            result = process_checkin(reference)

    stats = get_checkin_stats()
    return render_template("checkin/scan.html", result=result, stats=stats)


@checkin_bp.route("/search")
@checkin_required
def search():
    """Search page for looking up attendees and exhibitors."""
    return render_template("checkin/search.html")


@checkin_bp.route("/history")
@checkin_required
def history():
    """Today's check-in history log."""
    today = date.today()
    filter_type = request.args.get("type", "all")

    query = (
        db.session.query(DailyCheckIn, Registration)
        .join(Registration, DailyCheckIn.registration_id == Registration.id)
        .filter(
            DailyCheckIn.event_date == today,
            Registration.is_deleted == False,
        )
    )

    if filter_type == "attendees":
        query = query.filter(
            Registration.id.in_(
                db.session.query(AttendeeRegistration.id)
            )
        )
    elif filter_type == "exhibitors":
        query = query.filter(
            Registration.id.in_(
                db.session.query(ExhibitorRegistration.id)
            )
        )

    checkins = query.order_by(DailyCheckIn.checked_in_at.desc()).all()

    entries = []
    for checkin, registration in checkins:
        reg_type = (
            "Attendee"
            if isinstance(registration, AttendeeRegistration)
            else "Exhibitor"
        )
        entries.append(
            {
                "id": registration.id,
                "name": registration.computed_full_name,
                "type": reg_type,
                "reference": registration.reference_number,
                "time": checkin.checked_in_at.strftime("%I:%M %p"),
                "checked_in_by": checkin.checked_in_by or "-",
                "method": checkin.check_in_method or "manual",
            }
        )

    stats = get_checkin_stats()
    return render_template(
        "checkin/history.html",
        entries=entries,
        filter_type=filter_type,
        stats=stats,
    )


@checkin_bp.route("/registration/<int:id>")
@checkin_required
def registration_detail(id):
    """View a single registration's details."""
    registration = Registration.query.filter_by(
        id=id, is_deleted=False
    ).first_or_404()

    today = date.today()
    is_checked_in_today = registration.is_checked_in_for_day(today)
    reg_type = (
        "Attendee"
        if isinstance(registration, AttendeeRegistration)
        else "Exhibitor"
    )

    return render_template(
        "checkin/registration.html",
        registration=registration,
        reg_type=reg_type,
        is_checked_in_today=is_checked_in_today,
    )


# ============================================
# API ENDPOINTS
# ============================================
def process_checkin(reference_or_qr):
    """Process a check-in by reference number or QR data. Returns result dict."""
    today = date.today()

    # Try QR code format first
    if reference_or_qr.startswith(("POLLINATION", "BEEASY")):
        valid, message, registration = BadgeService.verify_qr_code(reference_or_qr)
        if not valid:
            return {"success": False, "message": message}
    else:
        # Try as reference number
        registration = Registration.query.filter_by(
            reference_number=reference_or_qr, is_deleted=False
        ).first()

        if not registration:
            return {
                "success": False,
                "message": "Registration not found with that reference number.",
            }

    # Check if already checked in today
    if registration.is_checked_in_for_day(today):
        reg_type = (
            "Attendee"
            if isinstance(registration, AttendeeRegistration)
            else "Exhibitor"
        )
        return {
            "success": False,
            "already_checked_in": True,
            "message": f"{registration.computed_full_name} is already checked in for today.",
            "registration": {
                "id": registration.id,
                "name": registration.computed_full_name,
                "type": reg_type,
                "reference": registration.reference_number,
            },
        }

    # Perform check-in
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

    return {
        "success": True,
        "message": f"{registration.computed_full_name} checked in successfully!",
        "registration": {
            "id": registration.id,
            "name": registration.computed_full_name,
            "type": reg_type,
            "reference": registration.reference_number,
            "organization": getattr(registration, "organization", None)
            or getattr(registration, "company_name", None)
            or "",
        },
    }


@checkin_bp.route("/api/scan", methods=["POST"])
@checkin_required
def api_scan():
    """AJAX endpoint for QR scan or reference number check-in."""
    data = request.get_json(silent=True) or {}
    qr_data = data.get("qr_data", "").strip()
    reference = data.get("reference", "").strip()

    input_value = qr_data or reference
    if not input_value:
        return jsonify({"success": False, "message": "No reference provided."}), 400

    result = process_checkin(input_value)
    status_code = 200 if result["success"] or result.get("already_checked_in") else 404
    return jsonify(result), status_code


@checkin_bp.route("/api/checkin/<int:id>", methods=["POST"])
@checkin_required
def api_checkin_by_id(id):
    """AJAX endpoint to check in a registration by ID."""
    registration = Registration.query.filter_by(
        id=id, is_deleted=False
    ).first()

    if not registration:
        return jsonify({"success": False, "message": "Registration not found."}), 404

    today = date.today()
    if registration.is_checked_in_for_day(today):
        return jsonify(
            {
                "success": False,
                "already_checked_in": True,
                "message": f"{registration.computed_full_name} is already checked in for today.",
            }
        )

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

    return jsonify(
        {
            "success": True,
            "message": f"{registration.computed_full_name} checked in successfully!",
            "registration": {
                "id": registration.id,
                "name": registration.computed_full_name,
                "type": reg_type,
            },
        }
    )


@checkin_bp.route("/api/search")
@checkin_required
def api_search():
    """AJAX endpoint for searching registrations."""
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify({"results": []})

    today = date.today()
    search_term = f"%{q}%"

    # Search attendees
    attendees = (
        AttendeeRegistration.query.filter(
            AttendeeRegistration.is_deleted == False,
            AttendeeRegistration.status == RegistrationStatus.CONFIRMED,
            or_(
                AttendeeRegistration.first_name.ilike(search_term),
                AttendeeRegistration.last_name.ilike(search_term),
                AttendeeRegistration.email.ilike(search_term),
                AttendeeRegistration.reference_number.ilike(search_term),
            ),
        )
        .limit(10)
        .all()
    )

    # Search exhibitors
    exhibitors = (
        ExhibitorRegistration.query.filter(
            ExhibitorRegistration.is_deleted == False,
            ExhibitorRegistration.status == RegistrationStatus.CONFIRMED,
            or_(
                ExhibitorRegistration.first_name.ilike(search_term),
                ExhibitorRegistration.last_name.ilike(search_term),
                ExhibitorRegistration.email.ilike(search_term),
                ExhibitorRegistration.reference_number.ilike(search_term),
                ExhibitorRegistration.organization.ilike(search_term),
            ),
        )
        .limit(10)
        .all()
    )

    results = []
    for a in attendees:
        results.append(
            {
                "id": a.id,
                "name": a.computed_full_name,
                "email": a.email,
                "type": "Attendee",
                "reference": a.reference_number,
                "organization": getattr(a, "organization", "") or "",
                "checked_in": a.is_checked_in_for_day(today),
            }
        )

    for e in exhibitors:
        results.append(
            {
                "id": e.id,
                "name": e.computed_full_name,
                "email": e.email,
                "type": "Exhibitor",
                "reference": e.reference_number,
                "organization": e.organization or "",
                "checked_in": e.is_checked_in_for_day(today),
            }
        )

    return jsonify({"results": results})


@checkin_bp.route("/api/stats")
@checkin_required
def api_stats():
    """AJAX endpoint for live stat updates."""
    return jsonify(get_checkin_stats())
