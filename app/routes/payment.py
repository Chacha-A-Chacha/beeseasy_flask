"""
Payment routes for BEEASY2025
Handles checkout, payment processing, and webhooks
"""

import logging
from datetime import datetime, timedelta

import stripe
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.extensions import db
from app.forms import PaymentMethodForm
from app.models import Payment, PaymentMethod, PaymentStatus, Registration
from app.services.dpo_service import dpo_service
from app.services.registration_service import RegistrationService

logger = logging.getLogger(__name__)

payments_bp = Blueprint("payments", __name__)


# ============================================
# CHECKOUT PAGE
# ============================================


@payments_bp.route("/checkout/<ref>")
def checkout(ref):
    """Payment checkout page"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    # Check if already paid
    if registration.is_fully_paid():
        flash("This registration is already paid.", "info")
        return redirect(url_for("register.confirmation", ref=ref))

    # Get payment record
    payment = registration.payments[0] if registration.payments else None

    if not payment:
        flash("Payment record not found. Please contact support.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    form = PaymentMethodForm()

    # Calculate amounts
    balance_due = registration.get_balance_due()

    return render_template(
        "payments/checkout.html",
        registration=registration,
        payment=payment,
        balance_due=balance_due,
        form=form,
        stripe_key=current_app.config.get("STRIPE_PUBLIC_KEY", ""),
    )


@payments_bp.route("/select-method/<ref>", methods=["POST"])
def select_method(ref):
    """Process payment method selection"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    form = PaymentMethodForm()

    if form.validate_on_submit():
        payment_method = form.payment_method.data

        # Route to appropriate payment handler
        if payment_method == "card" or payment_method == "mobile_money":
            # For DPO payments, create token immediately and redirect to DPO gateway
            return redirect(url_for("payments.dpo_direct", ref=ref))
        elif payment_method == "bank_transfer":
            return redirect(url_for("payments.bank_transfer", ref=ref))
        elif payment_method == "invoice":
            return redirect(url_for("payments.invoice_request", ref=ref))

    flash("Please select a payment method.", "error")
    return redirect(url_for("payments.checkout", ref=ref))


# ============================================
# STRIPE PAYMENT
# ============================================


@payments_bp.route("/stripe/checkout/<ref>")
def stripe_checkout(ref):
    """Create Stripe checkout session"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        flash("Payment record not found.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    try:
        stripe.api_key = current_app.config.get("STRIPE_SECRET_KEY")

        # Create Stripe checkout session
        session_data = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": payment.currency.lower(),
                        "product_data": {
                            "name": f"BEEASY2025 Registration - {registration.registration_type.title()}",
                            "description": f"Reference: {registration.reference_number}",
                        },
                        "unit_amount": int(
                            float(payment.total_amount) * 100
                        ),  # Convert to cents
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=url_for("payments.success", ref=ref, _external=True),
            cancel_url=url_for("payments.cancelled", ref=ref, _external=True),
            metadata={
                "registration_id": registration.id,
                "payment_id": payment.id,
                "reference_number": registration.reference_number,
            },
        )

        # Update payment with Stripe session ID
        payment.stripe_checkout_session_id = session_data.id
        payment.payment_method = PaymentMethod.CARD
        payment.payment_status = PaymentStatus.PROCESSING
        db.session.commit()

        return redirect(session_data.url, code=303)

    except Exception as e:
        logger.error(f"Stripe checkout error: {str(e)}")
        flash(
            "Unable to process payment. Please try again or contact support.", "error"
        )
        return redirect(url_for("payments.checkout", ref=ref))


@payments_bp.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        logger.error("Invalid Stripe webhook payload")
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe webhook signature")
        return jsonify({"error": "Invalid signature"}), 400

    # Handle payment success
    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]

        payment_id = session_obj["metadata"].get("payment_id")
        registration_id = session_obj["metadata"].get("registration_id")

        if payment_id:
            # Process payment completion
            success, message = RegistrationService.process_payment_completion(
                payment_id=int(payment_id),
                transaction_id=session_obj["id"],
                payment_method=PaymentMethod.CARD,
            )

            if success:
                logger.info(f"Payment completed via Stripe webhook: {payment_id}")
            else:
                logger.error(f"Failed to process payment: {message}")

    return jsonify({"status": "success"}), 200


# ============================================
# M-PESA PAYMENT
# ============================================


@payments_bp.route("/mpesa/checkout/<ref>", methods=["GET", "POST"])
def mpesa_checkout(ref):
    """M-Pesa payment page"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        flash("Payment record not found.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    if request.method == "POST":
        phone_number = request.form.get("phone_number", "").strip()

        if not phone_number:
            flash("Phone number is required for M-Pesa payment.", "error")
            return render_template(
                "payments/mpesa.html", registration=registration, payment=payment
            )

        # TODO: Integrate with M-Pesa API (Safaricom)
        # For now, just update payment status
        payment.payment_method = PaymentMethod.MOBILE_MONEY
        payment.payment_status = PaymentStatus.PROCESSING
        db.session.commit()

        flash(
            "M-Pesa payment initiated. Please complete the payment on your phone.",
            "info",
        )
        return redirect(url_for("payments.pending", ref=ref))

    return render_template(
        "payments/mpesa.html", registration=registration, payment=payment
    )


