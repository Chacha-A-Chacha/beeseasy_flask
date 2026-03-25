# Registration Flow Audit — Issue Tracker

**Audit Date:** 2026-03-25
**Scope:** Full registration flow from ticket selection → DPO checkout → redirect, and emailed checkout link flow.

---

## Flow Overview

```
Ticket Selection → Registration Form (POST) → RegistrationService
  ├─ FREE ticket: auto-confirm → badge → confirmation email → DONE
  └─ PAID ticket: pending → registration email w/ checkout link
       ↓
     /checkout/<ref> → select payment method → /dpo/direct/<ref>
       ↓
     DPO creates token → redirect to DPO gateway → user pays
       ↓
     /dpo/callback → verify_token() → process_payment_completion()
       → confirm registration → generate badge → send email → /success/<ref>

Emailed checkout link flow:
  Email → /checkout/<ref> → same path as above
```

---

## CRITICAL

### ~~1. DPO Callback Has No Signature Verification~~ — CANCELLED

- **Status:** Cancelled after deep code review (2026-03-25)
- **Reason:** The `/dpo/callback` route **always** calls `dpo_service.verify_token()` — a server-to-server API call authenticated with `DPO_COMPANY_TOKEN` — before acting on any callback. This is functionally equivalent to signature verification. A forged callback triggers the verify call, DPO responds "not paid", and nothing happens. The verify step cannot be skipped (no code path around it) and cannot fail open (`success=False` on any error/timeout). Replay attacks are blocked by the idempotency guard in `process_payment_completion()`. No fix needed.

---

### 2. Checkout Links Never Expire and Have No Authentication

- **Location:** `app/services/registration_service.py` — `_send_registration_email()`, `app/routes/payment.py` — `/checkout/<ref>`
- **Description:** The checkout URL emailed to registrants is simply `/checkout/<reference_number>`. There is no expiry token, no session requirement, and no authentication. Anyone with a reference number can access the checkout page and see registration details (name, email, ticket type, amount due).
- **Reference number format:** `PAA` or `PAE` prefix + timestamp-based component + short random suffix. While not trivially sequential, they are not cryptographically random and could be enumerated or guessed with moderate effort.
- **Impact:**
  - Information disclosure: registration details visible to anyone with the reference number.
  - No time-bound access: a link emailed today works indefinitely, even if the event has passed.
  - Potential for unauthorized payment initiation on someone else's registration.
- **Recommendation:**
  - Option A (preferred): Add a signed, time-limited token to checkout URLs (e.g., `itsdangerous.URLSafeTimedSerializer`) that expires after 7 days. Validate the token on the checkout route.
  - Option B (minimal): Use cryptographically random reference numbers (e.g., UUID4) to make enumeration infeasible, and add a configurable expiry check on the checkout route.

---

### 3. Ticket Claim Not Guaranteed to Roll Back on All Failure Paths

- **Location:** `app/services/registration_service.py` lines 73–77 (`claim_tickets`), lines 125–126 (`flush`), lines 184/196 (`commit`/`rollback`)
- **Description:** `ticket_price.claim_tickets(1)` decrements `current_quantity` immediately in the SQLAlchemy session. The service then calls `db.session.flush()` (not `commit()`) after creating the registration, and `db.session.commit()` later.
  - If `commit()` raises a `SQLAlchemyError`, the `except` block calls `db.session.rollback()` which correctly restores the ticket count.
  - However, if a non-SQLAlchemy exception occurs between `flush()` and `commit()` (e.g., in `_send_registration_email()` or `BadgeService.generate_badge()`), the generic `except Exception` block also calls `rollback()` — but email sending or badge generation failures could leave the session in an ambiguous state if they partially committed side effects.
- **Impact:** Under certain failure modes, a ticket could be claimed but the registration never finalized, effectively losing inventory.
- **Recommendation:**
  - Move `db.session.commit()` to immediately after all database operations are complete, before any external calls (email, badge generation).
  - Perform email sending and badge generation after the commit, outside the transaction. If they fail, the registration is still valid and these can be retried.

---

### 4. Promo Code Usage Not Atomic With Payment Completion

- **Location:** `app/services/registration_service.py` — `_apply_promo_code()` (lines 397–446)
- **Description:** When a promo code is applied during registration:
  1. A `PromoCodeUsage` record is created.
  2. `promo.current_uses` is incremented.
  3. `payment.discount_amount` and `payment.total_amount` are updated.
  4. All of this is committed as part of the registration transaction.

  If the user never completes payment (abandons checkout), the promo code usage is consumed but wasted. There is no mechanism to reclaim promo code uses from abandoned registrations.
