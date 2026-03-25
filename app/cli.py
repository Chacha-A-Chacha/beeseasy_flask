"""
CLI commands for database management and seeding
Usage: flask <command>
"""

import click
from flask.cli import with_appcontext
from app.extensions import db
from app.seeds import seed_all, seed_ticket_prices, seed_exhibitor_packages, seed_addon_items


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database with tables."""

    from flask import current_app
    import os

    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    print("💾 DB URI:", db_uri)

    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "")
        print("🧭 Full DB path:", os.path.abspath(db_path))
        print("📂 Exists?", os.path.exists(os.path.dirname(os.path.abspath(db_path))))

    # Import models first
    from app.models import (
        User, Registration, AttendeeRegistration, ExhibitorRegistration,
        TicketPrice, ExhibitorPackagePrice, AddOnItem, Payment,
        PromoCode, PromoCodeUsage, EmailLog, ExchangeRate
    )

    db.create_all()
    click.echo('✅ Database tables created successfully.')


@click.command('seed-db')
@with_appcontext
def seed_db_command():
    """Seed database with initial pricing data."""
    try:
        seed_all()
        click.echo('✅ Database seeding complete!')
    except Exception as e:
        click.echo(f'❌ Error seeding database: {str(e)}', err=True)
        raise


@click.command('reset-db')
@with_appcontext
def reset_db_command():
    """Drop all tables, recreate, and seed (DESTRUCTIVE!)."""
    if click.confirm('⚠️  WARNING: This will DELETE ALL DATA. Continue?'):
        try:
            click.echo('🗑️  Dropping all tables...')
            db.drop_all()

            click.echo('🔨 Creating tables...')
            db.create_all()

            click.echo('🌱 Seeding database...')
            seed_all()

            click.echo('✅ Database reset complete!')
        except Exception as e:
            click.echo(f'❌ Error resetting database: {str(e)}', err=True)
            raise
    else:
        click.echo('Operation cancelled.')


@click.command('check-db')
@with_appcontext
def check_db_command():
    """Check database status and display statistics."""
    from app.models import (
        Registration, AttendeeRegistration, ExhibitorRegistration,
        TicketPrice, ExhibitorPackagePrice, AddOnItem, Payment, User
    )

    click.echo('\n📊 Database Status\n')
    click.echo('=' * 50)

    # Check tables exist
    tables = {
        'Users': User,
        'Registrations': Registration,
        'Attendees': AttendeeRegistration,
        'Exhibitors': ExhibitorRegistration,
        'Ticket Prices': TicketPrice,
        'Exhibitor Packages': ExhibitorPackagePrice,
        'Add-on Items': AddOnItem,
        'Payments': Payment,
    }

    for name, model in tables.items():
        try:
            count = model.query.count()
            click.echo(f'✓ {name}: {count} records')
        except Exception as e:
            click.echo(f'✗ {name}: Error - {str(e)}')

    click.echo('=' * 50)

    # Check pricing configuration
    click.echo('\n💰 Pricing Configuration\n')

    active_tickets = TicketPrice.query.filter_by(is_active=True).count()
    active_packages = ExhibitorPackagePrice.query.filter_by(is_active=True).count()
    active_addons = AddOnItem.query.filter_by(is_active=True).count()

    click.echo(f'Active Ticket Types: {active_tickets}')
    click.echo(f'Active Exhibitor Packages: {active_packages}')
    click.echo(f'Active Add-on Items: {active_addons}')

    if active_tickets == 0:
        click.echo('\n⚠️  No ticket prices found. Run: flask seed-db')
    if active_packages == 0:
        click.echo('⚠️  No exhibitor packages found. Run: flask seed-db')

    click.echo('\n')


@click.command('seed-tickets')
@with_appcontext
def seed_tickets_command():
    """Seed only ticket prices."""
    try:
        seed_ticket_prices()
        click.echo('✅ Ticket prices seeded!')
    except Exception as e:
        click.echo(f'❌ Error: {str(e)}', err=True)
        raise


@click.command('seed-packages')
@with_appcontext
def seed_packages_command():
    """Seed only exhibitor packages."""
    try:
        seed_exhibitor_packages()
        click.echo('✅ Exhibitor packages seeded!')
    except Exception as e:
        click.echo(f'❌ Error: {str(e)}', err=True)
        raise


@click.command('seed-addons')
@with_appcontext
def seed_addons_command():
    """Seed only add-on items."""
    try:
        seed_addon_items()
        click.echo('✅ Add-on items seeded!')
    except Exception as e:
        click.echo(f'❌ Error: {str(e)}', err=True)
        raise


@click.command('create-admin')
@click.option('--email', prompt=True, help='Admin email address')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--name', prompt=True, help='Admin name')
@with_appcontext
def create_admin_command(email, password, name):
    """Create an admin user."""
    from app.models import User, UserRole

    # Check if user exists
    existing = User.query.filter_by(email=email).first()
    if existing:
        click.echo(f'[ERROR] User with email {email} already exists.')
        return

    # Create admin user
    admin = User(
        name=name,
        email=email,
        role=UserRole.ADMIN,
        is_active=True
    )
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    click.echo(f'[OK] Admin user created: {email}')


@click.command('expire-stale')
@click.option('--days', default=7, help='Expire PENDING registrations older than this many days.')
@click.option('--dry-run', is_flag=True, help='Show what would be expired without making changes.')
@with_appcontext
def expire_stale_command(days, dry_run):
    """Expire stale PENDING registrations and release their tickets."""
    from datetime import datetime, timedelta
    from app.models import (
        AttendeeRegistration,
        ExhibitorRegistration,
        Payment,
        PaymentStatus,
        Registration,
        RegistrationStatus,
    )

    cutoff = datetime.utcnow() - timedelta(days=days)

    stale = Registration.query.filter(
        Registration.status.in_([RegistrationStatus.PENDING, RegistrationStatus.PAYMENT_PENDING]),
        Registration.is_deleted == False,
        Registration.created_at < cutoff,
    ).all()

    if not stale:
        click.echo(f'No stale registrations older than {days} days.')
        return

    click.echo(f'Found {len(stale)} stale registration(s) older than {days} days:')

    expired_count = 0
    for reg in stale:
        click.echo(f'  {reg.reference_number}  {reg.email}  created {reg.created_at.date()}')

        if dry_run:
            continue

        # Release ticket/package inventory
        if isinstance(reg, AttendeeRegistration) and reg.ticket_price:
            reg.ticket_price.release_tickets(
                quantity=reg.group_size if reg.group_size else 1
            )
        elif isinstance(reg, ExhibitorRegistration) and reg.package_price:
            reg.package_price.release_package()

        # Mark registration as expired
        reg.status = RegistrationStatus.EXPIRED

        # Mark any pending/processing payments as failed
        for payment in reg.payments:
            if payment.payment_status in (PaymentStatus.PENDING, PaymentStatus.PROCESSING):
                payment.payment_status = PaymentStatus.FAILED
                payment.failure_reason = f'Registration expired after {days} days'

        expired_count += 1

    if dry_run:
        click.echo(f'[DRY RUN] Would expire {len(stale)} registration(s). Run without --dry-run to apply.')
    else:
        db.session.commit()
        click.echo(f'[OK] Expired {expired_count} registration(s) and released inventory.')


def register_cli_commands(app):
    """Register all CLI commands with Flask app."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)
    app.cli.add_command(reset_db_command)
    app.cli.add_command(check_db_command)
    app.cli.add_command(seed_tickets_command)
    app.cli.add_command(seed_packages_command)
    app.cli.add_command(seed_addons_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(expire_stale_command)
