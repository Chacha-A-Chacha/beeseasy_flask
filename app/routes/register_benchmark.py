"""
Enhanced registration routes for BEEASY2025
Supports single-page and multi-page forms with AJAX validation
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, jsonify, current_app
)
from app.forms import (
    AttendeeRegistrationForm,
    ExhibitorRegistrationForm,
    PromoCodeForm
)
from app.services.registration_service import RegistrationService
from app.models import (
    Registration, TicketPrice, ExhibitorPackagePrice,
    AttendeeTicketType, ExhibitorPackage
)
from app.models import PromoCode
from app.extensions import db
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

register_bp = Blueprint('register', __name__)


# ============================================
# LANDING / SELECTION
# ============================================

@register_bp.route('/')
def index():
    """Registration type selection page"""
    return render_template('register/index.html')


# ============================================
# ATTENDEE REGISTRATION - SINGLE PAGE
# ============================================

@register_bp.route('/attendee', methods=['GET', 'POST'])
def register_attendee():
    """Single-page attendee registration"""
    form = AttendeeRegistrationForm()

    # Get available tickets for display
    tickets = TicketPrice.query.filter_by(is_active=True).all()

    if form.validate_on_submit():
        # Clear any existing multi-step session data
        session.pop('attendee_step1', None)
        session.pop('attendee_step2', None)

        # Register attendee
        success, message, attendee = RegistrationService.register_attendee(form.data)

        if success:
            flash(message, 'success')
            # Store reference in session for payment
            session['registration_ref'] = attendee.reference_number

            # Redirect to payment if needed
            if attendee.get_balance_due() > 0:
                return redirect(url_for('payments.checkout', ref=attendee.reference_number))
            else:
                return redirect(url_for('register.confirmation', ref=attendee.reference_number))
        else:
            flash(message, 'error')

    return render_template('register/attendee.html', form=form, tickets=tickets)


# ============================================
# ATTENDEE REGISTRATION - MULTI-STEP
# ============================================

@register_bp.route('/attendee/step1', methods=['GET', 'POST'])
def attendee_step1():
    """Step 1: Basic info and ticket selection"""
    form = AttendeeRegistrationForm()

    if request.method == 'POST' and form.validate():
        # Store step 1 data in session
        session['attendee_step1'] = {
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone_country_code': form.phone_country_code.data,
            'phone_number': form.phone_number.data,
            'ticket_type': form.ticket_type.data,
        }
        return redirect(url_for('register.attendee_step2'))

    # Pre-populate from session if exists
    if 'attendee_step1' in session:
        for key, value in session['attendee_step1'].items():
            if hasattr(form, key):
                getattr(form, key).data = value

    tickets = TicketPrice.query.filter_by(is_active=True).all()
    return render_template('register/attendee_step1.html', form=form, tickets=tickets)


@register_bp.route('/attendee/step2', methods=['GET', 'POST'])
def attendee_step2():
    """Step 2: Professional info and preferences"""
    # Redirect to step 1 if no data
    if 'attendee_step1' not in session:
        return redirect(url_for('register.attendee_step1'))

    form = AttendeeRegistrationForm()

    if request.method == 'POST' and form.validate():
        # Store step 2 data
        session['attendee_step2'] = {
            'organization': form.organization.data,
            'job_title': form.job_title.data,
            'professional_category': form.professional_category.data,
            'years_in_beekeeping': form.years_in_beekeeping.data,
            'session_interests': form.session_interests.data,
            'networking_goals': form.networking_goals.data,
            'dietary_requirement': form.dietary_requirement.data,
            'dietary_notes': form.dietary_notes.data,
        }
        return redirect(url_for('register.attendee_step3'))

    # Pre-populate
    if 'attendee_step2' in session:
        for key, value in session['attendee_step2'].items():
            if hasattr(form, key):
                getattr(form, key).data = value

    return render_template('register/attendee_step2.html', form=form)


@register_bp.route('/attendee/step3', methods=['GET', 'POST'])
def attendee_step3():
    """Step 3: Review and submit"""
    # Redirect if missing data
    if 'attendee_step1' not in session or 'attendee_step2' not in session:
        return redirect(url_for('register.attendee_step1'))

    form = AttendeeRegistrationForm()

    if request.method == 'POST':
        # Combine all session data
        registration_data = {**session.get('attendee_step1', {}), **session.get('attendee_step2', {})}

        # Add step 3 data (promo code, consent)
        registration_data.update({
            'promo_code': form.promo_code.data,
            'consent_photography': form.consent_photography.data,
            'consent_networking': form.consent_networking.data,
            'consent_data_sharing': form.consent_data_sharing.data,
            'newsletter_signup': form.newsletter_signup.data,
            'referral_source': form.referral_source.data,
        })

        # Register
        success, message, attendee = RegistrationService.register_attendee(registration_data)

        if success:
            # Clear session data
            session.pop('attendee_step1', None)
            session.pop('attendee_step2', None)

            flash(message, 'success')
            session['registration_ref'] = attendee.reference_number

            if attendee.get_balance_due() > 0:
                return redirect(url_for('payments.checkout', ref=attendee.reference_number))
            else:
                return redirect(url_for('register.confirmation', ref=attendee.reference_number))
        else:
            flash(message, 'error')

    # Get summary data for display
    step1 = session.get('attendee_step1', {})
    step2 = session.get('attendee_step2', {})

    return render_template('register/attendee_step3.html',
                           form=form, step1=step1, step2=step2)


# ============================================
# EXHIBITOR REGISTRATION - SINGLE PAGE
# ============================================

@register_bp.route('/exhibitor', methods=['GET', 'POST'])
def register_exhibitor():
    """Single-page exhibitor registration"""
    form = ExhibitorRegistrationForm()

    # Get available packages
    packages = ExhibitorPackagePrice.query.filter_by(is_active=True).all()

    if form.validate_on_submit():
        # Clear any multi-step session data
        session.pop('exhibitor_step1', None)
        session.pop('exhibitor_step2', None)
        session.pop('exhibitor_step3', None)

        # Register exhibitor
        success, message, exhibitor = RegistrationService.register_exhibitor(form.data)

        if success:
            flash(message, 'success')
            session['registration_ref'] = exhibitor.reference_number

            # Redirect to payment
            return redirect(url_for('payments.checkout', ref=exhibitor.reference_number))
        else:
            flash(message, 'error')

    return render_template('register/exhibitor.html', form=form, packages=packages)


# ============================================
# EXHIBITOR REGISTRATION - MULTI-STEP
# ============================================

@register_bp.route('/exhibitor/step1', methods=['GET', 'POST'])
def exhibitor_step1():
    """Step 1: Contact and company info"""
    form = ExhibitorRegistrationForm()

    if request.method == 'POST' and form.validate():
        session['exhibitor_step1'] = {
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone_country_code': form.phone_country_code.data,
            'phone_number': form.phone_number.data,
            'job_title': form.job_title.data,
            'company_legal_name': form.company_legal_name.data,
            'company_country': form.company_country.data,
            'company_address': form.company_address.data,
            'company_website': form.company_website.data,
            'company_email': form.company_email.data,
            'industry_category': form.industry_category.data,
            'company_description': form.company_description.data,
        }
        return redirect(url_for('register.exhibitor_step2'))

    # Pre-populate
    if 'exhibitor_step1' in session:
        for key, value in session['exhibitor_step1'].items():
            if hasattr(form, key):
                getattr(form, key).data = value

    return render_template('register/exhibitor_step1.html', form=form)


@register_bp.route('/exhibitor/step2', methods=['GET', 'POST'])
def exhibitor_step2():
    """Step 2: Package selection and booth preferences"""
    if 'exhibitor_step1' not in session:
        return redirect(url_for('register.exhibitor_step1'))

    form = ExhibitorRegistrationForm()
    packages = ExhibitorPackagePrice.query.filter_by(is_active=True).all()

    if request.method == 'POST' and form.validate():
        session['exhibitor_step2'] = {
            'package_type': form.package_type.data,
            'booth_preference_corner': form.booth_preference_corner.data,
            'booth_preference_entrance': form.booth_preference_entrance.data,
            'booth_preference_area': form.booth_preference_area.data,
            'number_of_staff': form.number_of_staff.data,
            'exhibitor_badges_needed': form.exhibitor_badges_needed.data,
            'electricity_required': form.electricity_required.data,
            'electricity_watts': form.electricity_watts.data,
            'internet_required': form.internet_required.data,
            'special_requirements': form.special_requirements.data,
        }
        return redirect(url_for('register.exhibitor_step3'))

    # Pre-populate
    if 'exhibitor_step2' in session:
        for key, value in session['exhibitor_step2'].items():
            if hasattr(form, key):
                getattr(form, key).data = value

    return render_template('register/exhibitor_step2.html',
                           form=form, packages=packages)


@register_bp.route('/exhibitor/step3', methods=['GET', 'POST'])
def exhibitor_step3():
    """Step 3: Review and submit"""
    if 'exhibitor_step1' not in session or 'exhibitor_step2' not in session:
        return redirect(url_for('register.exhibitor_step1'))

    form = ExhibitorRegistrationForm()

    if request.method == 'POST':
        # Combine all data
        registration_data = {
            **session.get('exhibitor_step1', {}),
            **session.get('exhibitor_step2', {})
        }

        # Add step 3 data
        registration_data.update({
            'billing_address': form.billing_address.data,
            'tax_id': form.tax_id.data,
            'payment_terms': form.payment_terms.data,
            'linkedin_url': form.linkedin_url.data,
            'facebook_url': form.facebook_url.data,
            'twitter_handle': form.twitter_handle.data,
            'has_liability_insurance': form.has_liability_insurance.data,
            'insurance_policy_number': form.insurance_policy_number.data,
            'products_comply_regulations': form.products_comply_regulations.data,
            'promo_code': form.promo_code.data,
            'consent_photography': form.consent_photography.data,
            'consent_catalog': form.consent_catalog.data,
            'newsletter_signup': form.newsletter_signup.data,
        })

        # Register
        success, message, exhibitor = RegistrationService.register_exhibitor(registration_data)

        if success:
            # Clear session
            session.pop('exhibitor_step1', None)
            session.pop('exhibitor_step2', None)
            session.pop('exhibitor_step3', None)

            flash(message, 'success')
            session['registration_ref'] = exhibitor.reference_number

            return redirect(url_for('payments.checkout', ref=exhibitor.reference_number))
        else:
            flash(message, 'error')

    # Summary data
    step1 = session.get('exhibitor_step1', {})
    step2 = session.get('exhibitor_step2', {})

    return render_template('register/exhibitor_step3.html',
                           form=form, step1=step1, step2=step2)


# ============================================
# CONFIRMATION PAGE
# ============================================

@register_bp.route('/confirmation/<ref>')
def confirmation(ref):
    """Registration confirmation page"""
    registration = Registration.query.filter_by(
        reference_number=ref,
        is_deleted=False
    ).first_or_404()

    return render_template('register/confirmation.html', registration=registration)


# ============================================
# AJAX ENDPOINTS
# ============================================

@register_bp.route('/api/validate-email', methods=['POST'])
def validate_email():
    """AJAX endpoint to check email availability"""
    email = request.json.get('email', '').lower()
    registration_type = request.json.get('type', 'attendee')

    if not email:
        return jsonify({'valid': False, 'message': 'Email is required'})

    existing = Registration.query.filter(
        db.func.lower(Registration.email) == email,
        Registration.registration_type == registration_type,
        Registration.is_deleted == False
    ).first()

    if existing:
        return jsonify({
            'valid': False,
            'message': f'This email is already registered as {registration_type}'
        })

    return jsonify({'valid': True, 'message': 'Email available'})


@register_bp.route('/api/validate-promo', methods=['POST'])
def validate_promo():
    """AJAX endpoint to validate promo code"""
    code = request.json.get('code', '').upper()
    email = request.json.get('email', '').lower()
    registration_type = request.json.get('type', 'attendee')

    if not code:
        return jsonify({'valid': False, 'message': 'Promo code is required'})

    promo = PromoCode.query.filter_by(code=code).first()

    if not promo:
        return jsonify({'valid': False, 'message': 'Invalid promo code'})

    if not promo.is_valid():
        return jsonify({'valid': False, 'message': 'Promo code is expired or inactive'})

    if email and not promo.is_valid_for_user(email):
        return jsonify({'valid': False, 'message': 'You have already used this promo code'})

    # Check applicability
    if registration_type == 'attendee' and not promo.applicable_to_attendees:
        return jsonify({'valid': False, 'message': 'This code is not valid for attendees'})

    if registration_type == 'exhibitor' and not promo.applicable_to_exhibitors:
        return jsonify({'valid': False, 'message': 'This code is not valid for exhibitors'})

    # Calculate discount preview
    amount = Decimal(request.json.get('amount', '0'))
    discount = float(promo.calculate_discount(amount))

    return jsonify({
        'valid': True,
        'message': f'Valid! {promo.description}',
        'discount': discount,
        'discount_type': promo.discount_type,
        'discount_value': float(promo.discount_value)
    })


@register_bp.route('/api/ticket-info/<ticket_type>')
def ticket_info(ticket_type):
    """AJAX endpoint to get ticket pricing info"""
    try:
        ticket_enum = AttendeeTicketType[ticket_type.upper()]
    except KeyError:
        return jsonify({'error': 'Invalid ticket type'}), 400

    ticket = TicketPrice.query.filter_by(ticket_type=ticket_enum).first()

    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    return jsonify({
        'name': ticket.name,
        'price': float(ticket.get_current_price()),
        'currency': ticket.currency,
        'available': ticket.is_available(),
        'max_quantity': ticket.max_quantity,
        'current_quantity': ticket.current_quantity,
        'includes_lunch': ticket.includes_lunch,
        'includes_materials': ticket.includes_materials,
        'includes_certificate': ticket.includes_certificate,
    })


@register_bp.route('/api/package-info/<package_type>')
def package_info(package_type):
    """AJAX endpoint to get package pricing info"""
    try:
        package_enum = ExhibitorPackage[package_type.upper()]
    except KeyError:
        return jsonify({'error': 'Invalid package type'}), 400

    package = ExhibitorPackagePrice.query.filter_by(package_type=package_enum).first()

    if not package:
        return jsonify({'error': 'Package not found'}), 404

    return jsonify({
        'name': package.name,
        'price': float(package.price),
        'currency': package.currency,
        'available': package.is_available(),
        'booth_size': package.booth_size,
        'included_passes': package.included_passes,
        'features': package.features,
        'includes_electricity': package.includes_electricity,
        'includes_wifi': package.includes_wifi,
        'includes_speaking_slot': package.includes_speaking_slot,
    })


@register_bp.route('/api/calculate-total', methods=['POST'])
def calculate_total():
    """AJAX endpoint to calculate total cost with add-ons and upgrades"""
    data = request.json

    base_price = Decimal(str(data.get('base_price', 0)))

    # Add booth upgrades
    if data.get('corner_booth'):
        base_price += Decimal('200.00')
    if data.get('entrance_booth'):
        base_price += Decimal('150.00')

    # Add-ons (if provided)
    addons_total = Decimal('0.00')
    for addon in data.get('addons', []):
        addons_total += Decimal(str(addon.get('price', 0))) * addon.get('quantity', 1)

    subtotal = base_price + addons_total

    # Apply promo code discount
    discount = Decimal(str(data.get('discount', 0)))
    subtotal_after_discount = subtotal - discount

    # Calculate tax
    tax_rate = Decimal('0.16')
    tax = subtotal_after_discount * tax_rate

    total = subtotal_after_discount + tax

    return jsonify({
        'base_price': float(base_price),
        'addons_total': float(addons_total),
        'subtotal': float(subtotal),
        'discount': float(discount),
        'subtotal_after_discount': float(subtotal_after_discount),
        'tax': float(tax),
        'tax_rate': float(tax_rate),
        'total': float(total),
        'currency': 'USD'
    })
