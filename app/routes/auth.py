"""
Authentication routes for Bee East Africa Symposium.
Handles login, logout, password management, and session utilities.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, session, current_app
)
from flask_login import login_required, logout_user, current_user
from urllib.parse import urlparse, urljoin
from app.extensions import db
from app.services.auth_service import AuthService
from app.forms.auth_forms import LoginForm, PasswordResetForm, PasswordResetRequestForm, PasswordChangeForm

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')

# --- Utilities ---
def is_safe_url(target: str) -> bool:
    """Ensure redirects stay within same host."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


# --- Login ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route for all roles."""
    if current_user.is_authenticated:
        # redirect based on role
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'exhibitor':
            return redirect(url_for('exhibitor.dashboard'))
        else:
            return redirect(url_for('attendee.dashboard'))

    form = LoginForm()
    next_url = request.args.get('next', '/')
    form.next_url.data = next_url

    if form.validate_on_submit():
        email = form.email.data.strip()
        password = form.password.data
        remember = form.remember_me.data

        success, user, message = AuthService.authenticate(email=email, password=password, remember=remember)

        if success:
            flash('Login successful.', 'success')

            if form.next_url.data and is_safe_url(form.next_url.data):
                return redirect(form.next_url.data)

            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'exhibitor':
                return redirect(url_for('exhibitor.dashboard'))
            else:
                return redirect(url_for('attendee.dashboard'))
        else:
            flash(message, 'error')

    return render_template('auth/login.html', form=form, next_url=next_url)


# --- Logout ---
@auth_bp.route('/logout')
@login_required
def logout():
    """Logout and clear session."""
    AuthService.logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


# --- Password Reset Request ---
@auth_bp.route('/password-reset', methods=['GET', 'POST'])
def password_reset_request():
    """Password reset initiation."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        email = form.email.data.strip()
        success, message = AuthService.initiate_reset(email)
        flash(message, 'info' if success else 'error')
        if success:
            return redirect(url_for('auth.password_reset_sent'))

    return render_template('auth/password_reset_request.html', form=form)


@auth_bp.route('/password-reset/sent')
def password_reset_sent():
    """Show confirmation message after reset request."""
    return render_template('auth/password_reset_sent.html')


@auth_bp.route('/password-reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    """Complete reset via token."""
    valid, user, message = AuthService.verify_token(token)
    if not valid:
        flash(message, 'error')
        return redirect(url_for('auth.password_reset_request'))

    form = PasswordResetForm()
    if form.validate_on_submit():
        success, message = AuthService.reset_password(user=user, new_password=form.password.data)
        flash(message, 'success' if success else 'error')
        if success:
            return redirect(url_for('auth.login'))
    return render_template('auth/password_reset.html', form=form)


# --- Password Change ---
@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Authenticated user password change."""
    form = PasswordChangeForm()
    if form.validate_on_submit():
        success, message = AuthService.change_password(
            user=current_user,
            current=form.current_password.data,
            new=form.new_password.data
        )
        flash(message, 'success' if success else 'error')
        return redirect(url_for('auth.change_password'))
    return render_template('auth/change_password.html', form=form)


# --- Session & Status (AJAX) ---
@auth_bp.route('/session-check', methods=['GET'])
def session_check():
    """Check session validity (AJAX)."""
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'role': current_user.role})
    return jsonify({'authenticated': False}), 401


@auth_bp.route('/extend-session', methods=['POST'])
@login_required
def extend_session():
    """Extend current session (AJAX)."""
    session.permanent = True
    return jsonify({'success': True, 'message': 'Session extended'})


# --- Context Processor ---
@auth_bp.context_processor
def inject_auth_context():
    """Inject shared vars for auth templates."""
    return dict(
        site_name=current_app.config.get('SITE_NAME', 'Bee East Africa Symposium'),
        contact_email=current_app.config.get('CONTACT_EMAIL', 'info@beeseasy.org'),
        password_min_length=8
    )
