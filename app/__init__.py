import os

from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import inspect

# Import config dictionary
from app.config import config

# Import extensions
from app.extensions import bcrypt, cors, db, login_manager, mail, migrate

# Initialize CSRF separately for fine-grained control
csrf = CSRFProtect()


def ensure_tables_exist(app):
    """
    Check if tables exist and create them if they don't.
    Safe to run in all environments.
    Gracefully handles database connection errors (e.g., Neon auto-suspend).
    """
    with app.app_context():
        try:
            # Import all models to ensure SQLAlchemy knows about them
            from app.models import (
                AddOnItem,
                AddOnPurchase,
                AttendeeRegistration,
                EmailLog,
                ExchangeRate,
                ExhibitorPackagePrice,
                ExhibitorRegistration,
                Payment,
                PromoCode,
                PromoCodeUsage,
                Registration,
                TicketPrice,
                User,
            )

            # Check if tables exist using inspector
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()

            # Get all model table names
            model_tables = [table.name for table in db.Model.metadata.tables.values()]

            # Find missing tables
            missing_tables = [
                table for table in model_tables if table not in existing_tables
            ]

            if missing_tables:
                app.logger.info(f"Creating missing tables: {', '.join(missing_tables)}")
                db.create_all()
                app.logger.info("✅ Database tables created successfully")
            else:
                app.logger.info("✅ All database tables already exist")
        except Exception as e:
            # Log warning but don't crash - database might be sleeping (Neon scale-to-zero)
            app.logger.warning(
                f"⚠️ Could not verify database tables at startup: {str(e)}"
            )
            app.logger.warning("Database will be initialized on first request")


def create_app(config_name=None):
    """
    Application factory for Bee Easy Flask App.
    Initializes extensions, blueprints, and global context.
    """

    # --- Flask App Initialization ---
    app = Flask(__name__, instance_relative_config=True)

    os.makedirs(app.instance_path, exist_ok=True)

    # Use chosen config (default to development)
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config[config_name])

    # --- Initialize Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    csrf.init_app(app)

    # --- Login Manager Setup ---
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # --- Register Blueprints ---
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.payment import payments_bp
    from app.routes.register import register_bp

    # Exempt API routes from CSRF protection
    csrf.exempt(api_bp)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(register_bp, url_prefix="/register")
    app.register_blueprint(payments_bp, url_prefix="/payments")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # --- Register CLI Commands ---
    from app.cli import register_cli_commands

    register_cli_commands(app)

    # --- Auto-create tables if they don't exist ---
    # Safe to run in all environments - only creates missing tables
    ensure_tables_exist(app)

    # --- Database Wake-up Hook (for Neon scale-to-zero) ---
    @app.before_request
    def ensure_db_awake():
        """
        Ensure database is awake before processing requests.
        This prevents connection errors when Neon scales to zero.
        """
        # Skip for static files
        if request.endpoint and "static" in request.endpoint:
            return None

        # Check if we need database for this request
        # (Most requests will need it, but some might not)
        try:
            from app.utils.database import ensure_database_connection

            # Try to ensure connection (with retry logic built-in)
            if not ensure_database_connection():
                # If we can't establish connection after retries, log it
                app.logger.error("Failed to establish database connection for request")
                # Don't block the request - let it fail naturally with better error handling
        except Exception as e:
            # Gracefully handle any errors in the database wake-up process
            app.logger.warning(f"Database wake-up check failed: {str(e)}")
            # Continue with request - database errors will be handled by route handlers

        return None

    # --- Template Context Processors ---
    @app.context_processor
    def inject_globals():
        """
        Inject global variables (e.g. event name, organization info)
        into all templates and emails.
        """
        return dict(
            event_name=app.config.get(
                "EVENT_NAME", "Pollination Africa Symposium 2026"
            ),
            event_short_name=app.config.get(
                "EVENT_SHORT_NAME", "Pollination Africa 2026"
            ),
            event_date=app.config.get("EVENT_DATE", "3-5 June 2026"),
            event_location=app.config.get(
                "EVENT_LOCATION",
                "Arusha International Conference Centre, Arusha, Tanzania",
            ),
            event_time=app.config.get("EVENT_TIME", "8:00 AM - 6:00 PM"),
            organization_name=app.config.get("ORGANIZATION_NAME", "Pollination Africa"),
            contact_email=app.config.get("CONTACT_EMAIL", "info@pollination.africa"),
            support_phone=app.config.get("SUPPORT_PHONE", "+254 719 740 938"),
            support_whatsapp=app.config.get("SUPPORT_WHATSAPP", "+254 719 740 938"),
            website_url=app.config.get("WEBSITE_URL", "https://pollination.africa"),
        )

    # --- Error Handlers ---
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template("errors/500.html"), 500

    # --- Shell Context (for Flask CLI) ---
    @app.shell_context_processor
    def make_shell_context():
        from app.models import (
            AddOnItem,
            AttendeeRegistration,
            ExhibitorPackagePrice,
            ExhibitorRegistration,
            Payment,
            Registration,
            TicketPrice,
            User,
        )

        return {
            "db": db,
            "User": User,
            "Registration": Registration,
            "AttendeeRegistration": AttendeeRegistration,
            "ExhibitorRegistration": ExhibitorRegistration,
            "TicketPrice": TicketPrice,
            "ExhibitorPackagePrice": ExhibitorPackagePrice,
            "AddOnItem": AddOnItem,
            "Payment": Payment,
        }

    return app
