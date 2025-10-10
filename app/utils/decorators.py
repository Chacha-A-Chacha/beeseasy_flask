from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def role_required(*roles):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role.value not in roles:
                flash("Access denied.", "danger")
                return redirect(url_for('main.index'))
            return func(*args, **kwargs)
        return decorated_view
    return wrapper
