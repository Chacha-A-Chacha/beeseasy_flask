# DPO Payment Gateway Integration Guide

## Overview

This guide covers the integration of DPO Group payment gateway for handling payments in Tanzania, including:
- **Mobile Money**: M-Pesa (Vodacom), Tigo Pesa, Airtel Money
- **Card Payments**: Visa, Mastercard, American Express
- **Multi-currency support**: TZS (Tanzania Shillings), USD, KES, etc.

---

## Quick Start

### 1. Get DPO Credentials

Contact DPO Group to obtain your credentials:
- **Email**: support@dpogroup.com
- **Phone**: +255 677 335 555
- **Website**: https://dpogroup.com

You will receive:
- `CompanyToken` - Your unique merchant identifier
- `ServiceType` - Your service type code

### 2. Configure Environment Variables

Update your `.env` file with DPO credentials:

```env
# DPO Payment Gateway
DPO_COMPANY_TOKEN=your-dpo-company-token-here
DPO_SERVICE_TYPE=your-service-type-here
DPO_CURRENCY=TZS
DPO_TEST_MODE=True

# DPO Callback URLs (update with your domain)
DPO_REDIRECT_URL=https://yourdomain.com/payments/dpo/callback
DPO_BACK_URL=https://yourdomain.com/payments/cancel
```

**For Local Development:**
```env
DPO_REDIRECT_URL=http://localhost:5000/payments/dpo/callback
DPO_BACK_URL=http://localhost:5000/payments/cancel
```

**For Production with ngrok (testing):**
```env
DPO_REDIRECT_URL=https://abc123.ngrok.io/payments/dpo/callback
DPO_BACK_URL=https://abc123.ngrok.io/payments/cancel
```

### 3. Install Dependencies

The DPO service requires these packages (already in requirements.txt):

```bash
pip install requests==2.31.0
pip install xmltodict==0.13.0
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DPO_COMPANY_TOKEN` | Yes | - | Your DPO company token |
| `DPO_SERVICE_TYPE` | Yes | - | Your service type code |
| `DPO_CURRENCY` | No | TZS | Payment currency (TZS, USD, KES, etc.) |
| `DPO_TEST_MODE` | No | True | Use sandbox (True) or live (False) |
| `DPO_REDIRECT_URL` | Yes | - | Where DPO redirects after payment |
| `DPO_BACK_URL` | Yes | - | Where user goes if they cancel |
| `DPO_PAYMENT_TOKEN_LIFETIME` | No | 5 | Token validity in hours |

### Config.py Settings

All DPO configuration is loaded in `app/config.py`:

```python
# DPO Payment Gateway
DPO_COMPANY_TOKEN: str | None = os.getenv("DPO_COMPANY_TOKEN")
DPO_SERVICE_TYPE: str | None = os.getenv("DPO_SERVICE_TYPE")
DPO_CURRENCY: str = os.getenv("DPO_CURRENCY", "TZS")
DPO_TEST_MODE: bool = os.getenv("DPO_TEST_MODE", "True").lower() == "true"
```

---

## DPO Service Usage

### Initialize Service

The DPO service is initialized in your Flask app:

```python
from app.services.dpo_service import dpo_service

# In app/__init__.py or app factory
dpo_service.init_app(app)
```

### Create Payment Token

```python
from app.services.dpo_service import dpo_service

# Prepare payment data
payment_data = {
    'amount': 150000.00,  # Amount in TZS
    'company_ref': payment.payment_reference,  # Must be unique!
    'customer_name': 'John Doe',
    'customer_email': 'john@example.com',
    'customer_phone': '+255712345678',
    'service_description': 'VIP Ticket - Pollination Africa Symposium 2026',
    'service_date': '2026-06-03',
    'payment_type': 'mpesa'  # Optional: mpesa, tigo, airtel, card
}

# Create token
result = dpo_service.create_token(payment_data)

if result['success']:
    # Redirect user to DPO payment page
    payment_url = result['payment_url']
    trans_token = result['trans_token']
    trans_ref = result['trans_ref']
    
    # Save to database
    payment.trans_token = trans_token
    payment.trans_ref = trans_ref
    payment.payment_url = payment_url
    db.session.commit()
    
    # Redirect user
    return redirect(payment_url)
else:
    # Handle error
    error_message = result['error']
    flash(f'Payment initialization failed: {error_message}', 'error')
```

### Verify Payment (Callback)

After user completes payment, DPO redirects to your callback URL with `TransactionToken`:

