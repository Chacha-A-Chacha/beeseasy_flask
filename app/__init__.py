import os
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

# Import extensions
from app.extensions import (
    db, migrate, login_manager, bcrypt, mail, cors
)

# Import config dictionary
from app.config import config

# Initialize CSRF separately for fine-grained control
csrf = CSRFProtect()


def create_app(config_name=None):
    """
    Application factory for Bee Easy Flask App.
    Initializes extensions, blueprints, and global context.
    """

    # --- Flask App Initialization ---
    app = Flask(__name__, instance_relative_config=True)

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
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.register import register_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    # Exempt API routes from CSRF protection
    csrf.exempt(api_bp)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(register_bp, url_prefix="/register")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # --- Template Context Processors ---
    @app.context_processor
    def inject_globals():
        """
        Inject global variables (e.g. event name, organization info)
        into all templates.
        """
        return dict(
            event_name="Bee East Africa Symposium",
            organization_name="Bee Easy Africa",
            contact_email="info@beeseasy.org"
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
        from app.models.user import User
        from app.models.registration import Registration
        return {'db': db, 'User': User, 'Registration': Registration}

    return app
