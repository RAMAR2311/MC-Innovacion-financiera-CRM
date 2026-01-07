from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(roles):
    """
    Decorator to restrict access to routes based on user roles.
    :param roles: List of allowed roles (strings).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.rol not in roles:
                flash('No autorizado', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