```python
from flask import request
from app.services.dpo_service import dpo_service

@payments_bp.route('/dpo/callback')
def dpo_callback():
    # Get transaction token from URL
    trans_token = request.args.get('TransactionToken')
    
    # Find payment record
    payment = Payment.query.filter_by(trans_token=trans_token).first()
    
    # Verify with DPO
    verification = dpo_service.verify_token(trans_token)
    
    if verification['success'] and verification['status'] == 'Approved':
        # Payment successful!
        payment.status = 'approved'
        payment.completed_at = datetime.utcnow()
        payment.payment_method = verification['payment_method']
        
        # Mark registration as confirmed
        registration.status = RegistrationStatus.CONFIRMED
        
        # Generate badge, send email, etc.
        # ... (call RegistrationService.process_payment_completion)
        
        db.session.commit()
        
        return render_template('payment_success.html', payment=payment)
    else:
        # Payment failed
        payment.status = 'declined'
        db.session.commit()
        
        return render_template('payment_failed.html', 
                             error=verification.get('error'))
```

---

## Payment Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Selects Ticket/Package                             │
│    ↓                                                        │
│ 2. Fills Registration Form                                 │
│    ↓                                                        │
│ 3. Clicks "Proceed to Payment"                             │
│    ↓                                                        │
│ 4. Selects Payment Method (M-Pesa/Tigo/Airtel/Card)       │
│    ↓                                                        │
│ 5. Flask: Create DPO Token (createToken API)              │
│    └─> Stores: trans_token, trans_ref, payment_url        │
│    ↓                                                        │
│ 6. Redirect to DPO Payment Page                            │
│    └─> User sees payment options                           │
│    ↓                                                        │
│ 7. User Completes Payment                                  │
│    └─> M-Pesa prompt / Card form / etc.                   │
│    ↓                                                        │
│ 8. DPO Redirects to Callback URL                           │
│    └─> /payments/dpo/callback?TransactionToken=xxx        │
│    ↓                                                        │
│ 9. Flask: Verify Payment (verifyToken API)                │
│    └─> Checks if payment successful                        │
│    ↓                                                        │
│ 10. Update Database                                        │
│     ├─> Mark payment as completed                          │
│     ├─> Confirm registration                               │
│     ├─> Generate badge PDF                                 │
│     └─> Send confirmation email                            │
│    ↓                                                        │
│ 11. Show Success Page with Badge Download                  │
└─────────────────────────────────────────────────────────────┘
```

---

## API Methods

### dpo_service.create_token(payment_data)

Creates a payment token and returns payment URL.

**Parameters:**
```python
payment_data = {
    'amount': float,              # Required
    'company_ref': str,           # Required - Must be unique!
    'customer_name': str,         # Required
    'customer_email': str,        # Required
    'customer_phone': str,        # Required - Format: +255XXXXXXXXX
    'service_description': str,   # Required
    'service_date': str,          # Optional - Event date
    'payment_type': str          # Optional - mpesa, tigo, airtel, card
}
```

**Returns:**
```python
{
    'success': bool,
    'trans_token': str,          # DPO transaction token
    'trans_ref': str,            # DPO reference number
    'payment_url': str,          # URL to redirect user
    'error': str,                # (if failed)
    'full_response': dict        # Complete DPO response
}
```

### dpo_service.verify_token(trans_token)

Verifies payment status after user completes payment.

**Parameters:**
- `trans_token` (str): Transaction token from DPO

**Returns:**
```python
{
    'success': bool,
    'status': str,               # Approved / Declined
    'customer_name': str,
    'customer_phone': str,
    'payment_method': str,       # M-Pesa, Visa, etc.
    'amount': float,
    'currency': str,
    'trans_ref': str,
    'error': str,                # (if failed)
    'full_response': dict
}
```

### dpo_service.cancel_token(trans_token)

Cancels a payment token (optional - for cleanup).

**Parameters:**
- `trans_token` (str): Transaction token to cancel

**Returns:**
```python
{
    'success': bool,
    'message': str,
    'full_response': dict
}
```

### dpo_service.is_configured()

Checks if DPO service has all required credentials.

**Returns:**
- `bool`: True if configured properly

### dpo_service.get_supported_payment_methods()

Returns dictionary of supported payment methods.

**Returns:**
```python
{
    'mpesa': {'name': 'M-Pesa (Vodacom)', 'type': 'mobile_money', ...},
    'tigo': {'name': 'Tigo Pesa', 'type': 'mobile_money', ...},
    'airtel': {'name': 'Airtel Money', 'type': 'mobile_money', ...},
    'card': {'name': 'Credit/Debit Card', 'type': 'card', ...}
}
```

---

## Testing

### Test Mode vs Production

**Test Mode (Sandbox):**
- Set `DPO_TEST_MODE=True`
- Uses: `https://secure.3gdirectpay.com`
- Use test Company Token provided by DPO
- Test card numbers available from DPO
- No real money charged

