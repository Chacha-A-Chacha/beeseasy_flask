"""
Database seed functions for Pollination Africa Summit 2026
Populates initial pricing and configuration data

Ticket structure:
- International Delegate Pass: $300 USD
- Africa-Based Delegate Pass: $250 USD
- Student Pass (Africa-Based Institutions): $180 USD
- Farmer Groups Pass (5-10 members): $1,500 USD

Early bird: 20% off all attendee tickets (before April 15, 2026)

All tickets include:
- Full 3-day access to all summit sessions
- Catering (breakfast, lunch, and refreshment breaks)
- Summit materials and delegate kit
- Simultaneous interpretation (English, French, Arabic)
"""

from datetime import datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import (
    AddOnItem,
    AttendeeTicketType,
    ExhibitorPackage,
    ExhibitorPackagePrice,
    PromoCode,
    TicketPrice,
    User,
    UserRole,
)


def seed_ticket_prices():
    """Seed delegate ticket pricing for Pollination Africa Summit 2026"""
    print("🎫 Seeding delegate ticket prices for Pollination Africa Summit 2026...")

    early_bird_deadline = datetime(2026, 4, 15, 23, 59, 59)

    # All tickets share the same base inclusions:
    # - Full 3-day access to all summit sessions
    # - Catering (breakfast, lunch, and refreshment breaks)
    # - Summit materials and delegate kit
    # - Simultaneous interpretation (English, French, Arabic)
    shared_inclusions = {
        "currency": "USD",
        "includes_lunch": True,
        "includes_materials": True,
        "includes_certificate": True,
        "includes_networking": True,
        "is_active": True,
    }

    tickets = [
        {
            "ticket_type": AttendeeTicketType.STANDARD,
            "name": "International Delegate Pass",
            "description": "Full summit access for international delegates. Open to all participants outside the African Union.",
            "price": Decimal("300.00"),
            "early_bird_price": Decimal("240.00"),
            "early_bird_deadline": early_bird_deadline,
            **shared_inclusions,
        },
        {
            "ticket_type": AttendeeTicketType.AFRICAN,
            "name": "Africa-Based Delegate Pass",
            "description": "Full summit access for delegates residing in or affiliated with African Union member states.",
            "price": Decimal("250.00"),
            "early_bird_price": Decimal("200.00"),
            "early_bird_deadline": early_bird_deadline,
            **shared_inclusions,
        },
        {
            "ticket_type": AttendeeTicketType.STUDENT,
            "name": "Student Pass (Africa-Based Institutions)",
            "description": "Full summit access for students enrolled at Africa-based institutions. Valid student ID required at check-in.",
            "price": Decimal("180.00"),
            "early_bird_price": Decimal("145.00"),
            "early_bird_deadline": early_bird_deadline,
            **shared_inclusions,
        },
        {
            "ticket_type": AttendeeTicketType.GROUP,
            "name": "Farmer Groups Pass (5-10 members)",
            "description": "Group registration for farmer cooperatives and agricultural groups. Covers 5 to 10 members under a single registration.",
            "price": Decimal("1500.00"),
            "early_bird_price": Decimal("1200.00"),
            "early_bird_deadline": early_bird_deadline,
            **shared_inclusions,
        },
    ]

    for ticket_data in tickets:
        existing = TicketPrice.query.filter_by(
            ticket_type=ticket_data["ticket_type"]
        ).first()

        if existing:
            # Update existing ticket with new pricing and names
            for key, value in ticket_data.items():
                if key != "ticket_type":
                    setattr(existing, key, value)
            print(f"  ↻ Updated: {ticket_data['name']} - ${ticket_data['price']} USD")
        else:
            ticket = TicketPrice(**ticket_data)
            db.session.add(ticket)
            print(f"  ✓ Added: {ticket_data['name']} - ${ticket_data['price']} USD")

    # Deactivate VIP ticket if it exists
    vip_ticket = TicketPrice.query.filter_by(ticket_type=AttendeeTicketType.VIP).first()
    if vip_ticket and vip_ticket.is_active:
        vip_ticket.is_active = False
        print("  ✗ Deactivated: VIP Delegate Pass")

    db.session.commit()
    print("✅ Ticket prices seeded\n")


