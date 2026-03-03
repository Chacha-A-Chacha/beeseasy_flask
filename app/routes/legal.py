"""
Legal pages routes — Terms & Conditions and Refund Policy.
"""

from flask import Blueprint, render_template

legal_bp = Blueprint("legal", __name__)


@legal_bp.route("/terms")
def terms():
    """Terms & Conditions page."""
    return render_template("legal/terms.html")


@legal_bp.route("/refund-policy")
def refund_policy():
    """Refund & Cancellation Policy page."""
    return render_template("legal/refund_policy.html")
