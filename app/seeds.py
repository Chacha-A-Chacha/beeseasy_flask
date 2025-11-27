"""
Database seed functions for Pollination Africa Symposium 2025
Populates initial pricing and configuration data for all pollinator conservation

Migration from BEEASY2025:
- Expanded from bees-only to all pollinators (bees, butterflies, birds, bats, beetles)
- Updated professional categories to be pollinator-inclusive
- Expanded industry categories to cover broader pollination ecosystem
- Updated branding and event names
- Revised pricing structure: Exhibition starts at $250 USD, Standard tickets at $30 USD equivalent
"""

from datetime import datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import (
    AddOnItem,
    AttendeeTicketType,
    ExhibitorPackage,
    ExhibitorPackagePrice,
    TicketPrice,
    User,
    UserRole,
)


def seed_ticket_prices():
    """Seed attendee ticket pricing for Pollination Africa Symposium"""
    print("🎫 Seeding ticket prices for Pollination Africa Symposium...")

    tickets = [
        {
            "ticket_type": AttendeeTicketType.FREE,
            "name": "Free Community Pass",
            "description": "Basic symposium access with networking opportunities for pollinator enthusiasts",
            "price": Decimal("0.00"),
            "currency": "TZS",
            "includes_lunch": False,
            "includes_materials": False,
            "includes_certificate": False,
            "includes_networking": True,
            "is_active": True,
        },
        {
            "ticket_type": AttendeeTicketType.STANDARD,
            "name": "Standard Steward Pass",
            "description": "Full symposium access with lunch, materials, and certificate of participation",
            "price": Decimal("75000.00"),
            "currency": "TZS",
            "includes_lunch": True,
            "includes_materials": True,
            "includes_certificate": True,
            "includes_networking": True,
            "is_active": True,
        },
        {
            "ticket_type": AttendeeTicketType.VIP,
            "name": "VIP Conservation Leader Pass",
            "description": "Premium experience with VIP lounge, priority seating, exclusive networking, and special pollinator garden tour",
            "price": Decimal("225000.00"),
            "currency": "TZS",
            "includes_lunch": True,
            "includes_materials": True,
            "includes_certificate": True,
            "includes_networking": True,
            "max_quantity": 50,
            "is_active": True,
        },
        {
            "ticket_type": AttendeeTicketType.STUDENT,
            "name": "Student & Researcher Pass",
            "description": "Discounted pass for students and early-career researchers with valid ID",
            "price": Decimal("37500.00"),
            "currency": "TZS",
            "includes_lunch": True,
            "includes_materials": True,
            "includes_certificate": True,
            "includes_networking": True,
            "is_active": True,
        },
        {
            "ticket_type": AttendeeTicketType.GROUP,
            "name": "Community Group Pass (5+)",
            "description": "Special pricing for conservation groups, NGOs, and community organizations (5+ members)",
            "price": Decimal("60000.00"),
            "currency": "TZS",
            "includes_lunch": True,
            "includes_materials": True,
            "includes_certificate": True,
            "includes_networking": True,
            "is_active": True,
        },
        {
            "ticket_type": AttendeeTicketType.EARLY_BIRD,
            "name": "Early Bird Pollinator Pass",
            "description": "Limited time special pricing for early supporters - Save 33%!",
            "price": Decimal("50000.00"),
            "currency": "TZS",
            "includes_lunch": True,
            "includes_materials": True,
            "includes_certificate": True,
            "includes_networking": True,
            "max_quantity": 100,
            "early_bird_deadline": datetime.now() + timedelta(days=60),
            "is_active": True,
        },
        {
            "ticket_type": AttendeeTicketType.SPEAKER,
            "name": "Speaker/Presenter Pass",
            "description": "Complimentary pass for confirmed speakers, presenters, and panelists",
            "price": Decimal("0.00"),
            "currency": "TZS",
            "includes_lunch": True,
            "includes_materials": True,
            "includes_certificate": True,
            "includes_networking": True,
            "is_active": True,
        },
        {
            "ticket_type": AttendeeTicketType.VOLUNTEER,
            "name": "Volunteer Pollinator Pass",
            "description": "Complimentary pass for event volunteers - Thank you for supporting pollinator conservation!",
            "price": Decimal("0.00"),
            "currency": "TZS",
            "includes_lunch": True,
            "includes_materials": False,
            "includes_certificate": True,
            "includes_networking": True,
            "is_active": True,
        },
    ]

    for ticket_data in tickets:
        existing = TicketPrice.query.filter_by(
            ticket_type=ticket_data["ticket_type"]
        ).first()

        if not existing:
            ticket = TicketPrice(**ticket_data)
            db.session.add(ticket)
            print(f"  ✓ Added: {ticket.name} - ${ticket.price} {ticket.currency}")
        else:
            print(f"  ⊘ Exists: {ticket_data['name']}")

    db.session.commit()
    print("✅ Ticket prices seeded\n")


