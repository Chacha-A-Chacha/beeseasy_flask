"""
Live Database Migration Script — Ticket Pricing Update
Pollination Africa Summit 2026

MUST be run AFTER: flask db upgrade (to add resume_otp columns)
MUST be run BEFORE: seed_ticket_prices() (which would corrupt data)

This script safely:
1. Creates the new 'tanzania' ticket type
2. Moves existing registration from 'speaker' (Tanzania pass) to 'tanzania'
3. Repurposes 'speaker' ticket as PhD/Presenter Pass
4. Updates all ticket prices per client spec
5. Recalculates pending payments to match new prices

Usage:
    set PYTHONIOENCODING=utf-8
    venv/Scripts/python.exe migrate_live_tickets.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models.registration import (
    AttendeeRegistration,
    AttendeeTicketType,
    TicketPrice,
)
from app.models.payment import Payment, PaymentStatus

app = create_app()


def migrate():
    with app.app_context():
        print("=" * 60)
        print("LIVE DATABASE TICKET MIGRATION")
        print("=" * 60)

        # -------------------------------------------------------
        # PRE-FLIGHT CHECKS
        # -------------------------------------------------------
        print("\n[1/7] Pre-flight checks...")

        # Verify we're on the right DB
        old_tz_ticket = TicketPrice.query.filter_by(
            ticket_type=AttendeeTicketType.SPEAKER
        ).first()

        if not old_tz_ticket:
            print("  ERROR: No 'speaker' ticket found. Wrong database?")
            return False

        if "Tanzania" not in old_tz_ticket.name:
            print(f"  ERROR: Speaker ticket is '{old_tz_ticket.name}', expected Tanzania pass.")
            print("  This script is designed for the live DB where speaker=Tanzania pass.")
            return False

        # Check if migration already ran
        existing_tz = TicketPrice.query.filter_by(
            ticket_type=AttendeeTicketType.TANZANIA
        ).first()

        if existing_tz:
            print("  Tanzania ticket already exists. Migration may have already run.")
            print(f"  Existing: id={existing_tz.id} name={existing_tz.name}")
            confirm = input("  Continue anyway? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("  Aborted.")
                return False

        # Find the registration on speaker ticket
        tz_registration = AttendeeRegistration.query.filter_by(
            ticket_type=AttendeeTicketType.SPEAKER
        ).first()

        if tz_registration:
            print(f"  Found registration to migrate: id={tz_registration.id} "
                  f"email={tz_registration.email} price_id={tz_registration.ticket_price_id}")
        else:
            print("  No registrations on speaker ticket to migrate.")

        print("  Pre-flight OK")

        # -------------------------------------------------------
        # STEP 1: Create tanzania ticket
        # -------------------------------------------------------
        print("\n[2/7] Creating Tanzania Access Pass ticket...")

        early_bird_deadline = datetime(2026, 4, 15, 23, 59, 59)

        if not existing_tz:
            tanzania_ticket = TicketPrice(
                ticket_type=AttendeeTicketType.TANZANIA,
                name="Tanzania Access Pass",
                description=(
                    "Exclusive pass for Tanzania-based delegates. "
                    "Limited to 250 delegates only."
                ),
                price=Decimal("250000.00"),
                currency="TZS",
                early_bird_price=Decimal("200000.00"),
                early_bird_deadline=early_bird_deadline,
                max_quantity=250,
                current_quantity=0,
                includes_lunch=True,
                includes_materials=True,
                includes_certificate=True,
                includes_networking=True,
                is_active=True,
            )
            db.session.add(tanzania_ticket)
            db.session.flush()  # Get the ID
            print(f"  Created: id={tanzania_ticket.id}")
        else:
            tanzania_ticket = existing_tz
            print(f"  Using existing: id={tanzania_ticket.id}")

        # -------------------------------------------------------
        # STEP 2: Move registration from speaker to tanzania
        # -------------------------------------------------------
        print("\n[3/7] Moving registration from speaker to tanzania...")

        if tz_registration:
            old_price_id = tz_registration.ticket_price_id
            tz_registration.ticket_type = AttendeeTicketType.TANZANIA
            tz_registration.ticket_price_id = tanzania_ticket.id
            print(f"  Moved reg id={tz_registration.id}: "
                  f"speaker(price_id={old_price_id}) -> tanzania(price_id={tanzania_ticket.id})")

            # Update inventory counts
            old_tz_ticket.current_quantity = max(0, (old_tz_ticket.current_quantity or 0) - 1)
            tanzania_ticket.current_quantity = (tanzania_ticket.current_quantity or 0) + 1
            print(f"  Inventory: speaker ticket sold {old_tz_ticket.current_quantity}, "
                  f"tanzania ticket sold {tanzania_ticket.current_quantity}")
        else:
            print("  No registration to move.")

        # -------------------------------------------------------
        # STEP 3: Repurpose speaker ticket as PhD/Presenter
        # -------------------------------------------------------
        print("\n[4/7] Updating speaker ticket to PhD/Presenter Pass...")

        old_tz_ticket.name = "PhD/Presenter Pass"
        old_tz_ticket.description = (
            "For accepted presenters and PhD researchers. "
            "Only approved abstracts qualify. Do not register if your "
            "abstract has not been confirmed by the secretariat."
        )
        old_tz_ticket.price = Decimal("145.00")
        old_tz_ticket.currency = "USD"
        old_tz_ticket.early_bird_price = Decimal("116.00")
        old_tz_ticket.early_bird_deadline = early_bird_deadline
        old_tz_ticket.max_quantity = None
        old_tz_ticket.is_active = True
        print(f"  Updated: id={old_tz_ticket.id} -> PhD/Presenter Pass, USD 145 (EB 116)")

        # -------------------------------------------------------
        # STEP 4: Update remaining ticket prices
        # -------------------------------------------------------
        print("\n[5/7] Updating ticket prices...")

        updates = [
            {
                "type": AttendeeTicketType.AFRICAN,
                "name": "Africa Delegate Pass",
                "description": (
                    "Full summit access for delegates residing in or affiliated with "
                    "African Union member states. Proof of residence may be required."
                ),
                "price": Decimal("200.00"),
                "currency": "USD",
                "early_bird_price": Decimal("130.00"),
                "early_bird_deadline": early_bird_deadline,
            },
            {
                "type": AttendeeTicketType.STUDENT,
                "name": "Student Pass (Africa-Based Institutions)",
                "description": (
                    "Full summit access for students enrolled at Africa-based institutions. "
                    "Must provide proof of current student status. Valid student ID required at check-in."
                ),
                "price": Decimal("60.00"),
                "currency": "USD",
                "early_bird_price": Decimal("48.00"),
                "early_bird_deadline": early_bird_deadline,
            },
            {
                "type": AttendeeTicketType.GROUP,
                "name": "Farmer Group Pass (5-10 Participants)",
                "description": (
                    "Group registration for farmer cooperatives and agricultural groups. "
                    "Covers 5 to 10 members. Requires group registration with designated "
                    "group leader details."
                ),
                "price": Decimal("1300000.00"),
                "currency": "TZS",
                "early_bird_price": Decimal("1040000.00"),
                "early_bird_deadline": early_bird_deadline,
            },
        ]

        for u in updates:
            ticket = TicketPrice.query.filter_by(ticket_type=u["type"]).first()
            if ticket:
                old_price = ticket.price
                old_cur = ticket.currency
                ticket.name = u["name"]
                ticket.description = u["description"]
                ticket.price = u["price"]
                ticket.currency = u["currency"]
                ticket.early_bird_price = u["early_bird_price"]
                ticket.early_bird_deadline = u["early_bird_deadline"]
                print(f"  {u['name']}: {old_cur} {old_price} -> {u['currency']} {u['price']} "
                      f"(EB {u['currency']} {u['early_bird_price']})")
            else:
                print(f"  WARNING: Ticket type {u['type']} not found!")

        # -------------------------------------------------------
        # STEP 5: Recalculate pending payments
        # -------------------------------------------------------
        print("\n[6/7] Recalculating pending payments...")

        # Get all pending attendee registrations with their payments
        pending_regs = (
            AttendeeRegistration.query
            .filter(
                AttendeeRegistration.is_deleted == False,
                AttendeeRegistration.status.in_(["pending"]),
            )
            .all()
        )

        recalculated = 0
        for reg in pending_regs:
            payment = reg.payments[0] if reg.payments else None
            if not payment:
                continue

            # Only recalculate pending/failed payments (not completed/processing)
            if payment.payment_status not in (PaymentStatus.PENDING, PaymentStatus.FAILED):
                print(f"  SKIP reg id={reg.id} (payment status={payment.payment_status.value})")
                continue

            # Get fresh price from the updated ticket
            ticket = TicketPrice.query.get(reg.ticket_price_id)
            if not ticket:
                print(f"  SKIP reg id={reg.id} (no ticket found)")
                continue

            new_price = ticket.get_current_price()
            old_total = payment.total_amount

            payment.subtotal = new_price
            payment.currency = ticket.currency
            payment.total_amount = new_price - (payment.discount_amount or Decimal("0.00"))

            if old_total != payment.total_amount:
                print(f"  reg id={reg.id} ({reg.email}): "
                      f"{old_total} -> {payment.total_amount} {payment.currency} "
                      f"(ticket: {ticket.name})")
                recalculated += 1

        print(f"  Recalculated {recalculated} payments")

        # -------------------------------------------------------
        # STEP 6: Summary and confirm
        # -------------------------------------------------------
        print("\n[7/7] Final state preview...")
        print()

        all_tickets = TicketPrice.query.order_by(TicketPrice.id).all()
        for t in all_tickets:
            active = "ACTIVE" if t.is_active else "INACTIVE"
            print(f"  id={t.id} | {t.ticket_type.value:10s} | {t.name:45s} | "
                  f"{t.currency} {t.price:>12} | EB={t.early_bird_price} | "
                  f"max={t.max_quantity} | sold={t.current_quantity} | {active}")

        print()
        confirm = input("Commit these changes to the live database? (yes/no): ").strip().lower()

        if confirm == "yes":
            db.session.commit()
            print("\nMIGRATION COMMITTED SUCCESSFULLY")
            return True
        else:
            db.session.rollback()
            print("\nROLLED BACK — no changes made")
            return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
