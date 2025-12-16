# Flask Payment Routes - DPO Integration (Part 2)

## Flask Routes Implementation

### app/routes/payments.py

```python
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, current_app
from app import db
from app.models import Payment, Ticket, ExhibitorBooth
from app.services.dpo_service import DPOService
from app.services.email_service import EmailService
from app.services.ticket_service import TicketService
import json
from datetime import datetime

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')
dpo_service = DPOService()
email_service = EmailService()
ticket_service = TicketService()


@payments_bp.route('/initiate/ticket', methods=['POST'])
def initiate_ticket_payment():
    """
    Initiate payment for event ticket
    
    Expected POST data:
    {
        "ticket_type": "VIP",
        "quantity": 2,
        "attendee_name": "John Doe",
        "attendee_email": "john@example.com",
        "attendee_phone": "+255712345678"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['ticket_type', 'quantity', 'attendee_name', 
                          'attendee_email', 'attendee_phone']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Get ticket pricing (you can store this in database or config)
        ticket_prices = {
            'VIP': 150000,        # TZS 150,000
            'Regular': 50000,     # TZS 50,000
            'Student': 20000      # TZS 20,000
        }
        
        ticket_type = data['ticket_type']
        if ticket_type not in ticket_prices:
            return jsonify({
                'success': False,
                'error': 'Invalid ticket type'
            }), 400
        
        quantity = int(data['quantity'])
        price_per_ticket = ticket_prices[ticket_type]
        total_amount = price_per_ticket * quantity
        
        # Create payment record
        payment = Payment(
            amount=total_amount,
            currency='TZS',
            payment_type='ticket',
            customer_name=data['attendee_name'],
            customer_email=data['attendee_email'],
            customer_phone=data['attendee_phone'],
            status='pending'
        )
        
        db.session.add(payment)
        db.session.flush()  # Get payment ID without committing
        
        # Create ticket records (pending)
        tickets = []
        for i in range(quantity):
            ticket = Ticket(
                ticket_type=ticket_type,
                attendee_name=data['attendee_name'],
                attendee_email=data['attendee_email'],
                attendee_phone=data['attendee_phone'],
                price=price_per_ticket,
                quantity=1,
                total_amount=price_per_ticket,
                payment_id=payment.id,
                status='pending'
            )
            tickets.append(ticket)
            db.session.add(ticket)
        
        db.session.flush()
        
        # Create DPO payment token
        payment_data = {
            'amount': total_amount,
            'company_ref': payment.company_ref,
            'customer_name': data['attendee_name'],
            'customer_email': data['attendee_email'],
            'customer_phone': data['attendee_phone'],
            'service_description': f'{quantity}x {ticket_type} Ticket(s) - {current_app.config["EVENT_NAME"]}',
            'service_date': current_app.config.get('EVENT_DATE', ''),
            'payment_type': data.get('preferred_payment_method', '')
        }
        
        dpo_response = dpo_service.create_token(payment_data)
        
        if dpo_response['success']:
            # Update payment record with DPO details
            payment.trans_token = dpo_response['trans_token']
            payment.trans_ref = dpo_response['trans_ref']
            payment.payment_url = dpo_response['payment_url']
            payment.dpo_response = json.dumps(dpo_response['full_response'])
            
            db.session.commit()
            
            current_app.logger.info(
                f"Payment initiated for {quantity} {ticket_type} ticket(s). "
                f"Payment ID: {payment.id}, Trans Token: {payment.trans_token}"
            )
            
            return jsonify({
                'success': True,
                'payment_id': payment.id,
                'payment_url': dpo_response['payment_url'],
                'trans_ref': dpo_response['trans_ref'],
                'amount': total_amount,
                'currency': 'TZS'
            })
        else:
            # Payment token creation failed
            db.session.rollback()
            current_app.logger.error(
                f"DPO token creation failed: {dpo_response.get('error')}"
            )
            return jsonify({
                'success': False,
                'error': dpo_response.get('error', 'Payment initialization failed')
            }), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ticket payment initiation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request'
        }), 500


@payments_bp.route('/initiate/booth', methods=['POST'])
def initiate_booth_payment():
    """
    Initiate payment for exhibitor booth
    
    Expected POST data:
    {
        "booth_size": "Premium",
        "company_name": "Tech Corp",
        "contact_person": "Jane Smith",
        "contact_email": "jane@techcorp.com",
        "contact_phone": "+255712345678",
        "requirements": "Power outlet and internet"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['booth_size', 'company_name', 'contact_person',
                          'contact_email', 'contact_phone']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Booth pricing
        booth_prices = {
            'Standard': 500000,   # TZS 500,000
            'Premium': 1000000,   # TZS 1,000,000
            'Corner': 1500000     # TZS 1,500,000
        }
        
        booth_size = data['booth_size']
        if booth_size not in booth_prices:
            return jsonify({
                'success': False,
                'error': 'Invalid booth size'
            }), 400
        
        booth_price = booth_prices[booth_size]
        
        # Create payment record
        payment = Payment(
            amount=booth_price,
            currency='TZS',
            payment_type='booth',
            customer_name=data['contact_person'],
            customer_email=data['contact_email'],
            customer_phone=data['contact_phone'],
            status='pending'
        )
        
        db.session.add(payment)
        db.session.flush()
        
        # Create booth record
        booth = ExhibitorBooth(
            booth_size=booth_size,
            company_name=data['company_name'],
            contact_person=data['contact_person'],
            contact_email=data['contact_email'],
            contact_phone=data['contact_phone'],
            price=booth_price,
            requirements=data.get('requirements', ''),
            payment_id=payment.id,
            status='pending'
        )
        
        db.session.add(booth)
        db.session.flush()
        
        # Create DPO token
        payment_data = {
            'amount': booth_price,
            'company_ref': payment.company_ref,
            'customer_name': data['contact_person'],
            'customer_email': data['contact_email'],
            'customer_phone': data['contact_phone'],
            'service_description': f'{booth_size} Exhibitor Booth - {current_app.config["EVENT_NAME"]}',
            'service_date': current_app.config.get('EVENT_DATE', ''),
            'payment_type': data.get('preferred_payment_method', '')
        }
        
        dpo_response = dpo_service.create_token(payment_data)
        
        if dpo_response['success']:
            payment.trans_token = dpo_response['trans_token']
            payment.trans_ref = dpo_response['trans_ref']
            payment.payment_url = dpo_response['payment_url']
            payment.dpo_response = json.dumps(dpo_response['full_response'])
            
            db.session.commit()
            
            current_app.logger.info(
                f"Booth payment initiated. Company: {data['company_name']}, "
                f"Payment ID: {payment.id}"
            )
            
            return jsonify({
                'success': True,
                'payment_id': payment.id,
                'payment_url': dpo_response['payment_url'],
                'trans_ref': dpo_response['trans_ref'],
                'booth_number': booth.booth_number,
                'amount': booth_price,
                'currency': 'TZS'
            })
        else:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': dpo_response.get('error', 'Payment initialization failed')
            }), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Booth payment initiation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request'
        }), 500


@payments_bp.route('/callback', methods=['GET', 'POST'])
def payment_callback():
    """
    Handle DPO payment callback (redirect)
    
    DPO redirects here after payment with these parameters:
    - TransactionToken
    - CompanyRef
    - TransID (optional)
    """
    try:
        # Get transaction token from query params
        trans_token = request.args.get('TransactionToken') or request.form.get('TransactionToken')
        company_ref = request.args.get('CompanyRef') or request.form.get('CompanyRef')
        
        if not trans_token:
            current_app.logger.error("Payment callback received without transaction token")
            flash('Payment verification failed. Please contact support.', 'error')
            return redirect(url_for('main.index'))
        
        current_app.logger.info(
            f"Payment callback received. Token: {trans_token}, Ref: {company_ref}"
        )
        
        # Find payment record
        payment = Payment.query.filter_by(trans_token=trans_token).first()
        
        if not payment:
            current_app.logger.error(f"Payment not found for token: {trans_token}")
            flash('Payment record not found.', 'error')
            return redirect(url_for('main.index'))
        
        # Verify payment with DPO
        verification_result = dpo_service.verify_token(trans_token)
        
        if verification_result['success'] and verification_result['status'] == 'Approved':
            # Payment successful
            payment.status = 'approved'
            payment.completed_at = datetime.utcnow()
            payment.payment_method = verification_result.get('payment_method', '')
            
            # Update related tickets or booths
            if payment.payment_type == 'ticket':
                for ticket in payment.tickets:
                    ticket.status = 'confirmed'
                    # Generate QR code for ticket
                    ticket.qr_code = ticket_service.generate_qr_code(ticket.ticket_number)
                
                db.session.commit()
                
                # Send confirmation email
                email_service.send_ticket_confirmation(
                    payment.customer_email,
                    payment.tickets
                )
                
                current_app.logger.info(
                    f"Ticket payment confirmed. Payment ID: {payment.id}, "
                    f"Tickets: {len(payment.tickets)}"
                )
                
                return render_template(
                    'payment_success.html',
                    payment=payment,
                    tickets=payment.tickets,
                    message='Your tickets have been confirmed!'
                )
                
            elif payment.payment_type == 'booth':
                for booth in payment.booths:
                    booth.status = 'confirmed'
                
                db.session.commit()
                
                # Send booth confirmation email
                email_service.send_booth_confirmation(
                    payment.customer_email,
                    payment.booths[0]
                )
                
                current_app.logger.info(
                    f"Booth payment confirmed. Payment ID: {payment.id}"
                )
                
                return render_template(
                    'payment_success.html',
                    payment=payment,
                    booth=payment.booths[0],
                    message='Your exhibitor booth has been confirmed!'
                )
        else:
            # Payment failed or declined
            payment.status = 'declined'
            db.session.commit()
            
            current_app.logger.warning(
                f"Payment declined. Payment ID: {payment.id}, "
                f"Reason: {verification_result.get('error', 'Unknown')}"
            )
            
            return render_template(
                'payment_failed.html',
                payment=payment,
                error=verification_result.get('error', 'Payment was not successful')
            )
            
    except Exception as e:
        current_app.logger.error(f"Payment callback error: {str(e)}")
        flash('An error occurred while processing your payment.', 'error')
        return redirect(url_for('main.index'))


@payments_bp.route('/cancel', methods=['GET'])
def payment_cancel():
    """Handle payment cancellation (user clicked back on DPO page)"""
    trans_token = request.args.get('TransactionToken')
    
    if trans_token:
        payment = Payment.query.filter_by(trans_token=trans_token).first()
        if payment:
            payment.status = 'cancelled'
            db.session.commit()
            
            current_app.logger.info(f"Payment cancelled by user. Payment ID: {payment.id}")
    
    flash('Payment was cancelled.', 'info')
    return render_template('payment_cancel.html')


@payments_bp.route('/status/<int:payment_id>', methods=['GET'])
def payment_status(payment_id):
    """
    Check payment status (for AJAX polling)
    
    Returns JSON with payment status
    """
    payment = Payment.query.get_or_404(payment_id)
    
    return jsonify({
        'payment_id': payment.id,
        'status': payment.status,
        'amount': payment.amount,
        'currency': payment.currency,
        'trans_ref': payment.trans_ref,
        'payment_method': payment.payment_method,
        'created_at': payment.created_at.isoformat() if payment.created_at else None,
        'completed_at': payment.completed_at.isoformat() if payment.completed_at else None
    })


@payments_bp.route('/webhook', methods=['POST'])
def payment_webhook():
    """
    Handle DPO webhook notifications
    
    DPO sends POST with XML data containing payment status updates
    This is more reliable than the redirect callback
    """
    try:
        # Get XML data from request
        xml_data = request.data.decode('utf-8')
        
        current_app.logger.info(f"Webhook received: {xml_data[:200]}...")
        
        # Parse XML
        import xmltodict
        data = xmltodict.parse(xml_data)
        api_data = data.get('API3G', {})
        
        trans_token = api_data.get('TransactionToken')
        trans_ref = api_data.get('TransactionRef')
        result = api_data.get('Result')
        
        if not trans_token:
            current_app.logger.error("Webhook received without transaction token")
            return jsonify({'status': 'error', 'message': 'Missing transaction token'}), 400
        
        # Find payment
        payment = Payment.query.filter_by(trans_token=trans_token).first()
        
        if not payment:
            current_app.logger.error(f"Webhook: Payment not found for token {trans_token}")
            return jsonify({'status': 'error', 'message': 'Payment not found'}), 404
        
        # Update payment based on webhook data
        if result == '000':
            # Successful payment
            if payment.status != 'approved':  # Avoid duplicate processing
                payment.status = 'approved'
                payment.completed_at = datetime.utcnow()
                payment.payment_method = api_data.get('AccRef', '')
                
                # Update tickets/booths
                if payment.payment_type == 'ticket':
                    for ticket in payment.tickets:
                        ticket.status = 'confirmed'
                        if not ticket.qr_code:
                            ticket.qr_code = ticket_service.generate_qr_code(ticket.ticket_number)
                    
                    # Send email (background task would be better)
                    try:
                        email_service.send_ticket_confirmation(
                            payment.customer_email,
                            payment.tickets
                        )
                    except Exception as email_error:
                        current_app.logger.error(f"Email send failed: {email_error}")
                
                elif payment.payment_type == 'booth':
                    for booth in payment.booths:
                        booth.status = 'confirmed'
                    
                    try:
                        email_service.send_booth_confirmation(
                            payment.customer_email,
                            payment.booths[0]
                        )
                    except Exception as email_error:
                        current_app.logger.error(f"Email send failed: {email_error}")
                
                db.session.commit()
                
                current_app.logger.info(
                    f"Webhook processed: Payment {payment.id} confirmed"
                )
        else:
            # Payment failed
            payment.status = 'declined'
            db.session.commit()
            
            current_app.logger.warning(
                f"Webhook: Payment {payment.id} declined. Result: {result}"
            )
        
        return jsonify({'status': 'success', 'message': 'Webhook processed'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Webhook processing failed'}), 500


@payments_bp.route('/verify/<trans_token>', methods=['GET'])
def verify_payment(trans_token):
    """
    Manual payment verification endpoint
    Useful for testing or manual verification
    """
    try:
        verification_result = dpo_service.verify_token(trans_token)
        
        return jsonify({
            'success': verification_result['success'],
            'status': verification_result.get('status'),
            'customer_name': verification_result.get('customer_name'),
            'amount': verification_result.get('amount'),
            'payment_method': verification_result.get('payment_method'),
            'error': verification_result.get('error')
        })
        
    except Exception as e:
        current_app.logger.error(f"Manual verification error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## Supporting Services

### app/services/ticket_service.py

```python
import qrcode
from io import BytesIO
import base64
from flask import current_app