def seed_exhibitor_packages():
    """Seed exhibitor package pricing for Pollination Africa Symposium"""
    print("📦 Seeding exhibitor packages for Pollination Africa Symposium...")

    packages = [
        {
            "package_type": ExhibitorPackage.BRONZE,
            "name": "Bronze Pollinator Package",
            "description": "Entry-level exhibition package - perfect for startups, conservation groups, and small businesses",
            "price": Decimal("625000.00"),
            "currency": "TZS",
            "booth_size": "3x3m",
            "included_passes": 2,
            "includes_electricity": False,
            "includes_wifi": False,
            "includes_furniture": True,
            "includes_catalog_listing": True,
            "includes_social_media": False,
            "includes_speaking_slot": False,
            "is_active": True,
        },
        {
            "package_type": ExhibitorPackage.SILVER,
            "name": "Silver Conservation Package",
            "description": "Enhanced exhibition with electricity, WiFi, and social media promotion",
            "price": Decimal("1250000.00"),
            "currency": "TZS",
            "booth_size": "3x6m",
            "included_passes": 4,
            "includes_electricity": True,
            "includes_wifi": True,
            "includes_furniture": True,
            "includes_catalog_listing": True,
            "includes_social_media": True,
            "includes_speaking_slot": False,
            "is_active": True,
        },
        {
            "package_type": ExhibitorPackage.GOLD,
            "name": "Gold Ecosystem Package",
            "description": "Premium package with speaking slot, lead retrieval, and enhanced visibility",
            "price": Decimal("3125000.00"),
            "currency": "TZS",
            "booth_size": "6x6m",
            "included_passes": 6,
            "includes_electricity": True,
            "includes_wifi": True,
            "includes_furniture": True,
            "includes_catalog_listing": True,
            "includes_social_media": True,
            "includes_speaking_slot": True,
            "is_active": True,
        },
        {
            "package_type": ExhibitorPackage.PLATINUM,
            "name": "Platinum Pollinator Champion Package",
            "description": "Ultimate package with keynote opportunity, workshop hosting, and maximum brand visibility",
            "price": Decimal("6250000.00"),
            "currency": "TZS",
            "booth_size": "6x9m",
            "included_passes": 10,
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
            "currency": "TZS",
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

    addons = [
        # Exhibitor Add-ons
        {
            "name": "Extra Exhibitor Badge",
            "description": "Additional exhibitor badge for team members",
            "price": Decimal("125000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 10,
            "is_active": True,
        },
        {
            "name": "Electricity Connection",
            "description": "Power outlet for your booth (not included in Bronze package)",
            "price": Decimal("250000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "WiFi Access Point",
            "description": "Dedicated WiFi connection for your booth",
            "price": Decimal("187500.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Premium Furniture Set",
            "description": "Upgraded furniture package (display table, chairs, shelving, spotlights)",
            "price": Decimal("375000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Corner Booth Upgrade",
            "description": "Upgrade to premium corner booth location (subject to availability)",
            "price": Decimal("500000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Entrance Booth Upgrade",
            "description": "Prime location near main entrance (limited availability)",
            "price": Decimal("750000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Product Demo Session",
            "description": "30-minute live product/conservation demonstration in demo area",
            "price": Decimal("500000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 2,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Main Hall Speaking Slot",
            "description": "20-minute speaking opportunity in main conference hall",
            "price": Decimal("1250000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Workshop Hosting (2 hours)",
            "description": "Host a 2-hour workshop session with dedicated room and setup",
            "price": Decimal("1875000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "requires_approval": True,
            "is_active": True,
        },
        {
            "name": "Lead Retrieval App License",
            "description": "Mobile app for scanning and capturing attendee leads with analytics",
            "price": Decimal("250000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Social Media Campaign",
            "description": "5 dedicated posts promoting your organization across event social channels",
            "price": Decimal("625000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 2,
            "is_active": True,
        },
        {
            "name": "Email Blast to Attendees",
            "description": "Dedicated email promotion sent to all registered attendees",
            "price": Decimal("1000000.00"),
            "currency": "TZS",
            "for_attendees": False,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        # Attendee Add-ons
        {
            "name": "Pollinator Conservation Workshop Kit",
            "description": "Hands-on tools and materials for practical conservation workshops",
            "price": Decimal("62500.00"),
            "currency": "TZS",
            "for_attendees": True,
            "for_exhibitors": False,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Field Guide Set",
            "description": "Comprehensive field guide set for East African pollinators (bees, butterflies, birds)",
            "price": Decimal("87500.00"),
            "currency": "TZS",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "VIP Networking Dinner",
            "description": "Exclusive evening networking dinner with keynote speakers and conservation leaders",
            "price": Decimal("125000.00"),
            "currency": "TZS",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Pollinator Garden Field Trip",
            "description": "Guided visit to model pollinator gardens and conservation sites in Arusha region",
            "price": Decimal("112500.00"),
            "currency": "TZS",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Butterfly Farm Tour",
            "description": "Half-day tour of commercial butterfly farming operation with expert guidance",
            "price": Decimal("100000.00"),
            "currency": "TZS",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Bird Habitat Safari",
            "description": "Early morning bird-watching safari focusing on pollinating bird species",
            "price": Decimal("137500.00"),
            "currency": "TZS",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Beekeeping Site Visit",
            "description": "Guided visit to local beekeeping operations and honey processing facilities",
            "price": Decimal("87500.00"),
            "currency": "TZS",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Professional Photography Session",
            "description": "Professional headshot and event photography session",
            "price": Decimal("75000.00"),
            "currency": "TZS",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Conference Proceedings USB",
            "description": "USB drive with all presentations, research papers, and conference materials",
            "price": Decimal("50000.00"),
            "currency": "TZS",
            "for_attendees": True,
            "for_exhibitors": True,
            "max_quantity_per_registration": 1,
            "is_active": True,
        },
        {
            "name": "Certificate of Participation (Framed)",
            "description": "Professionally framed certificate of participation suitable for display",
            "price": Decimal("37500.00"),
            "currency": "TZS",
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
    """Run all seed functions for Pollination Africa Symposium"""
    print("\n" + "=" * 70)
    print("🦋 POLLINATION AFRICA SYMPOSIUM 2025 - DATABASE SEEDING")
    print("   Celebrating All Pollinators: Bees, Butterflies, Birds & Beyond")
    print("=" * 70 + "\n")

    seed_users()
    seed_ticket_prices()
    seed_exhibitor_packages()
    seed_addon_items()

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
