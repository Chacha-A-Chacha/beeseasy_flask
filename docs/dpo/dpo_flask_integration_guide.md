# DPO Group Payment Integration for Flask - Event Ticketing System

## Complete Implementation Guide for Tanzania Event Tickets & Exhibitor Booth Payments

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Installation & Setup](#installation--setup)
3. [Project Structure](#project-structure)
4. [Environment Configuration](#environment-configuration)
5. [Database Models](#database-models)
6. [DPO Service Class](#dpo-service-class)
7. [Flask Routes](#flask-routes)
8. [Frontend Integration](#frontend-integration)
9. [Webhook Handling](#webhook-handling)
10. [Testing Strategy](#testing-strategy)
11. [Production Deployment](#production-deployment)

---

## Architecture Overview

### Payment Flow Diagram

```
User selects ticket/booth
         ↓
Flask creates payment token (createToken API)
         ↓
User redirected to DPO checkout page
         ↓
User selects payment method (M-Pesa/Tigo/Airtel/Card)
         ↓
User completes payment
         ↓
DPO redirects back to your app
         ↓
Flask verifies payment (verifyToken API)
         ↓
Generate ticket/booth confirmation
         ↓
Send email confirmation
```

### Key Components

1. **DPO Service Class**: Handles all DPO API interactions
2. **Payment Routes**: Flask endpoints for payment initiation and callback
3. **Database Models**: Store transactions, tickets, and booths
4. **Webhook Handler**: Process DPO payment notifications
5. **Email Service**: Send confirmations

---

## Installation & Setup

### 1. Install Dependencies

```bash
pip install Flask==3.0.0
pip install Flask-SQLAlchemy==3.1.1
pip install Flask-Migrate==4.0.5
pip install python-dotenv==1.0.0
pip install requests==2.31.0
pip install xmltodict==0.13.0
pip install Flask-Mail==0.9.1
pip install gunicorn==21.2.0
```

### 2. Or use requirements.txt

```txt
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5
python-dotenv==1.0.0
requests==2.31.0
xmltodict==0.13.0
Flask-Mail==0.9.1
gunicorn==21.2.0
qrcode[pil]==7.4.2
Pillow==10.1.0
```

---

## Project Structure

```
event-ticketing/
│
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── tickets.py
│   │   ├── payments.py
│   │   └── exhibitors.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── dpo_service.py
│   │   ├── email_service.py
│   │   └── ticket_service.py
│   ├── templates/
│   │   ├── checkout.html
│   │   ├── payment_success.html
│   │   ├── payment_failed.html
│   │   └── emails/
│   │       └── ticket_confirmation.html
│   └── static/
│       ├── css/
│       └── js/
│
├── migrations/
├── tests/
├── config.py
├── .env
├── .env.example
├── run.py
└── requirements.txt
```

---

## Environment Configuration

### .env File

```env
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=sqlite:///event_ticketing.db

# DPO Configuration
DPO_COMPANY_TOKEN=9F416C11-127B-4DE2-AC7F-D5710E4C5E0A
DPO_SERVICE_TYPE=3854
DPO_CURRENCY=TZS
DPO_TEST_MODE=True
DPO_API_URL_LIVE=https://secure.3gdirectpay.com
DPO_API_URL_TEST=https://secure1.sandbox.directpay.online

# Application URLs
APP_BASE_URL=http://localhost:5000
DPO_REDIRECT_URL=http://localhost:5000/payments/callback
DPO_BACK_URL=http://localhost:5000/payments/cancel

# Email Configuration (for confirmations)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Event Configuration
EVENT_NAME=Tanzania Tech Summit 2025
EVENT_DATE=2025-03-15
EVENT_LOCATION=Dar es Salaam, Tanzania
```

### .env.example (for version control)

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=change-me
DATABASE_URL=sqlite:///event_ticketing.db

DPO_COMPANY_TOKEN=your-company-token
DPO_SERVICE_TYPE=your-service-type
DPO_CURRENCY=TZS
DPO_TEST_MODE=True

APP_BASE_URL=http://localhost:5000
DPO_REDIRECT_URL=http://localhost:5000/payments/callback
DPO_BACK_URL=http://localhost:5000/payments/cancel

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=

EVENT_NAME=Your Event Name
EVENT_DATE=2025-03-15
EVENT_LOCATION=Event Location
```

---

## Database Models

### app/models.py

```python
from datetime import datetime
from app import db
import secrets

class Ticket(db.Model):
    """Event Ticket Model"""
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    ticket_type = db.Column(db.String(50), nullable=False)  # VIP, Regular, Student
    attendee_name = db.Column(db.String(100), nullable=False)
    attendee_email = db.Column(db.String(120), nullable=False)
    attendee_phone = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Payment tracking
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'))
    payment = db.relationship('Payment', backref='tickets')
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled
    checked_in = db.Column(db.Boolean, default=False)
    checked_in_at = db.Column(db.DateTime)
    
    # QR Code for validation
    qr_code = db.Column(db.String(500))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(Ticket, self).__init__(**kwargs)
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
    
    @staticmethod
    def generate_ticket_number():
        """Generate unique ticket number"""
        prefix = "TKT"
        random_part = secrets.token_hex(4).upper()
        return f"{prefix}-{random_part}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_number': self.ticket_number,
            'ticket_type': self.ticket_type,
            'attendee_name': self.attendee_name,
            'attendee_email': self.attendee_email,
            'price': self.price,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ExhibitorBooth(db.Model):
    """Exhibitor Booth Model"""
    __tablename__ = 'exhibitor_booths'
    
    id = db.Column(db.Integer, primary_key=True)
    booth_number = db.Column(db.String(20), unique=True, nullable=False)
    booth_size = db.Column(db.String(20), nullable=False)  # Standard, Premium, Corner
    company_name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Payment tracking
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'))
    payment = db.relationship('Payment', backref='booths')
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled
    
    # Additional info
    requirements = db.Column(db.Text)  # Special requirements (power, internet, etc.)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(ExhibitorBooth, self).__init__(**kwargs)
        if not self.booth_number:
            self.booth_number = self.generate_booth_number()
    
    @staticmethod
    def generate_booth_number():
        """Generate unique booth number"""
        prefix = "BOOTH"
        random_part = secrets.token_hex(3).upper()
        return f"{prefix}-{random_part}"


class Payment(db.Model):
    """Payment Transaction Model"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # DPO Transaction Details
    trans_token = db.Column(db.String(100), unique=True)
    trans_ref = db.Column(db.String(100))
    company_ref = db.Column(db.String(100), unique=True, nullable=False)
    
    # Payment Details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='TZS')
    payment_type = db.Column(db.String(20))  # ticket, booth
    
    # Customer Details
    customer_name = db.Column(db.String(100))
    customer_email = db.Column(db.String(120))
    customer_phone = db.Column(db.String(20))
    
    # Payment Status
    status = db.Column(db.String(20), default='pending')  
    # pending, approved, declined, cancelled
    
    payment_method = db.Column(db.String(50))  # M-Pesa, Card, Tigo, Airtel
    
    # DPO Response Data
    dpo_response = db.Column(db.Text)  # Store full DPO response as JSON
    
    # URLs
    payment_url = db.Column(db.String(500))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        super(Payment, self).__init__(**kwargs)
        if not self.company_ref:
            self.company_ref = self.generate_company_ref()
    
    @staticmethod
    def generate_company_ref():
        """Generate unique company reference"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_part = secrets.token_hex(3).upper()
        return f"PAY-{timestamp}-{random_part}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'trans_ref': self.trans_ref,
            'company_ref': self.company_ref,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

---

## DPO Service Class

### app/services/dpo_service.py

```python
import os
import requests
import xmltodict
from typing import Dict, Optional
from flask import current_app


class DPOService:
    """
    DPO Payment Gateway Service
    
    Handles all interactions with DPO API including:
    - Creating payment tokens
    - Verifying payments
    - Generating payment URLs
    """
    
    def __init__(self):
        self.company_token = os.getenv('DPO_COMPANY_TOKEN')
        self.service_type = os.getenv('DPO_SERVICE_TYPE')
        self.currency = os.getenv('DPO_CURRENCY', 'TZS')
        self.test_mode = os.getenv('DPO_TEST_MODE', 'True').lower() == 'true'
        
        # API URLs
        self.base_url = (
            os.getenv('DPO_API_URL_TEST') if self.test_mode 
            else os.getenv('DPO_API_URL_LIVE')
        )
        self.api_url = f"{self.base_url}/API/v6/"
        
        # Callback URLs
        self.redirect_url = os.getenv('DPO_REDIRECT_URL')
        self.back_url = os.getenv('DPO_BACK_URL')
    
    def create_token(self, payment_data: Dict) -> Dict:
        """
        Create payment token with DPO
        
        Args:
            payment_data: Dictionary containing payment information
                {
                    'amount': float,
                    'company_ref': str (unique),
                    'customer_name': str,
                    'customer_email': str,
                    'customer_phone': str,
                    'service_description': str,
                    'payment_type': str (optional - for mobile money preset)
                }
        
        Returns:
            Dictionary with token information or error
            {
                'success': bool,
                'trans_token': str,
                'trans_ref': str,
                'payment_url': str,
                'error': str (if failed)
            }
        """
        try:
            # Build XML request
            xml_request = self._build_create_token_xml(payment_data)
            
            current_app.logger.info(f"Creating DPO token for {payment_data['company_ref']}")
            
            # Send request to DPO
            response = requests.post(
                self.api_url,
                data=xml_request,
                headers={'Content-Type': 'application/xml'},
                timeout=30
            )
            
            response.raise_for_status()
            
            # Parse XML response
            result = xmltodict.parse(response.content)
            api_response = result.get('API3G', {})
            
            # Check for success
            result_code = api_response.get('Result', '')
            
            if result_code == '000':
                trans_token = api_response.get('TransToken')
                trans_ref = api_response.get('TransRef')
                payment_url = self._create_payment_url(trans_token)
                
                current_app.logger.info(
                    f"DPO token created successfully: {trans_token}"
                )
                
                return {
                    'success': True,
                    'trans_token': trans_token,
                    'trans_ref': trans_ref,
                    'payment_url': payment_url,
                    'full_response': api_response
                }
            else:
                error_msg = api_response.get('ResultExplanation', 'Unknown error')
                current_app.logger.error(
                    f"DPO token creation failed: {error_msg}"
                )
                
                return {
                    'success': False,
                    'error': error_msg,
                    'result_code': result_code
                }
                
        except requests.RequestException as e:
            current_app.logger.error(f"DPO API request failed: {str(e)}")
            return {
                'success': False,
                'error': f'Payment gateway connection error: {str(e)}'
            }
        except Exception as e:
            current_app.logger.error(f"DPO token creation error: {str(e)}")
            return {
                'success': False,
                'error': f'Payment processing error: {str(e)}'
            }
    
    def verify_token(self, trans_token: str) -> Dict:
        """
        Verify payment status with DPO
        
        Args:
            trans_token: Transaction token from DPO
        
        Returns:
            Dictionary with payment verification result
            {
                'success': bool,
                'status': str (Approved, Declined, etc.),
                'customer_name': str,
                'customer_phone': str,
                'payment_method': str,
                'amount': float,
                'error': str (if failed)
            }
        """
        try:
            # Build XML request
            xml_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <API3G>
                <CompanyToken>{self.company_token}</CompanyToken>
                <Request>verifyToken</Request>
                <TransactionToken>{trans_token}</TransactionToken>
            </API3G>'''
            
            current_app.logger.info(f"Verifying DPO token: {trans_token}")
            
            # Send request
            response = requests.post(
                self.api_url,
                data=xml_request,
                headers={'Content-Type': 'application/xml'},
                timeout=30
            )
            
            response.raise_for_status()
            
            # Parse response
            result = xmltodict.parse(response.content)
            api_response = result.get('API3G', {})
            
            result_code = api_response.get('Result', '')
            
            if result_code == '000':
                # Payment successful
                current_app.logger.info(
                    f"Payment verified successfully: {trans_token}"
                )
                
                return {
                    'success': True,
                    'status': 'Approved',
                    'customer_name': api_response.get('CustomerName', ''),
                    'customer_phone': api_response.get('CustomerPhone', ''),
                    'payment_method': api_response.get('AccRef', ''),
                    'amount': float(api_response.get('TransactionAmount', 0)),
                    'currency': api_response.get('TransactionCurrency', self.currency),
                    'trans_ref': api_response.get('TransactionRef', ''),
                    'full_response': api_response
                }
            else:
                # Payment failed or pending
                status_explanation = api_response.get('ResultExplanation', 'Unknown')
                
                current_app.logger.warning(
                    f"Payment verification failed: {status_explanation}"
                )
                
                return {
                    'success': False,
                    'status': 'Declined',
                    'error': status_explanation,
                    'result_code': result_code,
                    'full_response': api_response
                }
                
        except Exception as e:
            current_app.logger.error(f"Token verification error: {str(e)}")
            return {
                'success': False,
                'error': f'Verification error: {str(e)}'
            }
    
    def _build_create_token_xml(self, payment_data: Dict) -> str:
        """Build XML request for createToken"""
        
        # Extract customer name parts
        customer_name = payment_data.get('customer_name', '').split(' ', 1)
        first_name = customer_name[0] if len(customer_name) > 0 else ''
        last_name = customer_name[1] if len(customer_name) > 1 else ''
        
        # Optional: Set default payment method for mobile money
        default_payment = ''
        payment_type = payment_data.get('payment_type', '').lower()
        
        if payment_type == 'mpesa':
            default_payment = '''
            <DefaultPayment>MO</DefaultPayment>
            <DefaultPaymentCountry>Tanzania</DefaultPaymentCountry>
            <DefaultPaymentMNO>Vodacom</DefaultPaymentMNO>'''
        elif payment_type == 'tigo':
            default_payment = '''
            <DefaultPayment>MO</DefaultPayment>
            <DefaultPaymentCountry>Tanzania</DefaultPaymentCountry>
            <DefaultPaymentMNO>Tigo</DefaultPaymentMNO>'''
        elif payment_type == 'airtel':
            default_payment = '''
            <DefaultPayment>MO</DefaultPayment>
            <DefaultPaymentCountry>Tanzania</DefaultPaymentCountry>
            <DefaultPaymentMNO>Airtel</DefaultPaymentMNO>'''
        
        xml = f'''<?xml version="1.0" encoding="utf-8"?>
        <API3G>
            <CompanyToken>{self.company_token}</CompanyToken>
            <Request>createToken</Request>
            <Transaction>
                <PaymentAmount>{payment_data['amount']}</PaymentAmount>
                <PaymentCurrency>{self.currency}</PaymentCurrency>
                <CompanyRef>{payment_data['company_ref']}</CompanyRef>
                <RedirectURL>{self.redirect_url}</RedirectURL>
                <BackURL>{self.back_url}</BackURL>
                <CompanyRefUnique>1</CompanyRefUnique>
                <PTL>5</PTL>
                <customerFirstName>{first_name}</customerFirstName>
                <customerLastName>{last_name}</customerLastName>
                <customerEmail>{payment_data.get('customer_email', '')}</customerEmail>
                <customerPhone>{payment_data.get('customer_phone', '')}</customerPhone>
                {default_payment}
            </Transaction>
            <Services>
                <Service>
                    <ServiceType>{self.service_type}</ServiceType>
                    <ServiceDescription>{payment_data.get('service_description', 'Event Payment')}</ServiceDescription>
                    <ServiceDate>{payment_data.get('service_date', '')}</ServiceDate>
                </Service>
            </Services>
        </API3G>'''
        
        return xml
    
    def _create_payment_url(self, trans_token: str) -> str:
        """Generate DPO payment page URL"""
        return f"{self.base_url}/payv2.php?ID={trans_token}"
    
    def cancel_token(self, trans_token: str) -> Dict:
        """
        Cancel a payment token
        
        Args:
            trans_token: Transaction token to cancel
        
        Returns:
            Dictionary with cancellation result
        """
        try:
            xml_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <API3G>
                <CompanyToken>{self.company_token}</CompanyToken>
                <Request>cancelToken</Request>
                <TransactionToken>{trans_token}</TransactionToken>
            </API3G>'''
            
            response = requests.post(
                self.api_url,
                data=xml_request,
                headers={'Content-Type': 'application/xml'},
                timeout=30
            )
            
            result = xmltodict.parse(response.content)
            api_response = result.get('API3G', {})
            
            return {
                'success': api_response.get('Result') == '000',
                'message': api_response.get('ResultExplanation', ''),
                'full_response': api_response
            }
            
        except Exception as e:
            current_app.logger.error(f"Token cancellation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
```

### Next: Continue with Flask Routes...

---