**Production (Live):**
- Set `DPO_TEST_MODE=False`
- Uses: `https://secure.3gdirectpay.com`
- Use live Company Token provided by DPO
- Real payments processed

**Note:** DPO uses the same API endpoint URL for both test and live environments. The difference is in the **Company Token** credentials you use, not the URL.

### Local Testing with ngrok

For DPO to reach your local callback URL:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start ngrok tunnel
ngrok http 5000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Update .env:
DPO_REDIRECT_URL=https://abc123.ngrok.io/payments/dpo/callback
DPO_BACK_URL=https://abc123.ngrok.io/payments/cancel
```

### Test Payment Flow

1. Create a test registration
2. Select payment method
3. Get redirected to DPO sandbox
4. Use test M-Pesa number or test card
5. Complete payment
6. Verify callback received
7. Check database updated correctly

---

## Webhook Integration (Advanced)

DPO also supports webhooks for more reliable payment notifications:

```python
@payments_bp.route('/dpo/webhook', methods=['POST'])
def dpo_webhook():
    # Parse XML from DPO
    xml_data = request.data.decode('utf-8')
    data = xmltodict.parse(xml_data)
    
    trans_token = data.get('API3G', {}).get('TransactionToken')
    
    # Verify and process payment
    verification = dpo_service.verify_token(trans_token)
    
    # Process payment...
    
    return jsonify({'status': 'success'}), 200
```

**Register webhook with DPO:**
Contact DPO support to register:
```
https://yourdomain.com/payments/dpo/webhook
```

---

## Security Best Practices

1. **Always Verify Payments**
   - Never trust redirect alone
   - Always call `verify_token()` before confirming

2. **Use HTTPS in Production**
   - DPO requires HTTPS for callback URLs
   - Get SSL certificate (Let's Encrypt, Cloudflare)

3. **Unique CompanyRef**
   - Use `payment.payment_reference` (already unique)
   - DPO rejects duplicate references

4. **Store Full Responses**
   - Save `full_response` for audit trail
   - Helps with debugging and disputes

5. **Handle Timeouts**
   - Mobile money can take 5-10 minutes
   - Implement payment status polling if needed

6. **Validate Callback**
   - Check trans_token exists in your database
   - Verify payment amount matches

---

## Troubleshooting

### Error: "CompanyToken not configured"

**Solution**: Add DPO credentials to `.env`:
```env
DPO_COMPANY_TOKEN=your-token-here
DPO_SERVICE_TYPE=your-service-type
```

### Error: "Payment gateway connection error"

**Causes:**
- No internet connection
- DPO API down
- Firewall blocking requests

**Solution**: Check connectivity, try again later

### Error: "CompanyRef already exists"

**Cause**: Duplicate payment reference

**Solution**: Ensure `payment.payment_reference` is unique (already handled in models)

### Payment shows pending forever

**Causes:**
- User didn't complete M-Pesa prompt
- Network timeout
- User cancelled

**Solution**: Implement token expiry (default 5 hours)

### Callback not received

**Causes:**
- Wrong callback URL
- URL not accessible (localhost without ngrok)
- HTTPS required in production

**Solution**:
- Verify `DPO_REDIRECT_URL` is correct
- Use ngrok for local testing
- Enable HTTPS for production

---

## Production Deployment Checklist

- [ ] Obtain production DPO credentials
- [ ] Set `DPO_TEST_MODE=False`
- [ ] Update callback URLs to production domain
- [ ] Enable HTTPS with SSL certificate
- [ ] Register webhook URL with DPO
- [ ] Test full payment flow in production
- [ ] Set up monitoring/logging for payments
- [ ] Configure email notifications
- [ ] Document payment reconciliation process

---

## Support

**DPO Group:**
- Email: support@dpogroup.com
- Phone: +255 677 335 555
- Website: https://dpogroup.com

**Documentation:**
- DPO Developer Resources: https://dpogroup.com/developer-resources/

**Your App Support:**
- Email: info@pollination.africa
- Phone: +254 719 740 938
