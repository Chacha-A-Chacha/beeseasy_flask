# Registration & Payment Workflow Audit Report
**Date:** 2024
**System:** BEEASY Flask Registration System

---

## Executive Summary

This audit traces the complete registration workflow from initial signup through payment processing with DPO. The analysis identifies the flow of ticket/package prices and payment amounts, highlighting several inconsistencies and potential issues.

### Critical Findings:
1. ✅ **Payment amounts are correctly passed to DPO**
2. ⚠️ **Tax is calculated in one endpoint but never applied to actual payments**
3. ⚠️ **Currency mismatch between attendee (USD) and exhibitor (TZS) products**
4. ⚠️ **Potential price drift between registration and checkout**

---

## 1. Registration Flow Overview

### 1.1 Attendee Registration Path
```
/register/attendee (Landing Page)
    ↓ User selects ticket type
/register/attendee/form (Registration Form)
    ↓ Form submission
RegistrationService.register_attendee()
    ↓ Creates AttendeeRegistration + Payment
/register/confirmation/<ref> (Confirmation Page)
    ↓ User clicks "Proceed to Payment"
/payments/checkout/<ref> (Checkout Page)
    ↓ User selects payment method
/payments/dpo_initiate/<ref> (DPO Initiation)
    ↓ Redirects to DPO payment page
DPO Payment Gateway
    ↓ Payment completion
/payments/dpo_callback (Callback Handler)
```

### 1.2 Exhibitor Registration Path
```
/register/exhibitor (Landing Page)
    ↓ User selects package type
/register/exhibitor/form (Registration Form)
    ↓ Form submission
RegistrationService.register_exhibitor()
    ↓ Creates ExhibitorRegistration + Payment
/register/confirmation/<ref> (Confirmation Page)
    ↓ Same as attendee flow onwards
```

---

## 2. Price Calculation Flow

### 2.1 Initial Registration (RegistrationService._create_payment)

**Location:** `app/services/registration_service.py:365-390`

```python
def _create_payment(registration) -> Payment:
    total_amount = registration.get_total_amount_due()
    
    payment = Payment(
        registration_id=registration.id,
        subtotal=total_amount,           # ← Base amount
        tax_amount=Decimal("0.00"),      # ← TAX IS ALWAYS ZERO!
        total_amount=total_amount,       # ← Same as subtotal
        currency=currency,
        payment_status=PaymentStatus.PENDING,
    )
```

**Issue:** Tax is hardcoded to 0.00 and never calculated.

### 2.2 Base Price Calculation

#### For Attendees (`AttendeeRegistration.get_base_price()`)
**Location:** `app/models/registration.py:970-986`

```python
def get_base_price(self) -> Decimal:
    if self.ticket_price:
        return Decimal(str(self.ticket_price.price))
    return Decimal("0.00")

def get_total_amount_due(self) -> Decimal:
    base_price = self.get_base_price()
    addons_total = sum(addon.total_price for addon in self.addon_purchases)
    return base_price + addons_total
```

**Ticket Prices (from seeds.py):**
- Standard: **$300.00 USD**
- Student: **$200.00 USD**
- Group: **$500.00 USD**
- VIP: **$600.00 USD**

#### For Exhibitors (`ExhibitorRegistration.get_base_price()`)
**Location:** `app/models/registration.py:1070-1110`

```python
def get_base_price(self) -> Decimal:
    if self.package_price:
        return Decimal(str(self.package_price.price))
    return Decimal("0.00")

def get_total_amount_due(self) -> Decimal:
    base_price = self.get_base_price()
    addons_total = sum(addon.total_price for addon in self.addon_purchases)
    return base_price + addons_total
```

**Package Prices (from seeds.py):**
- Bronze: **625,000.00 TZS**
- Silver: **1,250,000.00 TZS**
- Gold: **3,125,000.00 TZS**
- Platinum: **6,250,000.00 TZS**
- Custom: **0.00 TZS**

### 2.3 Promo Code Discount

**Location:** `app/services/registration_service.py:393-441`

```python
def _apply_promo_code(registration, payment: Payment, promo_code: str):
    discount = promo.calculate_discount(payment.subtotal)
    
    payment.discount_amount = discount
    payment.total_amount = payment.subtotal - discount  # ← Updated total
```

**Result:** `payment.total_amount` is correctly reduced by discount amount.

---

## 3. Confirmation Page Display

**Location:** `app/templates/register/confirmation.html:466-512`

### What's Shown to User:

```html
<!-- Payment Summary Card -->
<span>Ticket Price</span>
<span>{{ payment.currency }} {{ "%.2f"|format(payment.total_amount) }}</span>

<!-- Amount Due -->
<span>Amount Due</span>
<span>{{ payment.currency }} {{ "%.2f"|format(balance_due) }}</span>
```

**Variables:**
- `payment.total_amount` - Amount from Payment record (with discount applied)
- `balance_due` - Calculated via `registration.get_balance_due()`

### Balance Due Calculation

**Location:** `app/models/registration.py:672-680`

```python
def get_balance_due(self) -> Decimal:
    total_due = self.get_total_amount_due()      # ← Recalculates from current prices!
    total_paid = self.get_total_paid()           # ← Sum of completed payments
    total_refunded = self.get_total_refunded()
    return total_due - (total_paid - total_refunded)
```