class TicketService:
    """Handle ticket-related operations"""
    
    @staticmethod
    def generate_qr_code(ticket_number: str) -> str:
        """
        Generate QR code for ticket validation
        
        Args:
            ticket_number: Unique ticket number
        
        Returns:
            Base64 encoded QR code image
        """
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            # Add ticket data
            qr_data = f"TICKET:{ticket_number}"
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            current_app.logger.error(f"QR code generation error: {str(e)}")
            return ""
    
    @staticmethod
    def validate_ticket(ticket_number: str) -> dict:
        """
        Validate ticket for check-in
        
        Args:
            ticket_number: Ticket number to validate
        
        Returns:
            Dictionary with validation result
        """
        from app.models import Ticket
        from datetime import datetime
        
        ticket = Ticket.query.filter_by(ticket_number=ticket_number).first()
        
        if not ticket:
            return {
                'valid': False,
                'message': 'Ticket not found'
            }
        
        if ticket.status != 'confirmed':
            return {
                'valid': False,
                'message': f'Ticket status: {ticket.status}'
            }
        
        if ticket.checked_in:
            return {
                'valid': False,
                'message': f'Already checked in at {ticket.checked_in_at}',
                'checked_in_at': ticket.checked_in_at
            }
        
        # Mark as checked in
        from app import db
        ticket.checked_in = True
        ticket.checked_in_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'valid': True,
            'message': 'Check-in successful',
            'ticket': ticket.to_dict()
        }
