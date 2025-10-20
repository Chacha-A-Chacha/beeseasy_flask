"""
Database seed functions for BEEASY2025
Populates initial pricing and configuration data
"""

from decimal import Decimal
from datetime import datetime, timedelta
from app.extensions import db
from app.models import (
    TicketPrice, ExhibitorPackagePrice, AddOnItem,
    AttendeeTicketType, ExhibitorPackage
)


def seed_ticket_prices():
    """Seed attendee ticket pricing"""
    print("🎫 Seeding ticket prices...")

    tickets = [
        {
            'ticket_type': AttendeeTicketType.FREE,
            'name': 'Free Pass',
            'description': 'Basic conference access with networking opportunities',
            'price': Decimal('0.00'),
            'currency': 'TSH',
            'includes_lunch': False,
            'includes_materials': False,
            'includes_certificate': False,
            'includes_networking': True,
            'is_active': True,
        },
        {
            'ticket_type': AttendeeTicketType.STANDARD,
            'name': 'Standard Pass',
            'description': 'Full conference access with lunch, materials, and certificate',
            'price': Decimal('50000.00'),
            'currency': 'TSH',
            'includes_lunch': True,
            'includes_materials': True,
            'includes_certificate': True,
            'includes_networking': True,
            'is_active': True,
        },
        {
            'ticket_type': AttendeeTicketType.VIP,
            'name': 'VIP Pass',
            'description': 'Premium experience with VIP lounge, priority seating, and exclusive networking',
            'price': Decimal('150000.00'),
            'currency': 'TSH',
            'includes_lunch': True,
            'includes_materials': True,
            'includes_certificate': True,
            'includes_networking': True,
            'max_quantity': 50,
            'is_active': True,
        },
        {
            'ticket_type': AttendeeTicketType.STUDENT,
            'name': 'Student Pass',
            'description': 'Discounted pass for students with valid ID',
            'price': Decimal('25000.00'),
            'currency': 'TSH',
            'includes_lunch': True,
            'includes_materials': True,
            'includes_certificate': True,
            'includes_networking': True,
            'is_active': True,
        },
        {
            'ticket_type': AttendeeTicketType.GROUP,
            'name': 'Group Pass (5+)',
            'description': 'Special pricing for groups of 5 or more',
            'price': Decimal('40000.00'),
            'currency': 'TSH',
            'includes_lunch': True,
            'includes_materials': True,
            'includes_certificate': True,
            'includes_networking': True,
            'is_active': True,
        },
        {
            'ticket_type': AttendeeTicketType.EARLY_BIRD,
            'name': 'Early Bird Pass',
            'description': 'Limited time special pricing - Save 40%!',
            'price': Decimal('30000.00'),
            'currency': 'TSH',
            'includes_lunch': True,
            'includes_materials': True,
            'includes_certificate': True,
            'includes_networking': True,
            'max_quantity': 100,
            'early_bird_deadline': datetime.now() + timedelta(days=60),
            'is_active': True,
        },
        {
            'ticket_type': AttendeeTicketType.SPEAKER,
            'name': 'Speaker/Presenter Pass',
            'description': 'Complimentary pass for confirmed speakers and presenters',
            'price': Decimal('0.00'),
            'currency': 'TSH',
            'includes_lunch': True,
            'includes_materials': True,
            'includes_certificate': True,
            'includes_networking': True,
            'is_active': True,
        },
        {
            'ticket_type': AttendeeTicketType.VOLUNTEER,
            'name': 'Volunteer Pass',
            'description': 'Complimentary pass for event volunteers - Thank you!',
            'price': Decimal('0.00'),
            'currency': 'TSH',
            'includes_lunch': True,
            'includes_materials': False,
            'includes_certificate': True,
            'includes_networking': True,
            'is_active': True,
        },
    ]

    for ticket_data in tickets:
        existing = TicketPrice.query.filter_by(
            ticket_type=ticket_data['ticket_type']
        ).first()

        if not existing:
            ticket = TicketPrice(**ticket_data)
            db.session.add(ticket)
            print(f"  ✓ Added: {ticket.name}")
        else:
            print(f"  ⊘ Exists: {ticket_data['name']}")

    db.session.commit()
    print("✅ Ticket prices seeded\n")