- **Impact:** Promo codes with limited `max_uses` can be exhausted by users who register but never pay. A promo code with `max_uses=100` could be "used up" by 100 abandoned registrations, blocking legitimate users.
- **Recommendation:**
  - Option A: Defer promo code usage recording to `process_payment_completion()` instead of registration time. Store the promo code reference on the payment/registration but don't increment `current_uses` until payment succeeds.
  - Option B: Add a cleanup job that releases promo code uses from registrations that remain PENDING beyond a configurable threshold (e.g., 7 days).

---

## HIGH

### 5. No Recovery for Missed DPO Callbacks

- **Location:** `app/routes/payment.py` — `/dpo/callback`, `/dpo/verify/<ref>`
- **Description:** After DPO token creation, the payment status is set to `PROCESSING`. If the DPO callback redirect fails (browser closes, network timeout, user navigates away), the payment remains in `PROCESSING` state indefinitely. There is a manual verify endpoint (`/dpo/verify/<ref>`) and a "Check Status" button on the pending page, but:
  1. The user must know to visit the pending page and click the button.
  2. There is no automated process to detect and verify stale `PROCESSING` payments.
- **Impact:** Payments that were actually completed on DPO's side remain unconfirmed in the app. The user paid but doesn't receive confirmation, badge, or receipt. Manual admin intervention required.
- **Recommendation:** Implement a scheduled task (cron job or background worker) that:
  1. Queries all payments with `payment_status = PROCESSING` older than 15 minutes.
  2. Calls `dpo_service.verify_token()` for each.
  3. Updates payment status based on DPO's response.
  4. Processes completion if DPO confirms payment.

---

### 6. Payment Amount Not Re-validated at DPO Token Creation

- **Location:** `app/routes/payment.py` — `/dpo/direct/<ref>` (lines 265–337)
- **Description:** When creating a DPO token, the route reads `payment.total_amount` (set at registration time) and sends it to DPO. There is no check that this amount still matches the current ticket/package price. If an admin updates ticket prices between registration and checkout, the amount sent to DPO could be stale — either overcharging or undercharging the user.
- **Impact:** Financial discrepancy between what the user should pay (current price) and what DPO charges (registration-time price).
- **Recommendation:** Before creating the DPO token, re-calculate the expected amount from the current ticket/package price and compare with `payment.total_amount`. If they differ:
  - Option A: Update the payment record to reflect the current price.
  - Option B: Honor the original registration price (common practice) but log the discrepancy.
  - Either way, add an explicit validation step with a log entry.

---

### 7. `selected_ticket` / `selected_package` Still `None` on POST Validation Failure

- **Location:** `app/routes/register.py` — `register_attendee_form()` (line 99 onward), `app/templates/register/attendee.html` (line 843)
- **Description:** The GET redirect (added in previous fix) prevents the page from rendering without a valid ticket on initial load. However, on POST (form validation failure), if the submitted `ticket_type` doesn't resolve to a valid `TicketPrice` (e.g., ticket was deactivated between page load and form submission), `selected_ticket` is `None`. The template re-renders with:
  - The sidebar showing "No ticket selected" (guarded by `{% if selected_ticket %}`).
  - The promo code section rendering `data-price="0"` and `data-currency=""` (from our ternary fix).
  - A broken user experience — the user sees their filled form but the ticket context is lost.
- **Impact:** Confusing UX on POST failure. Promo code AJAX would send `amount=0` to the validation endpoint, returning incorrect discount calculations.
- **Recommendation:** On POST, if `selected_ticket` cannot be resolved, redirect back to the ticket selection page with the flash message "Your selected ticket is no longer available. Please choose another." Same for exhibitor packages.

---

### 8. Promo Code `applicable_ticket_types` / `applicable_packages` Not Enforced

- **Location:** `app/models/payment.py` — `PromoCode` model (lines 442–603), `app/services/registration_service.py` — `_apply_promo_code()`, `app/routes/register.py` — `validate_promo()`
- **Description:** The `PromoCode` model has two JSON fields:
  - `applicable_ticket_types` — intended to restrict the promo to specific attendee ticket types (e.g., only STUDENT tickets).
  - `applicable_packages` — intended to restrict the promo to specific exhibitor packages (e.g., only GOLD).

  Neither `is_valid()`, `is_valid_for_user()`, `calculate_discount()`, nor the service-layer `_apply_promo_code()` method checks these fields. The AJAX validation endpoint (`validate_promo`) also doesn't check them.
