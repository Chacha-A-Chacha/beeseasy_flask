# Flask DPO Integration - Part 3: App Setup & Frontend

## Flask Application Initialization

### app/__init__.py

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()


def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name == 'production':
        app.config.from_object('config.ProductionConfig')
    elif config_name == 'testing':
        app.config.from_object('config.TestingConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Initialize services
    from app.services.email_service import EmailService
    email_service = EmailService()
    email_service.init_app(mail)
    
    # Register blueprints
    from app.routes.payments import payments_bp
    from app.routes.tickets import tickets_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(tickets_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
```

### config.py

```python
import os
from datetime import timedelta


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///event_ticketing.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # DPO Configuration
    DPO_COMPANY_TOKEN = os.getenv('DPO_COMPANY_TOKEN')
    DPO_SERVICE_TYPE = os.getenv('DPO_SERVICE_TYPE')
    DPO_CURRENCY = os.getenv('DPO_CURRENCY', 'TZS')
    DPO_TEST_MODE = os.getenv('DPO_TEST_MODE', 'True').lower() == 'true'
    
    # Email configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Event Configuration
    EVENT_NAME = os.getenv('EVENT_NAME', 'Tanzania Tech Summit 2025')
    EVENT_DATE = os.getenv('EVENT_DATE', '2025-03-15')
    EVENT_LOCATION = os.getenv('EVENT_LOCATION', 'Dar es Salaam, Tanzania')
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Use PostgreSQL in production
    # SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
```

### run.py

```python
from app import create_app
import os

# Get environment from ENV variable (development, production, testing)
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True if config_name == 'development' else False
    )
```

---

## Frontend Templates

### app/templates/checkout.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Checkout - {{ config.EVENT_NAME }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .subtitle {
            color: #718096;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #4a5568;
            font-weight: 500;
        }
        
        input, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .price-display {
            background: #f7fafc;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        .price-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            color: #4a5568;
        }
        
        .price-row.total {
            font-size: 20px;
            font-weight: bold;
            color: #2d3748;
            padding-top: 10px;
            border-top: 2px solid #e2e8f0;
            margin-top: 10px;
        }
        
        .btn {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error {
            background: #fed7d7;
            color: #c53030;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            display: none;
        }
        
        .error.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎟️ Purchase Ticket</h1>
        <p class="subtitle">{{ config.EVENT_NAME }}</p>
        
        <div id="error-message" class="error"></div>
        
        <form id="checkout-form">
            <div class="form-group">
                <label for="ticket_type">Ticket Type</label>
                <select id="ticket_type" name="ticket_type" required>
                    <option value="">Select ticket type</option>
                    <option value="VIP" data-price="150000">VIP - TZS 150,000</option>
                    <option value="Regular" data-price="50000">Regular - TZS 50,000</option>
                    <option value="Student" data-price="20000">Student - TZS 20,000</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="quantity">Quantity</label>
                <input type="number" id="quantity" name="quantity" min="1" max="10" value="1" required>
            </div>
            
            <div class="form-group">
                <label for="attendee_name">Full Name</label>
                <input type="text" id="attendee_name" name="attendee_name" placeholder="John Doe" required>
            </div>
            
            <div class="form-group">
                <label for="attendee_email">Email Address</label>
                <input type="email" id="attendee_email" name="attendee_email" placeholder="john@example.com" required>
            </div>
            
            <div class="form-group">
                <label for="attendee_phone">Phone Number</label>
                <input type="tel" id="attendee_phone" name="attendee_phone" placeholder="+255712345678" required>
            </div>
            
            <div class="price-display">
                <div class="price-row">
                    <span>Ticket Price:</span>
                    <span id="unit-price">TZS 0</span>
                </div>
                <div class="price-row">
                    <span>Quantity:</span>
                    <span id="quantity-display">1</span>
                </div>
                <div class="price-row total">
                    <span>Total:</span>
                    <span id="total-price">TZS 0</span>
                </div>
            </div>
            
            <button type="submit" class="btn" id="checkout-btn">
                Proceed to Payment
            </button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Redirecting to payment gateway...</p>
        </div>
    </div>
    
    <script>
        // Price calculation
        const ticketSelect = document.getElementById('ticket_type');
        const quantityInput = document.getElementById('quantity');
        const unitPriceEl = document.getElementById('unit-price');
        const quantityDisplayEl = document.getElementById('quantity-display');
        const totalPriceEl = document.getElementById('total-price');
        
        function updatePrice() {
            const selectedOption = ticketSelect.options[ticketSelect.selectedIndex];
            const price = parseInt(selectedOption.dataset.price || 0);
            const quantity = parseInt(quantityInput.value || 1);
            const total = price * quantity;
            
            unitPriceEl.textContent = `TZS ${price.toLocaleString()}`;
            quantityDisplayEl.textContent = quantity;
            totalPriceEl.textContent = `TZS ${total.toLocaleString()}`;
        }
        
        ticketSelect.addEventListener('change', updatePrice);
        quantityInput.addEventListener('input', updatePrice);
        
        // Form submission
        const form = document.getElementById('checkout-form');
        const errorEl = document.getElementById('error-message');
        const loadingEl = document.getElementById('loading');
        const btnEl = document.getElementById('checkout-btn');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Hide error
            errorEl.classList.remove('active');
            
            // Get form data
            const formData = {
                ticket_type: document.getElementById('ticket_type').value,
                quantity: parseInt(document.getElementById('quantity').value),
                attendee_name: document.getElementById('attendee_name').value,
                attendee_email: document.getElementById('attendee_email').value,
                attendee_phone: document.getElementById('attendee_phone').value
            };
            
            // Disable button and show loading
            btnEl.disabled = true;
            loadingEl.classList.add('active');
            
            try {
                const response = await fetch('/payments/initiate/ticket', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Redirect to DPO payment page
                    window.location.href = result.payment_url;
                } else {
                    // Show error
                    errorEl.textContent = result.error || 'Payment initiation failed';
                    errorEl.classList.add('active');
                    btnEl.disabled = false;
                    loadingEl.classList.remove('active');
                }
            } catch (error) {
                errorEl.textContent = 'An error occurred. Please try again.';
                errorEl.classList.add('active');
                btnEl.disabled = false;
                loadingEl.classList.remove('active');
            }
        });
    </script>
</body>
</html>
```

### app/templates/payment_success.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Successful</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            max-width: 600px;
            background: white;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .success-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        
        h1 {
            color: #2d3748;
            margin-bottom: 10px;
        }
        
        .message {
            color: #48bb78;
            font-size: 18px;
            margin-bottom: 30px;
        }
        
        .ticket-card {
            background: #f7fafc;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: left;
        }
        
        .ticket-info {
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
        }
        
        .qr-code {
            margin: 20px 0;
        }
        
        .qr-code img {
            max-width: 200px;
        }
        
        .btn {
            display: inline-block;
            padding: 12px 30px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin: 10px 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>Payment Successful!</h1>
        <p class="message">{{ message }}</p>
        
        {% if tickets %}
            <h2>Your Tickets</h2>
            {% for ticket in tickets %}
            <div class="ticket-card">
                <div class="ticket-info">
                    <strong>Ticket Number:</strong>
                    <span>{{ ticket.ticket_number }}</span>
                </div>
                <div class="ticket-info">
                    <strong>Type:</strong>
                    <span>{{ ticket.ticket_type }}</span>
                </div>
                <div class="ticket-info">
                    <strong>Attendee:</strong>
                    <span>{{ ticket.attendee_name }}</span>
                </div>
                {% if ticket.qr_code %}
                <div class="qr-code">
                    <img src="{{ ticket.qr_code }}" alt="QR Code">
                </div>
                {% endif %}
            </div>
            {% endfor %}
            
            <p>A confirmation email has been sent to {{ payment.customer_email }}</p>
        {% endif %}
        
        {% if booth %}
            <div class="ticket-card">
                <div class="ticket-info">
                    <strong>Booth Number:</strong>
                    <span>{{ booth.booth_number }}</span>
                </div>
                <div class="ticket-info">
                    <strong>Company:</strong>
                    <span>{{ booth.company_name }}</span>
                </div>
                <div class="ticket-info">
                    <strong>Size:</strong>
                    <span>{{ booth.booth_size }}</span>
                </div>
            </div>
            
            <p>A confirmation email has been sent to {{ payment.customer_email }}</p>
        {% endif %}
        
        <a href="/" class="btn">Back to Home</a>
    </div>
</body>
</html>
```

---

## Complete Usage Guide

### 1. Initial Setup

```bash
# Clone/create your project
mkdir event-ticketing
cd event-ticketing

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your DPO credentials
nano .env
```

### 2. Configure DPO Credentials

Get your credentials from DPO:
1. Contact DPO sales: support@dpogroup.com or +255 677 335 555
2. Request Company Token and Service Type
3. Update `.env` file:

```env
DPO_COMPANY_TOKEN=YOUR-ACTUAL-COMPANY-TOKEN
DPO_SERVICE_TYPE=YOUR-SERVICE-TYPE
DPO_TEST_MODE=True  # Set to False for production
```

### 3. Initialize Database

```bash
# Initialize Flask-Migrate
flask db init

# Create migration
flask db migrate -m "Initial migration"

# Apply migration
flask db upgrade
```

### 4. Run Development Server

```bash
python run.py
```

Visit: http://localhost:5000

### 5. Test Payment Flow

```bash
# Test ticket purchase
curl -X POST http://localhost:5000/payments/initiate/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_type": "Regular",
    "quantity": 1,
    "attendee_name": "John Doe",
    "attendee_email": "john@example.com",
    "attendee_phone": "+255712345678"
  }'
```

Response:
```json
{
  "success": true,
  "payment_id": 1,
  "payment_url": "https://secure1.sandbox.directpay.online/payv2.php?ID=xxx",
  "trans_ref": "1285DB12G",
  "amount": 50000.0,
  "currency": "TZS"
}
```

### 6. Configure Webhook

Contact DPO to set your webhook URL:
```
https://yourdomain.com/payments/webhook
```

For local testing, use ngrok:
```bash
ngrok http 5000
# Use the https URL: https://abc123.ngrok.io/payments/webhook
```

---

## Production Deployment

### 1. Use Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### 2. Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Environment Variables

```bash
export FLASK_ENV=production
export DPO_TEST_MODE=False
export DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### 4. SSL Certificate

```bash
sudo certbot --nginx -d yourdomain.com
```

---

## Key Implementation Notes

### Payment Flow Summary:

1. **User initiates payment** → POST to `/payments/initiate/ticket` or `/payments/initiate/booth`
2. **Flask creates DPO token** → Calls DPO createToken API
3. **User redirected to DPO** → Shows payment options (M-Pesa, Cards, etc.)
4. **User completes payment** → DPO processes payment
5. **DPO redirects back** → GET to `/payments/callback?TransactionToken=xxx`
6. **Flask verifies payment** → Calls DPO verifyToken API
7. **Update database** → Confirm tickets/booths, generate QR codes
8. **Send email** → Confirmation with ticket details
9. **Webhook notification** → DPO POSTs to `/payments/webhook` (backup)

### Security Best Practices:

- Always verify payment status with `verifyToken` before confirming
- Store complete DPO responses for audit trail
- Use HTTPS in production
- Validate all input data
- Rate limit payment initiation endpoints
- Log all payment transactions
- Monitor for duplicate callbacks

### Error Handling:

- Network timeouts: Retry verification
- Duplicate payments: Check `company_ref` uniqueness
- Callback delays: Use webhook as backup
- Email failures: Queue for retry

---

This completes the full Flask + DPO integration!

**Ready to deploy? Checklist:**
- ✅ DPO credentials obtained
- ✅ Environment variables configured
- ✅ Database initialized
- ✅ Email service configured
- ✅ Webhook URL registered with DPO
- ✅ SSL certificate installed
- ✅ Test payment completed successfully

Need help? Contact: support@dpogroup.com
