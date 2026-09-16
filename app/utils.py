import json
from decimal import Decimal
from datetime import datetime, timezone
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_utc_now():
    return datetime.now(timezone.utc).isoformat()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "danger")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in.", "danger")
                return redirect(url_for('auth.login'))
            if session.get('role') not in roles:
                flash("You do not have permission to access this resource.", "danger")
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def owns_record(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ownership check logic to be implemented fully in future phase
        return f(*args, **kwargs)
    return decorated_function