def seed_promo_codes():
    """Seed promo codes for Pollination Africa Summit 2026"""
    print("🎟️  Seeding promo codes...")

    # EARLYBIRD2026 - 20% off all delegate tickets
    earlybird = PromoCode.query.filter_by(code="EARLYBIRD2026").first()

    if earlybird:
        # Update existing promo code
        earlybird.description = "Early Bird Discount 2026 - Save 20% on all delegate tickets"
        earlybird.discount_value = Decimal("20.00")
        earlybird.valid_until = datetime(2026, 3, 15, 23, 59, 59)
        print(f"  ↻ Updated: EARLYBIRD2026 - 20% off (valid until March 15, 2026)")
    else:
        earlybird = PromoCode(
            code="EARLYBIRD2026",
            description="Early Bird Discount 2026 - Save 20% on all delegate tickets",
            discount_type="percentage",
            discount_value=Decimal("20.00"),
            applicable_to_attendees=True,
            applicable_to_exhibitors=False,
            max_uses=500,
            max_uses_per_user=1,
            valid_from=datetime.now(),
            valid_until=datetime(2026, 3, 15, 23, 59, 59),
            is_active=True,
        )
        db.session.add(earlybird)
        print(f"  ✓ Added: EARLYBIRD2026 - 20% off (valid until March 15, 2026)")

    db.session.commit()
    print("✅ Promo codes seeded\n")


def seed_exhibitor_packages():
    """Seed exhibitor package pricing for Pollination Africa Symposium"""
    print("📦 Seeding exhibitor packages for Pollination Africa Symposium...")

    # ===== TEST DATA - $0.10 for easy testing =====
    # packages = [
    #     {
    #         "package_type": ExhibitorPackage.BRONZE,
    #         "name": "Standard Booth (3m x 3m)",
    #         "description": "9 SQM booth - ideal for startups, conservation groups, and small businesses",
    #         "price": Decimal("0.10"),
    #         "currency": "USD",
    #         "booth_size": "3m x 3m (9 SQM)",
    #         "included_passes": 2,
    #         "includes_electricity": False,
    #         "includes_wifi": False,
    #         "includes_furniture": True,
    #         "includes_catalog_listing": True,
    #         "includes_social_media": False,
    #         "includes_speaking_slot": False,
    #         "max_quantity": 10,
    #         "is_active": True,
    #     },
    #     {
    #         "package_type": ExhibitorPackage.SILVER,
    #         "name": "Medium Booth (5m x 5m)",
    #         "description": "25 SQM booth - enhanced space with electricity, WiFi, and social media promotion",
    #         "price": Decimal("0.10"),
    #         "currency": "USD",
    #         "booth_size": "5m x 5m (25 SQM)",
    #         "included_passes": 4,
    #         "includes_electricity": True,
    #         "includes_wifi": True,
    #         "includes_furniture": True,
    #         "includes_catalog_listing": True,
    #         "includes_social_media": True,
    #         "includes_speaking_slot": False,
    #         "max_quantity": 5,
    #         "is_active": True,
    #     },
    #     {
    #         "package_type": ExhibitorPackage.GOLD,
    #         "name": "Large Booth (6m x 5m)",
    #         "description": "30 SQM booth - premium package with speaking slot, lead retrieval, and enhanced visibility",
    #         "price": Decimal("0.10"),
    #         "currency": "USD",
    #         "booth_size": "6m x 5m (30 SQM)",
    #         "included_passes": 6,
    #         "includes_electricity": True,
    #         "includes_wifi": True,
    #         "includes_furniture": True,
    #         "includes_catalog_listing": True,
    #         "includes_social_media": True,
    #         "includes_speaking_slot": True,
    #         "max_quantity": 5,
    #         "is_active": True,
    #     },
    #     {
    #         "package_type": ExhibitorPackage.CUSTOM,
    #         "name": "Custom Partnership Package",
    #         "description": "Tailored solution for unique requirements - contact us to design your perfect package",
    #         "price": Decimal("0.00"),
    #         "currency": "USD",
    #         "booth_size": "Custom",
    #         "included_passes": 0,
    #         "includes_electricity": False,
    #         "includes_wifi": False,
    #         "includes_furniture": False,
    #         "includes_catalog_listing": True,
    #         "includes_social_media": False,
    #         "includes_speaking_slot": False,
    #         "is_active": True,
    #     },
    # ]

    # ===== PRODUCTION DATA - Comment out for testing =====
    packages = [
        {
            "package_type": ExhibitorPackage.BRONZE,
            "name": "Standard Booth (3m x 3m)",
            "description": "9 SQM booth - ideal for startups, conservation groups, and small businesses",
            "price": Decimal("1450.00"),
            "currency": "USD",
            # TZS equivalent: 3,625,000
            "booth_size": "3m x 3m (9 SQM)",
            "included_passes": 2,
            "includes_electricity": False,
            "includes_wifi": False,
            "includes_furniture": True,
            "includes_catalog_listing": True,
            "includes_social_media": False,
            "includes_speaking_slot": False,
            "max_quantity": 10,
            "is_active": True,
        },
        {
            "package_type": ExhibitorPackage.SILVER,
            "name": "Medium Booth (5m x 5m)",
            "description": "25 SQM booth - enhanced space with electricity, WiFi, and social media promotion",
            "price": Decimal("2250.00"),
            "currency": "USD",
            # TZS equivalent: 5,625,000
            "booth_size": "5m x 5m (25 SQM)",
            "included_passes": 4,
            "includes_electricity": True,
            "includes_wifi": True,
            "includes_furniture": True,
            "includes_catalog_listing": True,
            "includes_social_media": True,
            "includes_speaking_slot": False,
            "max_quantity": 5,
            "is_active": True,
        },
        {
            "package_type": ExhibitorPackage.GOLD,
            "name": "Large Booth (6m x 5m)",
            "description": "30 SQM booth - premium package with speaking slot, lead retrieval, and enhanced visibility",
            "price": Decimal("2900.00"),
            "currency": "USD",
            # TZS equivalent: 7,250,000
            "booth_size": "6m x 5m (30 SQM)",
            "included_passes": 6,
            "includes_electricity": True,
            "includes_wifi": True,
            "includes_furniture": True,
            "includes_catalog_listing": True,
            "includes_social_media": True,
            "includes_speaking_slot": True,
            "max_quantity": 5,
            "is_active": True,
        },
        {
            "package_type": ExhibitorPackage.CUSTOM,
            "name": "Custom Partnership Package",
            "description": "Tailored solution for unique requirements - contact us to design your perfect package",
            "price": Decimal("0.00"),
            "currency": "USD",
            "booth_size": "Custom",
            "included_passes": 0,
            "includes_electricity": False,
            "includes_wifi": False,
            "includes_furniture": False,
            "includes_catalog_listing": True,
            "includes_social_media": False,
            "includes_speaking_slot": False,
            "is_active": True,
        },
    ]

    for package_data in packages:
        existing = ExhibitorPackagePrice.query.filter_by(
            package_type=package_data["package_type"]
        ).first()

        if not existing:
            package = ExhibitorPackagePrice(**package_data)
            db.session.add(package)
            print(f"  ✓ Added: {package.name} - ${package.price} {package.currency}")
        else:
            print(f"  ⊘ Exists: {package_data['name']}")

    db.session.commit()
    print("✅ Exhibitor packages seeded\n")