- **Impact:** A promo code configured for STUDENT tickets only can be applied to VIP or any other ticket type. Business logic bypass leading to unintended discounts.
- **Recommendation:**
  - Add ticket type / package type validation to `is_valid()` or create a dedicated `is_applicable_to(ticket_type)` method.
  - Pass the ticket/package type to `_apply_promo_code()` and the AJAX endpoint for validation.
  - Reject codes that don't apply to the selected ticket/package with a clear message.

---

## MEDIUM

### 9. Stale PENDING Registrations Block Email Re-use and Consume Tickets

- **Location:** `app/services/registration_service.py` — `check_email_availability()` (called at line 54), `claim_tickets()` (line 73)
- **Description:** When a user registers but never pays:
  - The registration remains in `PENDING` status.
  - The email is marked as taken (`check_email_availability` returns false for the same email + registration type).
  - The claimed ticket remains decremented from `current_quantity`.

  There is no mechanism to expire, clean up, or allow re-registration for stale PENDING records.
- **Impact:**
  - Users who abandon registration cannot re-register with the same email.
  - Ticket inventory is permanently reduced by abandoned registrations.
  - Over time, this creates ghost registrations that inflate counts and reduce availability.
- **Recommendation:**
  - Implement a cleanup job that runs daily:
    1. Find all PENDING registrations older than N days (e.g., 7).
    2. Release their claimed tickets (`ticket_price.release_tickets(1)`).
    3. Release their promo code uses (if applicable).
    4. Either soft-delete or mark them as EXPIRED.
  - Alternatively, allow users to resume an existing PENDING registration by redirecting them to their existing checkout link when they try to register with the same email.

---

### 10. Payment Method Default Inconsistency

- **Location:** `app/routes/payment.py` — `/dpo/direct/<ref>` (line ~320), `app/models/payment.py` — `update_from_dpo_verification()`
- **Description:** The `/dpo/direct/<ref>` route sets `payment.payment_method = PaymentMethod.MOBILE_MONEY` as a default before redirecting to DPO. After payment, `update_from_dpo_verification()` updates the method based on DPO's `AccRef` field (e.g., "Visa", "M-Pesa"). However, if DPO's verification response doesn't include `AccRef` (or it's empty), the payment method remains `MOBILE_MONEY` even if the user paid by card.
- **Impact:** Inaccurate payment method reporting. Financial reconciliation may attribute card payments to mobile money.
- **Recommendation:** Default to a neutral value (e.g., `None` or a new `DPO` enum value) before DPO redirect. Only set the specific method after verification confirms it. If DPO doesn't return the method, flag it for admin review rather than guessing.

---

### 11. Race Condition in `process_payment_completion()`

- **Location:** `app/services/registration_service.py` — `process_payment_completion()` (lines 311–363)
- **Description:** The idempotency guard checks `payment.payment_status == COMPLETED` before processing. However, between reading the status and committing the update, a concurrent request (e.g., user rapidly clicking "Check Status", or DPO callback and manual verify hitting simultaneously) could enter the same block.
  - The `version` column on Registration provides optimistic locking, but Payment has no such column.
  - No `SELECT FOR UPDATE` or database-level lock is used.
- **Impact:** Potential duplicate badge generation, duplicate confirmation emails, or database integrity errors from concurrent commits.
- **Recommendation:** Add `SELECT FOR UPDATE` when fetching the payment record in `process_payment_completion()`:
  ```python
  payment = Payment.query.with_for_update().get(payment_id)
  ```
  This acquires a row-level lock, ensuring only one process can update the payment at a time.

---

### 12. Bank Transfer / Invoice Payments Have No Expiry

