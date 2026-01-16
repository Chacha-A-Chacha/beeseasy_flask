# DPO-Only Payment Implementation Plan

**Date**: 2025-12-04  
**Status**: Planning Phase  
**Priority**: HIGH

## Executive Summary

This document outlines the comprehensive implementation plan for transitioning the BEEASY Flask event registration system to use **DPO (Direct Pay Online) as the sole payment gateway**, putting Stripe and manual payment methods on hold. This strategic shift simplifies the payment architecture and focuses on Tanzania's mobile money ecosystem.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Strategic Decision: DPO-Only Approach](#strategic-decision-dpo-only-approach)
3. [Payment Methods via DPO](#payment-methods-via-dpo)
4. [Architecture Changes](#architecture-changes)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Database Schema Updates](#database-schema-updates)
7. [Route Structure](#route-structure)
8. [Template Modifications](#template-modifications)
9. [Configuration Priority](#configuration-priority)
10. [Testing Strategy](#testing-strategy)
11. [Migration Plan](#migration-plan)
12. [Rollback Strategy](#rollback-strategy)

---

## Current State Analysis

### Existing Payment Infrastructure

**Payment Models** (`app/models/payment.py`):
- ✅ Payment model with comprehensive fields
- ✅ Stripe-specific fields: `stripe_payment_intent_id`, `stripe_checkout_session_id`, `stripe_customer_id`, `stripe_charge_id`, `stripe_refund_id`
- ⚠️ **Missing DPO-specific fields**: `trans_token`, `trans_ref`, `dpo_response`
- ✅ Generic fields available: `transaction_id`, `gateway_response` (JSON), `payment_metadata` (JSON)

**Current Routes** (`app/routes/payment.py`):
- `/checkout/<ref>` - Main checkout page (multi-gateway)
- `/select-method/<ref>` - Payment method selection handler
- `/stripe/checkout/<ref>` - Stripe integration (to be deprecated)
- `/stripe/webhook` - Stripe webhook handler (to be deprecated)
- `/mpesa/checkout/<ref>` - M-Pesa placeholder (different from DPO, to be removed)
- `/bank-transfer/<ref>` - Manual bank transfer (to be moved to "alternative")
- `/invoice/<ref>` - Manual invoice (to be moved to "alternative")

**Checkout Template** (`app/templates/payments/checkout.html`):
- ✅ Beautiful hero section matching design system
- ✅ Sticky order summary sidebar
- ✅ Dynamic rendering for attendee tickets vs exhibitor packages
- ⚠️ Shows 4 payment methods: Card (Stripe), Mobile Money, Bank Transfer, Invoice
- ⚠️ Needs simplification to show only DPO methods

**DPO Service** (`app/services/dpo_service.py`):
- ✅ Fully implemented with 600+ lines
- ✅ `create_token()` method for payment initialization
- ✅ `verify_token()` method for payment verification
- ✅ `cancel_token()` method
- ✅ XML request/response handling
- ✅ Support for M-Pesa, Tigo, Airtel mobile money
- ✅ Card payment support
- ⚠️ Basic error handling (only handles code "000")
- ⚠️ Not yet integrated into payment routes

**Configuration** (`app/config.py`):
- ✅ Complete DPO configuration section added
- ✅ Stripe configuration exists (will become optional)
- ⚠️ Priority not yet reflected in documentation

---

## Strategic Decision: DPO-Only Approach

### Why DPO-Only?

1. **Tanzania Mobile Money Ecosystem**: DPO natively supports M-Pesa (Vodacom), Tigo Pesa, and Airtel Money
2. **Simplified User Experience**: Single payment flow reduces decision fatigue
3. **Reduced Complexity**: One gateway to maintain, test, and support
4. **Local Currency Support**: Direct TZS (Tanzania Shillings) support without conversion
5. **Cost Efficiency**: Consolidate payment processing fees
6. **Faster Time to Market**: Focus on one integration done well

### What Happens to Other Payment Methods?

| Method | Current Status | New Status |
|--------|----------------|------------|
| **Stripe Card Payments** | Active | **Deprecated** - Keep code but disable routes |
| **Mobile Money (Standalone)** | Placeholder | **Removed** - Replaced by DPO mobile money |
| **Bank Transfer** | Active | **Alternative Payment** - Moved to separate "offline" section |
| **Invoice Request** | Active | **Alternative Payment** - Moved to separate "offline" section |

---

## Payment Methods via DPO

### Primary Payment Methods (via DPO)

1. **M-Pesa (Vodacom)**
   - Most popular mobile money in Tanzania
   - Real-time payment confirmation
   - DPO payment type: `mpesa`

2. **Tigo Pesa**
   - Second largest mobile money provider
   - Real-time payment confirmation
   - DPO payment type: `tigo`

3. **Airtel Money**
   - Growing mobile money provider
   - Real-time payment confirmation
   - DPO payment type: `airtel`

4. **Card Payments (Visa/Mastercard/Amex)**
   - Processed through DPO (not Stripe)
   - International card support
   - 3D Secure authentication
   - DPO payment type: `card` or unspecified (DPO shows all options)

### Alternative Payment Methods (Not via DPO)

These will be moved to a separate "Offline Payments" section:

- **Bank Transfer**: Manual verification required
- **Invoice Request**: For institutional/company payments

---

## Architecture Changes

### Simplified Payment Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REGISTRATION                         │
│                 (Attendee or Exhibitor)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    CHECKOUT PAGE                             │
│  Shows: Order Summary + DPO Payment Method Selection        │
│  Options:                                                    │
│    [●] M-Pesa                                               │
│    [ ] Tigo Pesa                                            │
│    [ ] Airtel Money                                         │
│    [ ] Credit/Debit Card                                    │
│                                                              │
│  Link: "Need offline payment?" → Alternative methods        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              DPO PAYMENT INITIATION                          │
│  Route: /payments/dpo/initiate/<ref>                        │
│  Action:                                                     │
│    1. Call dpo_service.create_token()                       │
│    2. Store trans_token in payment record                   │
│    3. Redirect user to DPO payment page                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  DPO HOSTED PAYMENT PAGE                     │
│                   (External - DPO domain)                    │
│  User completes payment:                                     │
│    - M-Pesa: Enter phone, receive STK push                  │
│    - Tigo: Enter phone, receive USSD prompt                 │
│    - Airtel: Enter phone, receive USSD prompt               │
│    - Card: Enter card details, 3D Secure                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              DPO CALLBACK (Redirect)                         │
│  Route: /payments/dpo/callback                              │
│  Query params: ?TransactionToken=xxx&CompanyRef=xxx         │
│  Action:                                                     │
│    1. Extract trans_token from query                        │
│    2. Call dpo_service.verify_token(trans_token)            │
│    3. Update payment status in database                     │
│    4. Redirect to success/failed page                       │
└─────────────────────────────────────────────────────────────┘
```

### Database Design

**Existing Fields to Use**:
- `transaction_id` → Store DPO `trans_ref`
- `gateway_response` (JSON) → Store full DPO response
- `payment_metadata` (JSON) → Store DPO-specific data

**Recommended Additional Fields** (optional enhancement):
```python
# DPO-specific fields (optional - can use existing JSON fields)
trans_token = db.Column(db.String(255), index=True)  # DPO transaction token
trans_ref = db.Column(db.String(255), index=True)    # DPO transaction reference
dpo_result_code = db.Column(db.String(10))           # DPO result code (000, 900, etc.)
dpo_result_explanation = db.Column(db.Text)          # Human-readable result
```

**Decision**: We can start WITHOUT adding new columns by using existing JSON fields:
```python
# Store in payment.payment_metadata
payment.payment_metadata = {
    'gateway': 'dpo',
    'trans_token': 'ABC123...',
    'trans_ref': 'DPO-REF-123',
    'result_code': '000',
    'result_explanation': 'Transaction Paid',
    'payment_type': 'mpesa',
    'customer_phone': '+255712345678'
}

# Store in payment.transaction_id
payment.transaction_id = 'DPO-REF-123'  # DPO trans_ref

# Store in payment.gateway_response
payment.gateway_response = {
    # Full DPO verifyToken XML response as dict
}
```

---

## Implementation Roadmap

### Phase 1: Route Setup (Priority 1)

**Files to Modify**: `app/routes/payment.py`

**New Routes to Add**:

```python
# ============================================
# DPO PAYMENT ROUTES
# ============================================

@payments_bp.route('/dpo/initiate/<ref>', methods=['POST'])
def dpo_initiate(ref):
    """
    Initiate DPO payment
    Receives: payment_type (mpesa, tigo, airtel, card, or None for all options)
    """
    # 1. Get registration and payment
    # 2. Prepare payment data for DPO
    # 3. Call dpo_service.create_token()
    # 4. Store trans_token in payment.payment_metadata
    # 5. Redirect user to DPO payment URL
    pass

@payments_bp.route('/dpo/callback')
def dpo_callback():
    """
    Handle DPO redirect callback after user completes payment
    Query params: ?TransactionToken=xxx&CompanyRef=xxx
    """
    # 1. Extract trans_token from query params
    # 2. Call dpo_service.verify_token(trans_token)
    # 3. Update payment status based on result_code
    # 4. Send confirmation email if successful
    # 5. Redirect to success/failed page
    pass

@payments_bp.route('/dpo/cancel')
def dpo_cancel():
    """
    Handle DPO back/cancel button
    User clicked "Cancel" on DPO payment page
    """
    # 1. Get registration from session or query param
    # 2. Mark payment as cancelled (optional)
    # 3. Redirect back to checkout with message
    pass

# Optional: Server-to-server notification (more reliable than redirect)
@payments_bp.route('/dpo/webhook', methods=['POST'])
def dpo_webhook():
    """
    Handle DPO server notification (if configured)
    More reliable than redirect callback
    """
    # 1. Parse DPO notification
    # 2. Verify signature/authenticity
    # 3. Update payment status
    # 4. Return 200 OK
    pass
```

**Routes to Deprecate** (comment out or add `@deprecated` decorator):
- `/stripe/checkout/<ref>`
- `/stripe/webhook`
- `/mpesa/checkout/<ref>` (replaced by DPO M-Pesa)
- `/mpesa/callback`

**Routes to Keep (Alternative Payments)**:
- `/bank-transfer/<ref>` - Move to alternative section
- `/invoice/<ref>` - Move to alternative section

### Phase 2: Checkout Template Update (Priority 1)

**File to Modify**: `app/templates/payments/checkout.html`

**Changes Required**:

1. **Update Payment Method Cards** (line ~287-380):
   - Remove: "Credit/Debit Card (Stripe)" option
   - Remove: Generic "Mobile Money" option
   - Add: 4 new DPO-specific payment cards:
     - **M-Pesa (Vodacom)** - Green theme, M-Pesa logo
     - **Tigo Pesa** - Blue theme, Tigo logo
     - **Airtel Money** - Red theme, Airtel logo
     - **Card Payment (via DPO)** - Keep existing card icon

2. **Update Form Action** (line ~282):
   ```html
   <!-- OLD -->
   <form method="POST" action="{{ url_for('payments.select_method', ref=registration.reference_number) }}">
   
   <!-- NEW -->
   <form method="POST" action="{{ url_for('payments.dpo_initiate', ref=registration.reference_number) }}">
   ```

3. **Add Alternative Payment Link** (after main payment cards):
   ```html
   <div class="mt-8 text-center p-4 bg-gray-50 rounded-lg border border-gray-200">
       <p class="text-sm text-gray-600 mb-2">
           Need to pay via bank transfer or request an invoice?
       </p>
       <a href="{{ url_for('payments.alternative_methods', ref=registration.reference_number) }}" 
          class="text-accent-orange hover:text-accent-yellow font-semibold">
           View Alternative Payment Methods →
       </a>
   </div>
   ```

4. **Update Submit Button** (line ~426):
   ```html
   <!-- Keep same design, but ensure it submits to dpo_initiate -->
   <button type="submit" class="...">
       <span class="flex items-center justify-center">
           <svg class="w-5 h-5 mr-2">...</svg>
           Proceed to DPO Payment
       </span>
   </button>
   ```

5. **Update Payment Method Values**:
   ```html
   <!-- OLD values: card, mobile_money, bank_transfer, invoice -->
   <!-- NEW values: mpesa, tigo, airtel, card -->
   
   <input type="radio" name="payment_type" value="mpesa" class="sr-only">
   <input type="radio" name="payment_type" value="tigo" class="sr-only">
   <input type="radio" name="payment_type" value="airtel" class="sr-only">
   <input type="radio" name="payment_type" value="card" class="sr-only">
   ```

### Phase 3: Alternative Payment Page (Priority 2)

**File to Create**: `app/templates/payments/alternative_methods.html`

**Purpose**: Show bank transfer and invoice options for users who can't use DPO

**Content**:
- Hero section matching design system
- Two clear options:
  1. Bank Transfer (with bank details)
  2. Invoice Request (with form)
- Link back to main checkout

### Phase 4: Configuration Priority Update (Priority 2)

**Files to Modify**:
- `app/config.py` - Add comments about DPO being primary
- `.env.example` - Reorganize to show DPO at top
- `README.md` - Update payment gateway documentation

**Changes**:

**`.env.example`**:
```env
# ============================================
# PRIMARY PAYMENT GATEWAY - DPO (Required)
# ============================================
DPO_COMPANY_TOKEN=your-dpo-company-token-here
DPO_SERVICE_TYPE=your-service-type-code
DPO_CURRENCY=TZS
DPO_TEST_MODE=True

# Note: DPO uses the same URL for both test and live - the difference is in the Company Token
DPO_API_URL_TEST=https://secure.3gdirectpay.com
DPO_API_URL_LIVE=https://secure.3gdirectpay.com

DPO_REDIRECT_URL=http://localhost:5000/payments/dpo/callback
DPO_BACK_URL=http://localhost:5000/payments/dpo/cancel

DPO_PAYMENT_TOKEN_LIFETIME=5

# ============================================
# DEPRECATED - Stripe (Currently Disabled)
# ============================================
# STRIPE_PUBLIC_KEY=pk_test_...
# STRIPE_SECRET_KEY=sk_test_...
# STRIPE_WEBHOOK_SECRET=whsec_...
```

**`app/config.py`** - Add comments:
```python
# ============================================
# PRIMARY PAYMENT GATEWAY - DPO (REQUIRED)
# ============================================
# DPO is the primary and only active payment gateway
# Supports: M-Pesa, Tigo Pesa, Airtel Money, Card payments
# ============================================
DPO_COMPANY_TOKEN: str | None = os.getenv("DPO_COMPANY_TOKEN")
# ... rest of DPO config

# ============================================
# DEPRECATED - Stripe (Currently Disabled)
# ============================================
# These are kept for potential future use but are not active
# ============================================
STRIPE_PUBLIC_KEY: str | None = os.getenv("STRIPE_PUBLIC_KEY")
# ... rest of Stripe config
```

### Phase 5: Enhanced Error Handling (Priority 3)

**File to Modify**: `app/services/dpo_service.py`

**Current Issue**: Only handles result code "000" (paid), treats all others as generic failure

**Enhancement Needed**: Handle all 11 DPO result codes properly

```python
# Current (in verify_token method)
if result_code == "000":
    return {
        'success': True,
        'status': 'paid',
        # ...
    }
else:
    return {
        'success': False,
        'status': 'failed',
        'error': result_explanation
    }

# Enhanced (to be implemented)
DPO_RESULT_CODES = {
    '000': ('paid', 'Transaction paid successfully', True),
    '001': ('authorized', 'Transaction authorized but not charged', True),
    '002': ('amount_mismatch', 'Amount paid does not match', False),
    '003': ('pending_bank', 'Waiting for bank confirmation', 'pending'),
    '005': ('queued', 'Authorization queued for processing', 'pending'),
    '900': ('not_paid', 'Transaction not paid yet', False),
    '901': ('declined', 'Transaction declined by payment provider', False),
    '903': ('expired', 'Transaction expired', False),
    '904': ('cancelled', 'Transaction cancelled by user', False),
}

def verify_token(self, trans_token: str) -> Dict:
    # ... existing code ...
    
    result_code = result.get('Result', '')
    result_explanation = result.get('ResultExplanation', 'Unknown')
    
    if result_code in DPO_RESULT_CODES:
        status_key, explanation, is_success = DPO_RESULT_CODES[result_code]
        
        return {
            'success': is_success if isinstance(is_success, bool) else False,
            'status': status_key,
            'result_code': result_code,
            'message': result_explanation,
            'is_pending': is_success == 'pending',
            # ... rest of data
        }
```

### Phase 6: Testing (Priority 1)

**Test Plan**:

1. **DPO Sandbox Testing**:
   - Test M-Pesa payment flow
   - Test Tigo Pesa payment flow
   - Test Airtel Money payment flow
   - Test Card payment flow (Visa, Mastercard)
   - Test payment cancellation
   - Test payment expiry

2. **Edge Cases**:
   - Network timeout during payment
   - User closes browser during payment
   - Duplicate payment attempts
   - Currency mismatch
   - Amount tampering

3. **User Experience**:
   - Mobile responsiveness
   - Payment method selection UX
   - Loading states
   - Error messages
   - Success confirmations

**DPO Test Credentials** (from DPO sandbox documentation):
```
Company Token: [Get from DPO sandbox account]
Service Type: [Get from DPO sandbox account]
Test Mode: True

Test M-Pesa Phone: 0712345678 (any format)
Test Card: 4242424242424242 (Visa)
Test CVV: 123
Test Expiry: Any future date
```

### Phase 7: Production Deployment (Priority 4)

**Pre-deployment Checklist**:
- [ ] DPO production credentials configured
- [ ] DPO_TEST_MODE=False in production .env
- [ ] DPO callback URLs updated to production domain
- [ ] Stripe routes disabled/removed
- [ ] Database migrations applied (if new columns added)
- [ ] Email templates updated with DPO branding
- [ ] Error monitoring configured (Sentry, etc.)
- [ ] Payment reconciliation process documented
- [ ] Customer support trained on DPO payment issues

---

## Database Schema Updates

### Option A: Use Existing Fields (Recommended for MVP)

No schema changes needed. Use existing JSON columns:

```python
# In payment routes/service
payment.payment_metadata = {
    'gateway': 'dpo',
    'trans_token': 'ABC123...',
    'trans_ref': 'DPO-REF-123',
    'result_code': '000',
    'result_explanation': 'Transaction Paid',
    'payment_type': 'mpesa',  # or 'tigo', 'airtel', 'card'
    'customer_phone': '+255712345678',
    'dpo_currency': 'TZS'
}

payment.transaction_id = dpo_trans_ref  # Use existing field
payment.gateway_response = full_dpo_response_dict  # Use existing JSON field
payment.payment_method = PaymentMethod.MOBILE_MONEY  # or .CARD
```

### Option B: Add Dedicated DPO Columns (Future Enhancement)

**Migration**: `migrations/versions/XXX_add_dpo_fields.py`

```python
def upgrade():
    op.add_column('payments', sa.Column('trans_token', sa.String(255), nullable=True))
    op.add_column('payments', sa.Column('trans_ref', sa.String(255), nullable=True))
    op.add_column('payments', sa.Column('dpo_result_code', sa.String(10), nullable=True))
    op.add_column('payments', sa.Column('dpo_result_explanation', sa.Text, nullable=True))
    
    # Add indexes for faster lookups
    op.create_index('idx_trans_token', 'payments', ['trans_token'])
    op.create_index('idx_trans_ref', 'payments', ['trans_ref'])

def downgrade():
    op.drop_index('idx_trans_ref', 'payments')
    op.drop_index('idx_trans_token', 'payments')
    op.drop_column('payments', 'dpo_result_explanation')
    op.drop_column('payments', 'dpo_result_code')
    op.drop_column('payments', 'trans_ref')
    op.drop_column('payments', 'trans_token')
```

**Recommendation**: Start with **Option A** (use existing JSON fields). Only implement **Option B** if performance or querying needs require dedicated columns.

---

## Route Structure

### Complete Route Map (After Implementation)

```
PAYMENTS BLUEPRINT (/payments/)
│
├── /checkout/<ref>                    [GET]
│   └── Shows DPO payment method selection
│
├── /dpo/initiate/<ref>                [POST]
│   └── Creates DPO token, redirects to DPO
│
├── /dpo/callback                      [GET]
│   └── Handles DPO redirect after payment
│
├── /dpo/cancel                        [GET]
│   └── Handles user cancellation from DPO
│
├── /dpo/webhook                       [POST] (optional)
│   └── Handles DPO server notifications
│
├── /alternative-methods/<ref>         [GET] (new)
│   └── Shows bank transfer and invoice options
│
├── /bank-transfer/<ref>               [GET] (existing, kept)
│   └── Bank transfer instructions
│
├── /invoice/<ref>                     [GET] (existing, kept)
│   └── Invoice request
│
├── /success/<ref>                     [GET]
│   └── Payment success page
│
├── /cancelled/<ref>                   [GET]
│   └── Payment cancelled page
│
├── /pending/<ref>                     [GET]
│   └── Payment pending page
│
├── /api/payment-status/<ref>          [GET]
│   └── AJAX endpoint for status check
│
└── DEPRECATED (keep but disable):
    ├── /stripe/checkout/<ref>
    ├── /stripe/webhook
    ├── /mpesa/checkout/<ref>
    └── /mpesa/callback
```

---

## Template Modifications

### Files to Modify

1. **`app/templates/payments/checkout.html`** (MAJOR CHANGES)
   - Replace payment method cards
   - Update form action
   - Add alternative payment link
   - Update JavaScript for new payment types

2. **`app/templates/payments/success.html`** (MINOR CHANGES)
   - Update payment confirmation text
   - Remove Stripe references
   - Add DPO branding

3. **`app/templates/payments/cancelled.html`** (MINOR CHANGES)
   - Update cancellation message
   - Link back to checkout

4. **`app/templates/payments/pending.html`** (MINOR CHANGES)
   - Update pending message for mobile money
   - Add DPO support contact

### Files to Create

1. **`app/templates/payments/alternative_methods.html`** (NEW)
   - Hero section
   - Bank transfer option
   - Invoice request option
   - Link back to main checkout

### Template Component: DPO Payment Card

**Design Specification**:

```html
<!-- M-Pesa Payment Card -->
<label class="payment-method-card relative flex cursor-pointer rounded-lg border-2 border-gray-200 bg-white p-4 shadow-sm hover:border-green-500 transition-all focus:outline-none" data-method="mpesa">
    <input type="radio" name="payment_type" value="mpesa" class="sr-only" required>
    <span class="flex flex-1">
        <span class="flex flex-col">
            <span class="flex items-center">
                <!-- M-Pesa Logo (Green) -->
                <svg class="w-8 h-8 text-green-600 mr-3" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
                </svg>
                <span class="block text-lg font-bold text-gray-900">M-Pesa (Vodacom)</span>
            </span>
            <span class="mt-2 flex items-center text-sm text-gray-500">
                <span>Pay via M-Pesa mobile money • Instant confirmation</span>
            </span>
            <span class="mt-1 text-xs text-green-600 font-semibold">
                ✓ Most popular • Real-time payment
            </span>
        </span>
    </span>
    <svg class="h-5 w-5 text-green-600 payment-check hidden" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
    </svg>
</label>

<!-- Tigo Pesa Payment Card -->
<label class="payment-method-card relative flex cursor-pointer rounded-lg border-2 border-gray-200 bg-white p-4 shadow-sm hover:border-blue-500 transition-all focus:outline-none" data-method="tigo">
    <input type="radio" name="payment_type" value="tigo" class="sr-only">
    <span class="flex flex-1">
        <span class="flex flex-col">
            <span class="flex items-center">
                <!-- Tigo Logo (Blue) -->
                <svg class="w-8 h-8 text-blue-600 mr-3" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
                </svg>
                <span class="block text-lg font-bold text-gray-900">Tigo Pesa</span>
            </span>
            <span class="mt-2 flex items-center text-sm text-gray-500">
                <span>Pay via Tigo mobile money • Instant confirmation</span>
            </span>
            <span class="mt-1 text-xs text-blue-600 font-semibold">
                ✓ Real-time payment
            </span>
        </span>
    </span>
    <svg class="h-5 w-5 text-blue-600 payment-check hidden" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
    </svg>
</label>

<!-- Similar structure for Airtel Money (Red) and Card Payment -->
```

---

## Configuration Priority

### Environment Variables Priority Order

**Required (Application won't start without these)**:
```env
DPO_COMPANY_TOKEN=xxx
DPO_SERVICE_TYPE=xxx
DPO_REDIRECT_URL=xxx
DPO_BACK_URL=xxx
```

**Optional (Has sensible defaults)**:
```env
DPO_CURRENCY=TZS  # Default: TZS
DPO_TEST_MODE=True  # Default: True
DPO_PAYMENT_TOKEN_LIFETIME=5  # Default: 5 hours
```

**Deprecated (Not required)**:
```env
STRIPE_PUBLIC_KEY=xxx  # No longer used
STRIPE_SECRET_KEY=xxx  # No longer used
```

### Configuration Validation

**Add to `app/__init__.py`**:

```python
def validate_payment_config(app):
    """Validate that DPO configuration is present"""
    required_dpo_vars = [
        'DPO_COMPANY_TOKEN',
        'DPO_SERVICE_TYPE',
        'DPO_REDIRECT_URL',
        'DPO_BACK_URL'
    ]
    
    missing = [var for var in required_dpo_vars if not app.config.get(var)]
    
    if missing:
        raise RuntimeError(
            f"Missing required DPO configuration: {', '.join(missing)}. "
            f"Please set these in your .env file."
        )
    
    # Warn if Stripe is configured (not needed anymore)
    if app.config.get('STRIPE_SECRET_KEY'):
        app.logger.warning(
            "Stripe credentials detected but are not being used. "
            "DPO is the active payment gateway."
        )
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_dpo_service.py`

```python
class TestDPOService:
    def test_create_token_success(self):
        """Test successful token creation"""
        pass
    
    def test_create_token_with_mobile_money_type(self):
        """Test token creation with pre-selected mobile money"""
        pass
    
    def test_verify_token_paid(self):
        """Test verification of paid transaction"""
        pass
    
    def test_verify_token_pending(self):
        """Test verification of pending transaction"""
        pass
    
    def test_verify_token_failed(self):
        """Test verification of failed transaction"""
        pass
    
    def test_cancel_token(self):
        """Test token cancellation"""
        pass
```

### Integration Tests

**File**: `tests/test_payment_routes.py`

```python
class TestDPOPaymentFlow:
    def test_checkout_page_shows_dpo_methods(self):
        """Checkout page shows M-Pesa, Tigo, Airtel, Card"""
        pass
    
    def test_dpo_initiate_creates_token(self):
        """Initiate route creates DPO token and redirects"""
        pass
    
    def test_dpo_callback_success(self):
        """Callback route handles successful payment"""
        pass
    
    def test_dpo_callback_failed(self):
        """Callback route handles failed payment"""
        pass
    
    def test_dpo_cancel(self):
        """Cancel route handles user cancellation"""
        pass
```

### Manual Testing Checklist

- [ ] M-Pesa payment (sandbox)
- [ ] Tigo Pesa payment (sandbox)
- [ ] Airtel Money payment (sandbox)
- [ ] Card payment (sandbox - test Visa)
- [ ] Card payment (sandbox - test Mastercard)
- [ ] Payment cancellation
- [ ] Payment expiry (wait for token to expire)
- [ ] Network timeout simulation
- [ ] Duplicate payment prevention
- [ ] Email confirmation sent
- [ ] Receipt generated
- [ ] Admin dashboard shows payment correctly

---

## Migration Plan

### For New Installations

**Simple**: Just configure DPO credentials and go. Stripe is already optional.

### For Existing Installations (With Stripe Payments)

**Strategy**: Parallel Operation (Transitional Period)

**Phase 1: Add DPO (Week 1)**
- Deploy DPO routes alongside existing Stripe
- Checkout shows both options
- Monitor DPO usage

**Phase 2: Promote DPO (Week 2-3)**
- Make DPO the default/recommended option
- Stripe becomes "alternative method"
- Monitor for issues

**Phase 3: Deprecate Stripe (Week 4)**
- Remove Stripe from main checkout
- Keep Stripe routes for historical payments only
- Update documentation

**Phase 4: Stripe Removal (Month 2)**
- Completely remove Stripe code
- Archive Stripe payment data
- Final cleanup

### Data Migration

**No data migration needed** - Existing Stripe payments remain in database with Stripe identifiers. New payments use DPO identifiers.

**Payment Model Compatibility**:
```python
# Old Stripe payments
payment.stripe_payment_intent_id = "pi_123..."
payment.payment_method = PaymentMethod.CARD
payment.transaction_id = None

# New DPO payments
payment.stripe_payment_intent_id = None
payment.payment_method = PaymentMethod.MOBILE_MONEY  # or .CARD
payment.transaction_id = "DPO-REF-123"
payment.payment_metadata = {'gateway': 'dpo', ...}
```

---

## Rollback Strategy

### If DPO Integration Fails

**Option 1: Quick Rollback**
1. Revert code to previous commit (before DPO routes)
2. Re-enable Stripe routes
3. Deploy previous version
4. Investigate DPO issues offline

**Option 2: Feature Flag Rollback**

Add feature flag to config:
```python
# config.py
USE_DPO_PAYMENT = os.getenv('USE_DPO_PAYMENT', 'True').lower() == 'true'
USE_STRIPE_PAYMENT = os.getenv('USE_STRIPE_PAYMENT', 'False').lower() == 'true'
```

In checkout template:
```python
{% if config['USE_DPO_PAYMENT'] %}
    <!-- Show DPO payment methods -->
{% elif config['USE_STRIPE_PAYMENT'] %}
    <!-- Show Stripe payment methods -->
{% endif %}
```

**Rollback Steps**:
1. Set `USE_DPO_PAYMENT=False` in .env
2. Set `USE_STRIPE_PAYMENT=True` in .env
3. Restart application
4. No code deployment needed

### Risk Mitigation

**Before Go-Live**:
- [ ] Test all payment flows in DPO sandbox
- [ ] Set up monitoring for payment failures
- [ ] Configure alerts for high failure rates
- [ ] Document common DPO error codes
- [ ] Train support team on DPO issues
- [ ] Have DPO support contact ready
- [ ] Schedule deployment during low-traffic period

**After Go-Live**:
- [ ] Monitor first 24 hours closely
- [ ] Check payment success rate vs baseline
- [ ] Verify email confirmations sending
- [ ] Test payment reconciliation process
- [ ] Gather user feedback

---

## Success Metrics

### Key Performance Indicators (KPIs)

**Payment Success Rate**:
- Target: >95% payment success rate
- Measure: (Completed payments / Initiated payments) × 100

**Payment Speed**:
- Target: <2 minutes from initiation to confirmation
- Measure: Average time from initiate to callback

**User Abandonment**:
- Target: <20% checkout abandonment
- Measure: (Initiated checkouts / Completed registrations) × 100

**Mobile Money Adoption**:
- Target: >60% of payments via mobile money
- Measure: Mobile money payments / Total payments

**Support Tickets**:
- Target: <5% payment-related support tickets
- Measure: Payment tickets / Total registrations

### Monitoring Dashboard

**Create Admin Dashboard Section**:
```
PAYMENT ANALYTICS (Last 7 Days)
├── Total Payments: 150
├── Success Rate: 96.7%
├── Average Payment Time: 1m 34s
├── Payment Method Breakdown:
│   ├── M-Pesa: 85 (56.7%)
│   ├── Tigo Pesa: 35 (23.3%)
│   ├── Airtel Money: 15 (10.0%)
│   └── Card: 15 (10.0%)
├── Failed Payments: 5
│   ├── User Cancelled: 3
│   ├── Expired: 1
│   └── Declined: 1
└── Pending Payments: 2
```

---

## Next Steps

### Immediate Actions

1. **Review and Approve Plan** - Get stakeholder sign-off on DPO-only approach
2. **Setup DPO Sandbox Account** - Get test credentials
3. **Begin Phase 1 Implementation** - Create DPO payment routes
4. **Update Checkout Template** - Simplify to DPO methods only
5. **Test in Sandbox** - Validate all payment flows

### Timeline Estimate

| Phase | Duration | Description |
|-------|----------|-------------|
| **Phase 1** | 2 days | Create DPO payment routes |
| **Phase 2** | 1 day | Update checkout template |
| **Phase 3** | 1 day | Create alternative payment page |
| **Phase 4** | 0.5 days | Update configuration documentation |
| **Phase 5** | 1 day | Enhanced error handling in DPO service |
| **Phase 6** | 2 days | Testing (sandbox + edge cases) |
| **Phase 7** | 0.5 days | Production deployment |
| **Total** | **8 days** | Full implementation |

### Dependencies

- [ ] DPO sandbox credentials
- [ ] DPO production credentials
- [ ] Test phone numbers for mobile money
- [ ] Test cards for card payments
- [ ] Stakeholder approval
- [ ] Support team training

---

## Questions to Resolve

1. **Should we completely remove Stripe code or just disable routes?**
   - Recommendation: Keep code, disable routes (easier rollback)

2. **Do we need database migration for DPO fields or use JSON columns?**
   - Recommendation: Use existing JSON columns (faster, no migration needed)

3. **Should we keep bank transfer and invoice as alternative methods?**
   - Recommendation: Yes, keep for institutional/company payments

4. **What's the fallback if DPO is down?**
   - Recommendation: Show manual payment options (bank transfer, invoice)

5. **Do we need webhook or is redirect callback sufficient?**
   - Recommendation: Start with redirect callback, add webhook if needed

---

## Conclusion

This plan provides a **comprehensive roadmap** for transitioning the BEEASY Flask registration system to **DPO as the sole payment gateway**. The implementation focuses on:

1. **Simplicity**: Single payment flow, easier for users
2. **Local Focus**: Tanzania mobile money ecosystem
3. **Maintainability**: One gateway to support
4. **Flexibility**: Alternative methods for edge cases
5. **Safety**: Rollback strategy in case of issues

**Estimated Timeline**: 8 working days  
**Estimated Effort**: 1 developer, full-time  
**Risk Level**: LOW (well-documented, tested service already exists)

---

**Document Status**: DRAFT - Awaiting Approval  
**Last Updated**: 2025-12-04  
**Version**: 1.0  
**Author**: Claude (AI Assistant)