def seed_addon_items():
    """Seed add-on items for Pollination Africa Symposium"""
    print("➕ Seeding add-on items for Pollination Africa Symposium...")

    # ===== TEST DATA - $0.10 for easy testing =====
    addons = [
        # Exhibitor Add-ons
        {
            "name": "Extra Exhibitor Badge",
            "description": "Additional exhibitor badge for team members",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 10,
            "is_active": True,
        },
        {
            "name": "Electricity Connection",
            "description": "Power outlet for your booth (not included in Bronze package)",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "WiFi Access Point",
            "description": "Dedicated WiFi connection for your booth",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Premium Furniture Set",
            "description": "Upgraded furniture package (display table, chairs, shelving, spotlights)",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Corner Booth Upgrade",
            "description": "Upgrade to premium corner booth location (subject to availability)",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Entrance Booth Upgrade",
            "description": "Prime location near main entrance (limited availability)",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Product Demo Session",
            "description": "30-minute live product/conservation demonstration in demo area",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 2,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Main Hall Speaking Slot",
            "description": "20-minute speaking opportunity in main conference hall",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Workshop Hosting (2 hours)",
            "description": "Host a 2-hour workshop session with dedicated room and setup",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Lead Retrieval App License",
            "description": "Mobile app for scanning and capturing attendee leads with analytics",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Social Media Campaign",
            "description": "5 dedicated posts promoting your organization across event social channels",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 2,
            "is_active": True,
        },
        {
            "name": "Email Blast to Attendees",
            "description": "Dedicated email promotion sent to all registered attendees",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        # Attendee Add-ons
        {
            "name": "Pollinator Conservation Workshop Kit",
            "description": "Hands-on tools and materials for practical conservation workshops",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": False,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Field Guide Set",
            "description": "Comprehensive field guide set for East African pollinators (bees, butterflies, birds)",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "VIP Networking Dinner",
            "description": "Exclusive evening networking dinner with keynote speakers and conservation leaders",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Pollinator Garden Field Trip",
            "description": "Guided visit to model pollinator gardens and conservation sites in Arusha region",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Butterfly Farm Tour",
            "description": "Half-day tour of commercial butterfly farming operation with expert guidance",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Bird Habitat Safari",
            "description": "Early morning bird-watching safari focusing on pollinating bird species",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Beekeeping Site Visit",
            "description": "Guided visit to local beekeeping operations and honey processing facilities",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Professional Photography Session",
            "description": "Professional headshot and event photography session",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Conference Proceedings USB",
            "description": "USB drive with all presentations, research papers, and conference materials",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Certificate of Participation (Framed)",
            "description": "Professionally framed certificate of participation suitable for display",
            "price": Decimal("0.10"),
            "currency": "USD",
            "for_attendees": True,
            "for_exhibitors": False,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
    ]

    for addon_data in addons:
        existing = AddOnItem.query.filter_by(name=addon_data["name"]).first()

        if not existing:
            addon = AddOnItem(**addon_data)
            db.session.add(addon)
            print(f"  ✓ Added: {addon.name} - ${addon.price} {addon.currency}")
        else:
            print(f"  ⊘ Exists: {addon_data['name']}")

    db.session.commit()
    print("✅ Add-on items seeded\n")


def seed_users():
    """Seed test admin users for Pollination Africa Symposium"""
    print("👥 Seeding admin users...")

    users = [
        {
            "name": "Admin User",
            "email": "admin@pollination.africa",
            "password": "Admin@2025",
            "role": UserRole.ADMIN,
            "is_active": True,
        },
        {
            "name": "Staff Member",
            "email": "staff@pollination.africa",
            "password": "Staff@2025",
            "role": UserRole.STAFF,
            "is_active": True,
        },
        {
            "name": "Event Organizer",
            "email": "organizer@pollination.africa",
            "password": "Organizer@2025",
            "role": UserRole.ORGANIZER,
            "is_active": True,
        },
    ]

    for user_data in users:
        existing = User.query.filter_by(email=user_data["email"]).first()

        if not existing:
            user = User(
                name=user_data["name"],
                email=user_data["email"],
                role=user_data["role"],
                is_active=user_data["is_active"],
            )
            user.set_password(user_data["password"])
            db.session.add(user)
            print(f"  ✓ Added: {user.name} ({user.role.value}) - {user.email}")
        else:
            print(f"  ⊘ Exists: {user_data['email']} ({user_data['role'].value})")

    db.session.commit()
    print("✅ Admin users seeded\n")


def seed_all():
    """Run all seed functions for Pollination Africa Summit 2026"""
    print("\n" + "=" * 70)
    print("🦋 POLLINATION AFRICA SUMMIT 2026 - DATABASE SEEDING")
    print("   Celebrating All Pollinators: Bees, Butterflies, Birds & Beyond")
    print("=" * 70 + "\n")

    seed_users()
    seed_ticket_prices()
    seed_promo_codes()
    seed_exhibitor_packages()
    # seed_addon_items()

    print("=" * 70)
    print("✅ All seed data loaded successfully!")
    print("\n📧 Test Login Credentials:")
    print("   Admin:     admin@pollination.africa / Admin@2025")
    print("   Staff:     staff@pollination.africa / Staff@2025")
    print("   Organizer: organizer@pollination.africa / Organizer@2025")
    print("\n📧 Contact: info@pollinationafrica.org")
    print("🌐 Website: https://www.pollinationafrica.org")
    print("=" * 70 + "\n")


# ============================================
# CLI COMMAND HELPER
# ============================================


def reset_and_seed():
    """
    DANGEROUS: Clear all pricing data and users, then reseed
    Use only in development or when migrating from BEEASY
    """
    print("\n⚠️  WARNING: This will DELETE all existing pricing data and users!\n")
    response = input("Type 'YES' to continue: ")

    if response != "YES":
        print("❌ Seeding cancelled")
        return

    print("\n🗑️  Clearing existing data...")

    # Delete in correct order to respect foreign keys
    AddOnItem.query.delete()
    ExhibitorPackagePrice.query.delete()
    TicketPrice.query.delete()
    User.query.delete()

    db.session.commit()
    print("✅ Old data cleared\n")

    # Seed new data
    seed_all()


if __name__ == "__main__":
    # For testing - in production use via Flask CLI
    from app import create_app

    app = create_app()
    with app.app_context():
        seed_all()