@payments_bp.route("/mpesa/callback", methods=["POST"])
def mpesa_callback():
    """M-Pesa payment callback"""
    # TODO: Implement M-Pesa callback handling
    # Verify signature, update payment status

    data = request.json
    logger.info(f"M-Pesa callback received: {data}")

    # Extract payment details and update
    # payment_id = data.get('payment_id')
    # transaction_id = data.get('transaction_id')
    # status = data.get('status')

    return jsonify({"status": "received"}), 200


# ============================================
# DPO PAYMENT (Tanzania Mobile Money & Cards)
# ============================================


@payments_bp.route("/dpo/direct/<ref>")
def dpo_direct(ref):
    """
    Direct DPO payment - creates token immediately and redirects to DPO gateway
    User will select payment method on DPO's page (cards, mobile money, etc.)
    """
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        flash("Payment record not found.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    # Check if already paid
    if registration.is_fully_paid():
        flash("This registration is already paid.", "info")
        return redirect(url_for("register.confirmation", ref=ref))

    # Get customer details
    customer_name = f"{registration.first_name} {registration.last_name}"
    customer_email = registration.email
    customer_phone = f"{registration.phone_country_code}{registration.phone_number}"

    # Prepare payment data for DPO - no specific payment_type means DPO shows all options
    payment_data = {
        "amount": float(payment.total_amount),
        "currency": payment.currency,
        "company_ref": payment.payment_reference,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "service_description": f"{current_app.config.get('EVENT_SHORT_NAME')} - {registration.registration_type.title()} Registration",
        "service_date": (datetime.now() + timedelta(days=30)).strftime(
            "%Y/%m/%d 09:00"
        ),
        # No payment_type specified - DPO will show all available options
    }

    # Create DPO token
    logger.info(f"Creating DPO token for {payment.payment_reference} (direct mode)")
    result = dpo_service.create_token(payment_data)

    if result.get("success"):
        # Save DPO token to payment record
        payment.set_dpo_token(
            trans_token=result["trans_token"],
            trans_ref=result["trans_ref"],
            payment_type="dpo",  # Generic type
        )

        # Payment method will be determined after user pays on DPO's site
        payment.payment_method = (
            PaymentMethod.MOBILE_MONEY
        )  # Default, will update via webhook

        db.session.commit()

        logger.info(
            f"DPO token created: {result['trans_token']}, redirecting to payment page"
        )

        # Redirect directly to DPO payment page
        return redirect(result["payment_url"])
    else:
        # Token creation failed
        error_msg = result.get("error", "Unable to initiate payment")
        logger.error(f"DPO token creation failed: {error_msg}")
        flash(f"Payment initiation failed: {error_msg}", "error")
        return redirect(url_for("payments.checkout", ref=ref))


@payments_bp.route("/dpo/initiate/<ref>", methods=["GET", "POST"])
def dpo_initiate(ref):
    """
    Initiate DPO payment
    Supports:
    - Credit/Debit Cards (Visa, Mastercard, Amex)
    - M-Pesa Tanzania (Vodacom)
    - M-Pesa Kenya (Safaricom)
    - Tigo Pesa (Tanzania)
    - Airtel Money (Multi-country)
    - MTN Mobile Money (Uganda, Rwanda)
    - Orange Money (Multi-country)
    """
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        flash("Payment record not found.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    # Check if already paid
    if registration.is_fully_paid():
        flash("This registration is already paid.", "info")
        return redirect(url_for("register.confirmation", ref=ref))

    if request.method == "POST":
        # Get selected payment type (mpesa, tigo, airtel, card)
        payment_type = request.form.get("payment_type", "").lower()

        if not payment_type:
            flash("Please select a payment method.", "error")
            return render_template(
                "payments/dpo_select.html",
                registration=registration,
                payment=payment,
                payment_methods=dpo_service.get_supported_payment_methods(),
            )

        # Get attendee/exhibitor details
        # Note: With JTI, registration is already the subclass (AttendeeRegistration or ExhibitorRegistration)
        customer_name = f"{registration.first_name} {registration.last_name}"
        customer_email = registration.email
        customer_phone = f"{registration.phone_country_code}{registration.phone_number}"

        # Prepare payment data for DPO
        payment_data = {
            "amount": float(payment.total_amount),
            "currency": payment.currency,  # Use payment's actual currency (USD, TZS, etc.)
            "company_ref": payment.payment_reference,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "service_description": f"{current_app.config.get('EVENT_SHORT_NAME')} - {registration.registration_type.title()} Registration",
            "service_date": (datetime.now() + timedelta(days=30)).strftime(
                "%Y/%m/%d 09:00"
            ),
            "payment_type": payment_type,
        }

        # Create DPO token
        logger.info(f"Creating DPO token for {payment.payment_reference}")
        result = dpo_service.create_token(payment_data)

        if result.get("success"):
            # Save DPO token to payment record
            payment.set_dpo_token(
                trans_token=result["trans_token"],
                trans_ref=result["trans_ref"],
                payment_type=payment_type,
            )

            # Set payment method based on type
            if payment_type == "card":
                payment.payment_method = PaymentMethod.CARD
            else:
                payment.payment_method = PaymentMethod.MOBILE_MONEY

            db.session.commit()

            logger.info(
                f"DPO token created: {result['trans_token']}, redirecting to payment page"
            )

            # Redirect to DPO payment page
            return redirect(result["payment_url"])
        else:
            # Token creation failed
            error_msg = result.get("error", "Unable to initiate payment")
            logger.error(f"DPO token creation failed: {error_msg}")
            flash(f"Payment initiation failed: {error_msg}", "error")
            return render_template(
                "payments/dpo_select.html",
                registration=registration,
                payment=payment,
                payment_methods=dpo_service.get_supported_payment_methods(),
            )

    # GET request - show payment method selection
    return render_template(
        "payments/dpo_select.html",
        registration=registration,
        payment=payment,
        payment_methods=dpo_service.get_supported_payment_methods(),
    )


@payments_bp.route("/dpo/callback")
def dpo_callback():
    """
    DPO payment callback/redirect URL
    Called when user completes or cancels payment on DPO page
    """
    # DPO sends these parameters via GET
    trans_token = request.args.get("TransactionToken")
    trans_id = request.args.get("TransID")
    cc_approval = request.args.get("CCDapproval")
    pnr_id = request.args.get("PnrID")
    company_ref = request.args.get("CompanyRef")

    logger.info(
        f"DPO callback received - Token: {trans_token}, TransID: {trans_id}, CompanyRef: {company_ref}"
    )

    if not trans_token:
        flash("Invalid payment callback.", "error")
        return redirect(url_for("main.index"))

    # Find payment by DPO token
    payment = Payment.query.filter_by(dpo_trans_token=trans_token).first()

    if not payment:
        logger.error(f"Payment not found for DPO token: {trans_token}")
        flash("Payment record not found.", "error")
        return redirect(url_for("main.index"))

    # Verify payment with DPO
    logger.info(f"Verifying payment with DPO for token: {trans_token}")
    verification_result = dpo_service.verify_token(trans_token)

    # Update payment record with verification result
    payment.update_from_dpo_verification(verification_result)
    db.session.commit()

    registration = payment.registration

    if verification_result.get("success"):
        # Payment successful - process completion (generates badge and sends email)
        logger.info(
            f"Payment verified successfully: {payment.payment_reference} - Status: {payment.payment_status.value}"
        )

        # Process payment completion - generates badge and sends confirmation email
        success, message = RegistrationService.process_payment_completion(
            payment_id=payment.id,
            transaction_id=verification_result.get("trans_id", ""),
            payment_method=PaymentMethod.MOBILE_MONEY
            if payment.payment_method == PaymentMethod.MOBILE_MONEY
            else PaymentMethod.CARD,
        )

        if success:
            logger.info(f"Payment completion processed: {payment.payment_reference}")
        else:
            logger.error(f"Failed to process payment completion: {message}")

        flash(
            "Payment completed successfully! Check your email for your badge and confirmation.",
            "success",
        )
        return redirect(url_for("payments.success", ref=registration.reference_number))
    else:
        # Payment failed or pending
        status = verification_result.get("status", "Unknown")
        message = verification_result.get("error", "Payment verification failed")
        logger.warning(
            f"Payment verification failed: {payment.payment_reference} - {message}"
        )

        if payment.payment_status == PaymentStatus.PENDING:
            flash(
                "Payment is still pending. Please wait for confirmation or contact support.",
                "info",
            )
            return redirect(
                url_for("payments.pending", ref=registration.reference_number)
            )
        else:
            flash(f"Payment failed: {message}", "error")
            return redirect(
                url_for("payments.cancelled", ref=registration.reference_number)
            )


@payments_bp.route("/dpo/verify/<ref>")
def dpo_verify(ref):
    """
    Manual DPO payment verification endpoint
    Useful for checking payment status after redirect
    """
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    payment = registration.payments[0] if registration.payments else None

    if not payment or not payment.is_dpo_payment:
        flash("No DPO payment found for this registration.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    # Verify with DPO
    logger.info(f"Manual verification for DPO token: {payment.dpo_trans_token}")
    verification_result = dpo_service.verify_token(payment.dpo_trans_token)

    # Update payment
    payment.update_from_dpo_verification(verification_result)
    db.session.commit()

    if verification_result.get("success"):
        # Process payment completion - generates badge and sends confirmation email
        success, message = RegistrationService.process_payment_completion(
            payment_id=payment.id,
            transaction_id=verification_result.get("trans_id", ""),
            payment_method=PaymentMethod.MOBILE_MONEY
            if payment.payment_method == PaymentMethod.MOBILE_MONEY
            else PaymentMethod.CARD,
        )

        if success:
            logger.info(f"Manual verification completed: {payment.payment_reference}")
        else:
            logger.error(f"Failed to process payment completion: {message}")

        flash(
            "Payment verified successfully! Check your email for confirmation.",
            "success",
        )
        return redirect(url_for("payments.success", ref=ref))
    else:
        message = verification_result.get("error", "Payment not completed")
        flash(f"Payment status: {message}", "info")
        return redirect(url_for("payments.pending", ref=ref))


# ============================================
# BANK TRANSFER
# ============================================


@payments_bp.route("/bank-transfer/<ref>")
def bank_transfer(ref):
    """Bank transfer instructions page"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        flash("Payment record not found.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    # Update payment method
    payment.payment_method = PaymentMethod.BANK_TRANSFER
    payment.payment_status = PaymentStatus.PENDING
    db.session.commit()

    # Bank details (from config)
    bank_details = {
        "bank_name": current_app.config.get("BANK_NAME", "Bank Name"),
        "account_name": current_app.config.get(
            "BANK_ACCOUNT_NAME", "BEEASY Organization"
        ),
        "account_number": current_app.config.get("BANK_ACCOUNT_NUMBER", "1234567890"),
        "swift_code": current_app.config.get("BANK_SWIFT", "BANKKE22"),
        "branch": current_app.config.get("BANK_BRANCH", "Main Branch"),
    }

    return render_template(
        "payments/bank_transfer.html",
        registration=registration,
        payment=payment,
        bank_details=bank_details,
    )


# ============================================
# INVOICE REQUEST
# ============================================


@payments_bp.route("/invoice/<ref>")
def invoice_request(ref):
    """Request invoice for company payment"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        flash("Payment record not found.", "error")
        return redirect(url_for("register.confirmation", ref=ref))

    # Update payment method
    payment.payment_method = PaymentMethod.INVOICE
    payment.payment_status = PaymentStatus.PENDING
    db.session.commit()

    # Send invoice request confirmation email
    try:
        from app.utils.enhanced_email import EnhancedEmailService

        email_service = EnhancedEmailService(current_app)

        context = {
            "registration": registration,
            "payment": payment,
            "amount_due": float(payment.total_amount),
            "currency": payment.currency,
            "event_name": current_app.config.get(
                "EVENT_NAME", "Pollination Africa Symposium 2026"
            ),
            "event_date": current_app.config.get("EVENT_DATE", "3-5 June 2026"),
            "event_location": current_app.config.get(
                "EVENT_LOCATION",
                "Arusha International Conference Centre, Arusha, Tanzania",
            ),
            "contact_email": current_app.config.get(
                "CONTACT_EMAIL", "info@pollination.africa"
            ),
            "support_phone": current_app.config.get(
                "SUPPORT_PHONE", "+254 719 740 938"
            ),
            "support_whatsapp": current_app.config.get(
                "SUPPORT_WHATSAPP", "+254 719 740 938"
            ),
            "website_url": current_app.config.get(
                "WEBSITE_URL", "https://pollination.africa"
            ),
        }

        email_service.send_notification(
            recipient=registration.email,
            template="invoice_request_confirmation",
            subject="Invoice Request Received - Pollination Africa Symposium 2026",
            template_context=context,
            priority=1,
        )

        logger.info(f"Invoice request confirmation email sent to {registration.email}")

    except Exception as e:
        logger.error(f"Failed to send invoice request email: {str(e)}", exc_info=True)

    flash(
        "Invoice request received. An invoice will be sent to your email within 24 hours.",
        "success",
    )
    return render_template(
        "payments/invoice.html", registration=registration, payment=payment
    )


# ============================================
# PAYMENT STATUS PAGES
# ============================================


@payments_bp.route("/success/<ref>")
def success(ref):
    """Payment success page"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    # Check if payment is completed
    if not registration.is_fully_paid():
        flash(
            "Payment verification in progress. You will receive confirmation shortly.",
            "info",
        )

    return render_template("payments/success.html", registration=registration)


@payments_bp.route("/cancelled/<ref>")
def cancelled(ref):
    """Payment cancelled page"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    return render_template("payments/cancelled.html", registration=registration)


@payments_bp.route("/pending/<ref>")
def pending(ref):
    """Payment pending page"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    payment = registration.payments[0] if registration.payments else None

    return render_template(
        "payments/pending.html", registration=registration, payment=payment
    )


# ============================================
# AJAX ENDPOINTS
# ============================================


@payments_bp.route("/api/payment-status/<ref>")
def payment_status_api(ref):
    """AJAX endpoint to check payment status"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first()

    if not registration:
        return jsonify({"error": "Registration not found"}), 404

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        return jsonify({"error": "Payment not found"}), 404

    return jsonify(
        {
            "status": payment.payment_status.value,
            "is_paid": payment.is_paid,
            "total_amount": float(payment.total_amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method.value
            if payment.payment_method
            else None,
            "payment_completed_at": payment.payment_completed_at.isoformat()
            if payment.payment_completed_at
            else None,
        }
    )


@payments_bp.route("/api/verify-payment/<ref>", methods=["POST"])
def verify_payment(ref):
    """AJAX endpoint to manually verify payment (for bank transfers)"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first()

    if not registration:
        return jsonify({"error": "Registration not found"}), 404

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        return jsonify({"error": "Payment not found"}), 404

    # Get bank reference from request
    bank_reference = request.json.get("bank_reference", "")

    if not bank_reference:
        return jsonify({"error": "Bank reference is required"}), 400

    # Update payment with reference
    payment.bank_reference = bank_reference
    payment.payment_status = PaymentStatus.PROCESSING
    db.session.commit()

    # TODO: Queue for admin verification

    return jsonify(
        {
            "success": True,
            "message": "Payment verification requested. We will confirm within 24 hours.",
        }
    )


@payments_bp.route("/api/create-payment-intent", methods=["POST"])
def create_payment_intent():
    """Create Stripe payment intent for custom checkout"""
    data = request.json
    ref = data.get("reference_number")

    if not ref:
        return jsonify({"error": "Reference number required"}), 400

    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first()

    if not registration:
        return jsonify({"error": "Registration not found"}), 404

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        return jsonify({"error": "Payment not found"}), 404

    try:
        stripe.api_key = current_app.config.get("STRIPE_SECRET_KEY")

        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(float(payment.total_amount) * 100),
            currency=payment.currency.lower(),
            metadata={
                "registration_id": registration.id,
                "payment_id": payment.id,
                "reference_number": registration.reference_number,
            },
        )

        # Update payment record
        payment.stripe_payment_intent_id = intent.id
        payment.payment_method = PaymentMethod.CARD
        db.session.commit()

        return jsonify(
            {"client_secret": intent.client_secret, "payment_intent_id": intent.id}
        )

    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return jsonify({"error": "Failed to create payment intent"}), 500


# ============================================
# INVOICE DOWNLOAD
# ============================================


@payments_bp.route("/invoice/download/<ref>")
def download_invoice(ref):
    """Download invoice PDF"""
    registration = Registration.query.filter_by(
        reference_number=ref, is_deleted=False
    ).first_or_404()

    payment = registration.payments[0] if registration.payments else None

    if not payment:
        abort(404)

    # TODO: Generate PDF invoice
    # For now, redirect to invoice page
    return redirect(url_for("payments.invoice_request", ref=ref))