def seed_exhibitor_packages():
    """Seed exhibitor package pricing"""
    print("📦 Seeding exhibitor packages...")

    packages = [
        {
            'package_type': ExhibitorPackage.BRONZE,
            'name': 'Bronze Package',
            'description': 'Entry-level exhibition package - perfect for startups',
            'price': Decimal('500.00'),
            'currency': 'USD',
            'booth_size': '3x3m',
            'included_passes': 2,
            'includes_electricity': False,
            'includes_wifi': False,
            'includes_furniture': True,
            'includes_catalog_listing': True,
            'includes_social_media': False,
            'includes_speaking_slot': False,
            'is_active': True,
        },
        {
            'package_type': ExhibitorPackage.SILVER,
            'name': 'Silver Package',
            'description': 'Enhanced exhibition with electricity and WiFi',
            'price': Decimal('1000.00'),
            'currency': 'USD',
            'booth_size': '3x6m',
            'included_passes': 4,
            'includes_electricity': True,
            'includes_wifi': True,
            'includes_furniture': True,
            'includes_catalog_listing': True,
            'includes_social_media': True,
            'includes_speaking_slot': False,
            'is_active': True,
        },
        {
            'package_type': ExhibitorPackage.GOLD,
            'name': 'Gold Package',
            'description': 'Premium package with speaking slot and lead retrieval',
            'price': Decimal('2500.00'),
            'currency': 'USD',
            'booth_size': '6x6m',
            'included_passes': 6,
            'includes_electricity': True,
            'includes_wifi': True,
            'includes_furniture': True,
            'includes_catalog_listing': True,
            'includes_social_media': True,
            'includes_speaking_slot': True,
            'is_active': True,
        },
        {
            'package_type': ExhibitorPackage.PLATINUM,
            'name': 'Platinum Package',
            'description': 'Ultimate package with keynote opportunity and workshop hosting',
            'price': Decimal('5000.00'),
            'currency': 'USD',
            'booth_size': '6x9m',
            'included_passes': 10,
            'includes_electricity': True,
            'includes_wifi': True,
            'includes_furniture': True,
            'includes_catalog_listing': True,
            'includes_social_media': True,
            'includes_speaking_slot': True,
            'max_quantity': 5,
            'is_active': True,
        },
        {
            'package_type': ExhibitorPackage.CUSTOM,
            'name': 'Custom Package',
            'description': 'Tailored solution for unique requirements - contact us',
            'price': Decimal('0.00'),
            'currency': 'USD',
            'booth_size': 'Custom',
            'included_passes': 0,
            'includes_electricity': False,
            'includes_wifi': False,
            'includes_furniture': False,
            'includes_catalog_listing': True,
            'includes_social_media': False,
            'includes_speaking_slot': False,
            'is_active': True,
        },
    ]

    for package_data in packages:
        existing = ExhibitorPackagePrice.query.filter_by(
            package_type=package_data['package_type']
        ).first()

        if not existing:
            package = ExhibitorPackagePrice(**package_data)
            db.session.add(package)
            print(f"  ✓ Added: {package.name}")
        else:
            print(f"  ⊘ Exists: {package_data['name']}")

    db.session.commit()
    print("✅ Exhibitor packages seeded\n")