**⚠️ ISSUE:** If ticket/package prices are changed in the database after registration but before payment, `balance_due` will differ from `payment.total_amount`!

---

## 4. Checkout Page Display

**Location:** `app/templates/payments/checkout.html:400-460`

### What's Shown to User:

```html
<!-- Price Breakdown -->
<div>Ticket Price</div>
<div>{{ payment.currency }} {{ "%.2f"|format(payment.subtotal or payment.total_amount) }}</div>

<!-- Discount (if applicable) -->
<div>Discount</div>
<div>-{{ payment.currency }} {{ "%.2f"|format(payment.discount_amount) }}</div>

<!-- Tax (never shown because always 0) -->
{% if payment.tax_amount and payment.tax_amount > 0 %}
<div>Tax</div>
<div>{{ payment.currency }} {{ "%.2f"|format(payment.tax_amount) }}</div>
{% endif %}

<!-- Total Amount -->
<div>Total Amount</div>
<div>{{ "%.2f"|format(balance_due) }}</div>
```

**Displayed Amounts:**
- Subtotal: `payment.subtotal` or `payment.total_amount`
- Discount: `payment.discount_amount` (if > 0)
- Tax: Never displayed (always 0)
- **Total: `balance_due`** ← This is what user expects to pay

---

## 5. DPO Payment Initiation

**Location:** `app/routes/payment.py:269-367`

### What's Sent to DPO:

```python
payment_data = {
    "amount": float(payment.total_amount),           # ← FROM PAYMENT RECORD
    "currency": payment.currency,                    # ← TZS or USD
    "company_ref": payment.payment_reference,
    "customer_name": f"{registration.first_name} {registration.last_name}",
    "customer_email": registration.email,
    "customer_phone": f"{registration.phone_country_code}{registration.phone_number}",
    "service_description": "BEEASY2025 - Registration",
    "payment_type": payment_type,  # mpesa, tigo, airtel, card
}

result = dpo_service.create_token(payment_data)
```

### DPO XML Request

**Location:** `app/services/dpo_service.py:400-502`

```xml
<API3G>
    <CompanyToken>{company_token}</CompanyToken>
    <Transaction>
        <PaymentAmount>{payment_data["amount"]}</PaymentAmount>      <!-- ← payment.total_amount -->
        <PaymentCurrency>{currency}</PaymentCurrency>                <!-- ← payment.currency -->
        <CompanyRef>{payment.payment_reference}</CompanyRef>
        <customerEmail>{customer_email}</customerEmail>
        ...
    </Transaction>
</API3G>
```

**✅ CORRECT:** The exact amount from `payment.total_amount` is sent to DPO.

---

## 6. DPO Payment Summary Display

**Location:** `app/templates/payments/dpo_select.html:102-120`

```html
<!-- Amount Due -->
<div>Amount Due</div>
<div>{{ payment.currency }}</div>
<div>{{ "%.2f"|format(payment.total_amount) }}</div>  <!-- ← Matches DPO amount -->
```

**✅ CORRECT:** User sees the same amount that will be charged.

---

## 7. Issues & Inconsistencies

### 7.1 🔴 CRITICAL: Tax Not Applied

**Problem:** 
- Tax is hardcoded to `Decimal("0.00")` in `_create_payment()`
- There's an API endpoint `/api/calculate-total` that calculates 16% tax
- But this endpoint is **never called** by any frontend code
- Tax is never added to payment amounts

**Location of unused tax calculation:**
`app/routes/register.py:447-476`

```python
@register_bp.route("/api/calculate-total", methods=["POST"])
def calculate_total():
    # Calculate tax
    tax_rate = Decimal("0.16")
    tax = subtotal_after_discount * tax_rate
    total = subtotal_after_discount + tax
```

**Impact:**
- If tax should be collected, all payments are missing 16% tax
- For a $300 ticket: Missing $48 in tax
- For a TZS 625,000 package: Missing TZS 100,000 in tax

**Recommendation:**
1. **If tax is required:** Integrate tax calculation into `_create_payment()` method
2. **If tax is not required:** Remove the unused `calculate_total` endpoint and tax fields from Payment model

### 7.2 ⚠️ MEDIUM: Price Drift Risk

**Problem:**
- `payment.total_amount` is stored at registration time
- `balance_due` is calculated from current ticket/package prices
- If prices change between registration and checkout, amounts differ

**Example Scenario:**
1. User registers when Standard ticket is $300
2. Payment record stores `total_amount = 300.00`
3. Admin updates Standard ticket to $350
4. User proceeds to checkout
5. Confirmation page shows `balance_due = $350` (from current price)
6. But DPO receives `amount = $300` (from stored payment)

**Current Code:**
```python
# At registration time (stored):
payment.total_amount = 300.00

# At checkout time (calculated):
balance_due = registration.get_total_amount_due()  # ← Gets CURRENT price ($350)
```

**Recommendation:**
- Use `payment.total_amount` consistently (already stored amount)
- Or lock prices at registration time and don't allow updates to active ticket prices

### 7.3 ⚠️ MEDIUM: Currency Inconsistency

**Problem:**
- Attendee tickets use **USD**
- Exhibitor packages use **TZS**
- DPO must handle both currencies
- No exchange rate handling if user