- **Location:** `app/routes/payment.py` — `/bank-transfer/<ref>`, `/invoice/<ref>`
- **Description:** Both routes set `payment_status = PENDING` and `payment_method` accordingly, but set no deadline or expiry. The `payment_due_date` is set at registration time (7 days from creation) but is never enforced — the checkout page doesn't check it, and there's no process to expire overdue payments.
- **Impact:** Tickets remain claimed indefinitely for bank transfer and invoice payments that are never completed. Combined with issue #9, this creates permanent ticket inventory leakage.
- **Recommendation:**
  - Enforce `payment_due_date` on the checkout route: if past due, show a "payment expired" message and release the ticket.
  - Include the due date prominently on bank transfer instructions and invoice pages.
  - Add to the cleanup job (issue #9) to expire overdue payments.

---

### 13. CSRF Token Mixed Approach

- **Location:** `app/templates/register/attendee.html` (line 843 area — AJAX promo validation), `app/templates/base.html` (meta tag)
- **Description:** WTForms-based form submissions use `{{ form.hidden_tag() }}` which includes the CSRF token as a hidden input field. AJAX calls (promo code validation) use a different approach: reading from `<meta name="csrf-token">` in the HTML head and sending it as an `X-CSRFToken` header.
  - Both approaches work if `base.html` includes the meta tag.
  - If the meta tag is missing or the CSRF extension isn't configured to accept header-based tokens, AJAX calls silently fail with a 400 error.
- **Impact:** Promo code validation could silently break if template structure changes. Users would see "Could not verify code. Please try again." with no clear cause.
- **Recommendation:** Verify that `base.html` always includes the CSRF meta tag. Add a comment in `base.html` documenting that AJAX endpoints depend on it. Consider standardizing on one approach.

---

## LOW

### 14. Phone Fallback Country List Inconsistency

- **Location:** `app/forms/attendee_form.py` — `phone_country_code_fallback` choices, `app/forms/exhibitor_form.py` — same field
- **Description:** The attendee form's phone country code fallback dropdown has 7 countries; the exhibitor form has 6 (missing Burundi `+257`).
- **Impact:** Minor UX inconsistency. Exhibitors from Burundi using no-JS browsers cannot select their country code from the fallback dropdown.
- **Recommendation:** Synchronize the fallback country lists between both forms, or better yet, use the full country list from `app/utils/countries.py`.

---

### 15. `professional_category` Enum Conversion in Service Layer

- **Location:** `app/services/registration_service.py` lines 79–92
- **Description:** The `professional_category` field arrives as a string from the form and is converted to a `ProfessionalCategory` enum in the service layer. The conversion uses a try/except that silently defaults to `None` if the string doesn't match any enum value.
- **Impact:** If the form sends an unexpected value (due to a template/form mismatch), the professional category is silently dropped. No validation error is shown to the user.
- **Recommendation:** Move the enum conversion and validation to the form layer (custom validator on the `professional_category` field). Return a clear validation error if the value doesn't match.

---

### 16. `OSError: LSAPI: File error` (108 occurrences in stderr.log)

- **Location:** LiteSpeed/cPanel web server layer
- **Description:** These are LiteSpeed Application Server Protocol (LSAPI) worker lifecycle events — typically caused by process restarts, idle timeouts, or connection resets. They appear in stderr because the LSAPI worker writes them there.
- **Impact:** None to application logic. These are infrastructure noise.
- **Recommendation:** No code fix needed. If the frequency is concerning, review cPanel's LiteSpeed configuration for worker timeout and max-process settings.

---

## Summary Table

| # | Severity | Issue | Effort | Status |
|---|----------|-------|--------|--------|
| 1 | ~~CRITICAL~~ | ~~DPO callback no signature verification~~ | — | Cancelled |
| 2 | CRITICAL | Checkout links never expire, no auth | Medium | Fixed |
| 3 | CRITICAL → MEDIUM | Ticket claim rollback — post-commit side effects isolated | Small | Fixed |
| 4 | CRITICAL | Promo code usage not atomic with payment | Medium | Open |
| 5 | HIGH | No recovery for missed DPO callbacks | Medium | Open |
| 6 | HIGH | Payment amount not re-validated at DPO token creation | Small | Open |
| 7 | HIGH | `selected_ticket` None on POST validation failure | Small | Partial |
| 8 | HIGH | Promo `applicable_ticket_types`/`applicable_packages` not enforced | Small | Open |
| 9 | MEDIUM | Stale PENDING registrations block re-use | Medium | Open |
| 10 | MEDIUM | Payment method default inconsistency | Small | Open |
| 11 | MEDIUM | Race condition in `process_payment_completion()` | Small | Open |
| 12 | MEDIUM | Bank transfer / invoice payments no expiry | Small | Open |
| 13 | MEDIUM | CSRF token mixed approach | Trivial | Open |
| 14 | LOW | Phone fallback country list inconsistency | Trivial | Open |
| 15 | LOW | `professional_category` silent enum conversion | Small | Open |
| 16 | LOW | LSAPI file errors (infrastructure) | None | N/A |