```

### app/services/email_service.py

```python
from flask import current_app, render_template
from flask_mail import Mail, Message
from typing import List


class EmailService:
    """Handle email notifications"""
    
    def __init__(self):
        self.mail = None
    
    def init_app(self, mail: Mail):
        """Initialize with Flask-Mail instance"""
        self.mail = mail
    
    def send_ticket_confirmation(self, recipient_email: str, tickets: List):
        """
        Send ticket confirmation email with QR codes
        
        Args:
            recipient_email: Email address to send to
            tickets: List of Ticket objects
        """
        try:
            msg = Message(
                subject=f'Ticket Confirmation - {current_app.config["EVENT_NAME"]}',
                recipients=[recipient_email]
            )
            
            # Render HTML email template
            msg.html = render_template(
                'emails/ticket_confirmation.html',
                tickets=tickets,
                event_name=current_app.config.get('EVENT_NAME'),
                event_date=current_app.config.get('EVENT_DATE'),
                event_location=current_app.config.get('EVENT_LOCATION')
            )
            
            self.mail.send(msg)
            
            current_app.logger.info(
                f"Ticket confirmation email sent to {recipient_email}"
            )
            
        except Exception as e:
            current_app.logger.error(f"Email send error: {str(e)}")
            raise
    
    def send_booth_confirmation(self, recipient_email: str, booth):
        """
        Send exhibitor booth confirmation email
        
        Args:
            recipient_email: Email address
            booth: ExhibitorBooth object
        """
        try:
            msg = Message(
                subject=f'Exhibitor Booth Confirmation - {current_app.config["EVENT_NAME"]}',
                recipients=[recipient_email]
            )
            
            msg.html = render_template(
                'emails/booth_confirmation.html',
                booth=booth,
                event_name=current_app.config.get('EVENT_NAME'),
                event_date=current_app.config.get('EVENT_DATE'),
                event_location=current_app.config.get('EVENT_LOCATION')
            )
            
            self.mail.send(msg)
            
            current_app.logger.info(
                f"Booth confirmation email sent to {recipient_email}"
            )
            
        except Exception as e:
            current_app.logger.error(f"Booth email send error: {str(e)}")
            raise
```

[Continue to Part 3 for Flask App Initialization, Config, and Frontend Templates...]
