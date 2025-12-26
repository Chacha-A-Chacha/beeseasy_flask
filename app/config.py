import os
import re

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


def _get_database_uri():
    """Helper function to determine the database URI."""
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")

    # Use Turso if credentials provided
    if turso_url and turso_token:
        return f"{turso_url}?authToken={turso_token}"

    # Check for Neon/PostgreSQL DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Convert postgresql:// to postgresql+psycopg2:// for Flask-SQLAlchemy sync operations
        # If you need async support, explicitly set DATABASE_URL with postgresql+asyncpg://
        if database_url.startswith("postgresql://"):
            return re.sub(r"^postgresql://", "postgresql+psycopg2://", database_url)
        return database_url

    # Fall back to SQLite
    return f"sqlite:///{os.path.abspath(os.path.join(basedir, '..', 'instance', 'app.db'))}"


class Config:
    """Base configuration shared across environments."""

    # --- Core App Settings ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key")
    SQLALCHEMY_DATABASE_URI: str = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # --- Database Connection Pool Settings (for Neon scale-to-zero) ---
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        # Test connections before using them from the pool (handles stale connections)
        "pool_pre_ping": True,
        # Recycle connections after 5 minutes (before Neon's scale-to-zero)
        "pool_recycle": 300,
        # Increase connection timeout to allow for database wake-up (default is 10s)
        "connect_args": {
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
        # Connection pool sizing
        "pool_size": 5,
        "max_overflow": 10,
    }

    # --- Mail (SMTP) Configuration ---
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "mail.pollination.africa")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 465))
    MAIL_USE_TLS: bool = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USE_SSL: bool = os.getenv("MAIL_USE_SSL", "False").lower() == "true"
    MAIL_USERNAME: str | None = os.getenv(
        "MAIL_USERNAME"
    )  # e.g. info@pollination.africa
    MAIL_PASSWORD: str | None = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER: str = os.getenv(
        "MAIL_DEFAULT_SENDER", "no-reply@pollination.africa"
    )

    # --- Security ---
    SESSION_COOKIE_SECURE: bool = False
    REMEMBER_COOKIE_DURATION: int = 3600 * 24 * 7  # 1 week
    WTF_CSRF_ENABLED: bool = True

    # --- Payment Gateway Configuration ---

    # Stripe
    STRIPE_PUBLIC_KEY: str | None = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY: str | None = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str | None = os.getenv("STRIPE_WEBHOOK_SECRET")

    # DPO Payment Gateway (Tanzania Mobile Money & Cards)
    DPO_COMPANY_TOKEN: str | None = os.getenv("DPO_COMPANY_TOKEN")
    DPO_SERVICE_TYPE: str | None = os.getenv("DPO_SERVICE_TYPE")
    DPO_CURRENCY: str = os.getenv("DPO_CURRENCY", "TZS")
    DPO_TEST_MODE: bool = os.getenv("DPO_TEST_MODE", "True").lower() == "true"

    # DPO API URLs
    DPO_API_URL_TEST: str = os.getenv(
        "DPO_API_URL_TEST", "https://secure1.sandbox.directpay.online"
    )
    DPO_API_URL_LIVE: str = os.getenv(
        "DPO_API_URL_LIVE", "https://secure.3gdirectpay.com"
    )

    # DPO Callback URLs (dynamically set based on environment)
    DPO_REDIRECT_URL: str | None = os.getenv(
        "DPO_REDIRECT_URL"
    )  # e.g., https://yourdomain.com/payments/dpo/callback
    DPO_BACK_URL: str | None = os.getenv(
        "DPO_BACK_URL"
    )  # e.g., https://yourdomain.com/payments/cancel

    # Payment Token Lifetime (in hours) - DPO default is 5 hours
    DPO_PAYMENT_TOKEN_LIFETIME: int = int(os.getenv("DPO_PAYMENT_TOKEN_LIFETIME", "5"))

    # Bank Details (for manual bank transfer option)
    BANK_NAME: str = os.getenv("BANK_NAME", "Your Bank")
    BANK_ACCOUNT_NAME: str = os.getenv("BANK_ACCOUNT_NAME", "Pollination Africa")
    BANK_ACCOUNT_NUMBER: str | None = os.getenv("BANK_ACCOUNT_NUMBER")
    BANK_SWIFT: str | None = os.getenv("BANK_SWIFT")
    BANK_BRANCH: str = os.getenv("BANK_BRANCH", "Main Branch")

    # --- Event Configuration ---
    EVENT_NAME: str = os.getenv("EVENT_NAME", "Pollination Africa Summit 2026")
    EVENT_SHORT_NAME: str = os.getenv("EVENT_SHORT_NAME", "Pollination Africa 2026")
    EVENT_DATE: str = os.getenv("EVENT_DATE", "3-5 June 2026")
    EVENT_LOCATION: str = os.getenv("EVENT_LOCATION", "Arusha, Tanzania")
    EVENT_VENUE: str = os.getenv("EVENT_VENUE", "TBA")
    EVENT_TIME: str = os.getenv("EVENT_TIME", "Daily 9am-5pm")
    EVENT_DURATION: str = os.getenv("EVENT_DURATION", "3 Days")
    EVENT_THEME: str = os.getenv(
        "EVENT_THEME",
        "Harnessing Pollination for Food Security, Biodiversity, and Livelihoods",
    )
    EVENT_FORMAT: str = os.getenv(
        "EVENT_FORMAT", "Continental scientific, innovation & policy summit"
    )
    EVENT_GUEST_OF_HONOR: str = os.getenv("EVENT_GUEST_OF_HONOR", "TBC")
    ORGANIZATION_NAME: str = os.getenv("ORGANIZATION_NAME", "Pollination Africa")
    CONTACT_EMAIL: str = os.getenv("CONTACT_EMAIL", "info@pollination.africa")
    SUPPORT_PHONE: str = os.getenv("SUPPORT_PHONE", "+254 719 740 938")
    SUPPORT_WHATSAPP: str = os.getenv("SUPPORT_WHATSAPP", "+254 719 740 938")
    WEBSITE_URL: str = os.getenv("WEBSITE_URL", "https://pollination.africa")

    # --- Other Options ---
    DEBUG_TB_INTERCEPT_REDIRECTS: bool = False
    CORS_HEADERS: str = "Content-Type"


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG: bool = True
    ENV: str = "development"


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG: bool = False
    ENV: str = "production"
    SESSION_COOKIE_SECURE: bool = True


class TestingConfig(Config):
    """Testing configuration"""

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"


# Config dictionary for easy reference in app factory
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
