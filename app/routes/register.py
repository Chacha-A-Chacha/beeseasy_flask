# routes/register.py
from flask import Blueprint, render_template, request, redirect, flash, url_for
# from app.forms import AttendeeRegistrationForm, ExhibitorRegistrationForm
from app.services.registration_service import RegistrationService

register_bp = Blueprint("register", __name__)

@register_bp.route("/register/attendee", methods=["GET", "POST"])
def register_attendee():
    form = AttendeeRegistrationForm()
    if form.validate_on_submit():
        success, message, reg = RegistrationService.register_attendee(form.data)
        flash(message, 'success' if success else 'error')
        if success:
            return redirect(url_for('main.thank_you'))
    return render_template("register/attendee.html", form=form)

@register_bp.route("/register/exhibitor", methods=["GET", "POST"])
def register_exhibitor():
    form = ExhibitorRegistrationForm()
    if form.validate_on_submit():
        success, message, reg = RegistrationService.register_exhibitor(form.data)
        flash(message, 'success' if success else 'error')
        if success:
            return redirect(url_for('main.thank_you'))
    return render_template("register/exhibitor.html", form=form)