def seed_addon_items():
    """Seed add-on items for purchase"""
    print("➕ Seeding add-on items...")

    addons = [
        # Exhibitor Add-ons
        {
            'name': 'Extra Exhibitor Badge',
            'description': 'Additional exhibitor badge for staff members',
            'price': Decimal('50.00'),
            'currency': 'USD',
            'for_attendees': False,
            'for_exhibitors': True,
            'max_quantity_per_registration': 10,
            'is_active': True,
        },
        {
            'name': 'Electricity Connection',
            'description': 'Power outlet for your booth (not included in Bronze)',
            'price': Decimal('100.00'),
            'currency': 'USD',
            'for_attendees': False,
            'for_exhibitors': True,
            'max_quantity_per_registration': 1,
            'is_active': True,
        },
        {
            'name': 'WiFi Access',
            'description': 'Dedicated WiFi connection for your booth',
            'price': Decimal('75.00'),
            'currency': 'USD',
            'for_attendees': False,
            'for_exhibitors': True,
            'max_quantity_per_registration': 1,
            'is_active': True,
        },
        {
            'name': 'Furniture Upgrade',
            'description': 'Premium furniture set (table, chairs, display shelves)',
            'price': Decimal('150.00'),
            'currency': 'USD',
            'for_attendees': False,
            'for_exhibitors': True,
            'max_quantity_per_registration': 1,
            'is_active': True,
        },
        {
            'name': 'Product Demo Slot',
            'description': '30-minute live product demonstration session',
            'price': Decimal('200.00'),
            'currency': 'USD',
            'for_attendees': False,
            'for_exhibitors': True,
            'max_quantity_per_registration': 2,
            'requires_approval': True,
            'is_active': True,
        },
        {
            'name': 'Speaking Slot',
            'description': '20-minute speaking opportunity in main hall',
            'price': Decimal('500.00'),
            'currency': 'USD',
            'for_attendees': False,
            'for_exhibitors': True,
            'max_quantity_per_registration': 1,
            'requires_approval': True,
            'is_active': True,
        },
        {
            'name': 'Lead Retrieval App',
            'description': 'Mobile app for scanning and capturing attendee leads',
            'price': Decimal('100.00'),
            'currency': 'USD',
            'for_attendees': False,
            'for_exhibitors': True,
            'max_quantity_per_registration': 1,
            'is_active': True,
        },
        # Attendee Add-ons
        {
            'name': 'Workshop Kit',
            'description': 'Hands-on beekeeping tools and materials for workshops',
            'price': Decimal('25.00'),
            'currency': 'USD',
            'for_attendees': True,
            'for_exhibitors': False,
            'max_quantity_per_registration': 1,
            'is_active': True,
        },
        {
            'name': 'Networking Dinner',
            'description': 'Exclusive evening networking dinner with speakers',
            'price': Decimal('50.00'),
            'currency': 'USD',
            'for_attendees': True,
            'for_exhibitors': True,
            'max_quantity_per_registration': 1,
            'is_active': True,
        },
        {
            'name': 'Field Trip',
            'description': 'Guided visit to local beekeeping operation',
            'price': Decimal('35.00'),
            'currency': 'USD',
            'for_attendees': True,
            'for_exhibitors': True,
            'max_quantity_per_registration': 1,
            'is_active': True,
        },
        {
            'name': 'Professional Headshot',
            'description': 'Professional photography session',
            'price': Decimal('30.00'),
            'currency': 'USD',
            'for_attendees': True,
            'for_exhibitors': True,
            'max_quantity_per_registration': 1,
            'is_active': True,
        },
    ]

    for addon_data in addons:
        existing = AddOnItem.query.filter_by(name=addon_data['name']).first()

        if not existing:
            addon = AddOnItem(**addon_data)
            db.session.add(addon)
            print(f"  ✓ Added: {addon.name}")
        else:
            print(f"  ⊘ Exists: {addon_data['name']}")

    db.session.commit()
    print("✅ Add-on items seeded\n")


def seed_all():
    """Run all seed functions"""
    print("\n🌱 Starting database seeding...\n")
    print("=" * 50)

    seed_ticket_prices()
    seed_exhibitor_packages()
    seed_addon_items()

    print("=" * 50)
    print("✅ All seed data loaded successfully!\n")
