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

from app.extensions import db
from app.forms import ContactForm
from app.models import Registration  # maybe for stats
from app.services.contact_service import ContactService

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    # You might want to pass featured speakers, news, etc. to home
    # e.g., latest news posts, top speakers
    return render_template("index.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/speakers")
def speakers():
    # Pass a list of speakers from DB (or stub) to template
    return render_template("speakers.html")


@main_bp.route("/partners")
def partners():
    # Pass a list of speakers from DB (or stub) to template
    return render_template("partners.html")


@main_bp.route("/agenda")
def agenda():
    return render_template("agenda.html")


@main_bp.route("/news")
def news():
    # List of news posts (title, excerpt, link)
    return render_template("news.html")


@main_bp.route("/news/<slug>")
def news_detail(slug):
    # Fetch single news post by slug; if missing, 404
    # e.g. post = News.query.filter_by(slug=slug).first_or_404()
    return render_template("news_detail.html")


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    """Enhanced contact page with intelligent routing"""
    form = ContactForm()

    if form.validate_on_submit():
        # Collect form data
        form_data = {
            "first_name": form.first_name.data.strip(),
            "last_name": form.last_name.data.strip(),
            "email": form.email.data.strip().lower(),
            "country_code": form.country_code.data,
            "phone": form.phone.data.strip() if form.phone.data else None,
            "inquiry_type": form.inquiry_type.data,
            "subject": form.subject.data.strip(),
            "organization": form.organization.data.strip()
            if form.organization.data
            else None,
            "role": form.role.data.strip() if form.role.data else None,
            "message": form.message.data.strip(),
            "preferred_contact_method": form.preferred_contact_method.data,
            "newsletter_signup": form.newsletter_signup.data,
            "privacy_consent": form.privacy_consent.data,
        }

        # Send the message
        success, message, reference = ContactService.send_contact_message(form_data)

        if success:
            flash(f"{message}", "success")

            # If AJAX request, return JSON
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(
                    {"success": True, "message": message, "reference": reference}
                )

            return redirect(url_for("main.contact"))
        else:
            flash(message, "error")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "message": message}), 400

    elif request.method == "POST":
        # Form validation failed
        flash("Please correct the errors below and try again.", "error")


@main_bp.route("/become-exhibitor")
def become_exhibitor():
    # Explanation, benefits, link to exhibitor registration form
    return render_template("become_exhibitor.html")


@main_bp.route("/badge/download/<reference>")
def download_badge(reference):
    """
    Download event badge PDF by registration reference number

    Args:
        reference: Registration reference number (e.g., ATT-2025-XXXXX or EXH-2025-XXXXX)

    Returns:
        PDF file download or 404 if not found
    """
    # Find registration by reference number
    registration = Registration.query.filter_by(
        reference_number=reference, is_deleted=False
    ).first()

    if not registration:
        abort(404, description="Registration not found")

    # Check if badge has been generated
    if not registration.qr_code_image_url:
        abort(
            404, description="Badge not yet generated. Please complete payment first."
        )

    # Build the file path from the badge URL
    # Badge URL format: /storage/badges/2025/attendee|media|exhibitor/ATT-2025-XXXXX.pdf
    badge_url = registration.qr_code_image_url

    # Remove leading slash and convert to Path
    relative_path = badge_url.lstrip("/")
    badge_path = Path(current_app.root_path) / relative_path

    # Verify file exists
    if not badge_path.exists():
        abort(404, description="Badge file not found. Please contact support.")

    # Determine the download filename
    download_name = f"{registration.reference_number}_badge.pdf"

    # Send file for download
    return send_file(
        badge_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )
