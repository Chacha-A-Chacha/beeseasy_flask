import os
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

    # Fall back to DATABASE_URL or SQLite
    return os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.abspath(os.path.join(basedir, '..', 'instance', 'app.db'))}",
    )


class Config:
    """Base configuration shared across environments."""

    # --- Core App Settings ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key")
    SQLALCHEMY_DATABASE_URI: str = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # --- Mail (SMTP) Configuration ---
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS: bool = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USE_SSL: bool = os.getenv("MAIL_USE_SSL", "False").lower() == "true"
    MAIL_USERNAME: str | None = os.getenv("MAIL_USERNAME")  # e.g. info@beeseasy.org
    MAIL_PASSWORD: str | None = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER: str = os.getenv("MAIL_DEFAULT_SENDER", "info@beeseasy.org")

    # --- Security ---
    SESSION_COOKIE_SECURE: bool = False
    REMEMBER_COOKIE_DURATION: int = 3600 * 24 * 7  # 1 week
    WTF_CSRF_ENABLED: bool = True

    # Stripe
    STRIPE_PUBLIC_KEY: str | None = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY: str | None = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str | None = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Bank Details
    BANK_NAME: str = os.getenv("BANK_NAME", "Your Bank")
    BANK_ACCOUNT_NAME: str = os.getenv("BANK_ACCOUNT_NAME", "BEEASY Organization")
    BANK_ACCOUNT_NUMBER: str | None = os.getenv("BANK_ACCOUNT_NUMBER")
    BANK_SWIFT: str | None = os.getenv("BANK_SWIFT")
    BANK_BRANCH: str = os.getenv("BANK_BRANCH", "Main Branch")

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
