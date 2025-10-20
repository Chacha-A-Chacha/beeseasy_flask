import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration shared across environments."""
    
    # --- Core App Settings ---
    SECRET_KEY = os.getenv('SECRET_KEY', 'super-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f"sqlite:///{os.path.abspath(os.path.join(basedir, '..', 'instance', 'summit.db'))}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Mail (SMTP) Configuration ---
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')  # e.g. info@beeseasy.org
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'info@beeseasy.org')

    # --- Security ---
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_DURATION = 3600 * 24 * 7  # 1 week
    WTF_CSRF_ENABLED = True

    # Stripe
    STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

    # Bank Details
    BANK_NAME = os.getenv('BANK_NAME', 'Your Bank')
    BANK_ACCOUNT_NAME = os.getenv('BANK_ACCOUNT_NAME', 'BEEASY Organization')
    BANK_ACCOUNT_NUMBER = os.getenv('BANK_ACCOUNT_NUMBER')
    BANK_SWIFT = os.getenv('BANK_SWIFT')
    BANK_BRANCH = os.getenv('BANK_BRANCH', 'Main Branch')

    # --- Other Options ---
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CORS_HEADERS = 'Content-Type'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# Config dictionary for easy reference in app factory
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
