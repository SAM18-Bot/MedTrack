from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, session, g, redirect, url_for, flash
from app.config import Config
from app.extensions import csrf, limiter

def with_dr(name):
    if not name:
        return "Dr. Practitioner"
    s = str(name).strip()
    if s.lower().startswith("dr.") or s.lower().startswith("dr "):
        return s
    return f"Dr. {s}"

def get_current_user():
    if hasattr(g, '_current_user'):
        return g._current_user
    user_id = session.get('user_id')
    if not user_id:
        g._current_user = None
        return None
    try:
        from app.repositories.user_repository import UserRepository
        u = UserRepository().get_user(user_id)
        role = session.get('role', 'Patient')
        email = ''
        phone = ''
        if u:
            role = u.get('Role', role)
            email = u.get('Email', '')
            phone = u.get('Phone', '')
        
        name = email.split('@')[0].capitalize() if email else role
        spec = None

        if role == 'Patient':
            from app.repositories.patient_repository import PatientRepository
            repo = PatientRepository()
            p = repo.get_patient(user_id)
            if p and p.get('Name'):
                name = p['Name']
        elif role == 'Doctor':
            from app.repositories.doctor_repository import DoctorRepository
            repo = DoctorRepository()
            d = repo.get_doctor(user_id)
            if d and d.get('Name'):
                name = d['Name']
                spec = d.get('SpecializationID')
        elif role == 'Admin':
            name = 'Administrator'

        user_obj = {
            'id': user_id,
            'name': name or 'User',
            'email': email,
            'role': role.lower(),
            'role_display': role,
            'specialization': spec,
            'profile_picture': None,
            'phone': phone
        }
        g._current_user = user_obj
        return user_obj
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Note in get_current_user: {e}")
        fallback_role = session.get('role', 'Patient')
        user_obj = {
            'id': user_id,
            'name': fallback_role,
            'email': '',
            'role': fallback_role.lower(),
            'role_display': fallback_role,
            'specialization': None,
            'profile_picture': None,
            'phone': ''
        }
        g._current_user = user_obj
        return user_obj

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    if not app.config.get('SECRET_KEY') and not app.config.get('TESTING'):
        raise ValueError("No SECRET_KEY set for Flask application")
        
    csrf.init_app(app)
    limiter.init_app(app)
    app.jinja_env.filters['dr'] = with_dr

    from flask_wtf.csrf import CSRFError
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash("Your session timed out or form was expired. Please try signing in again.", "warning")
        return redirect(url_for('auth.login'))

    @app.context_processor
    def inject_user_context():
        cu = get_current_user()
        unread = 0
        if cu:
            try:
                from app.repositories.notification_repository import NotificationRepository
                unread = NotificationRepository().get_unread_count(cu['id'])
            except Exception:
                unread = 0
        return {
            'current_user': cu,
            'unread_notifications': unread
        }

    from app.blueprints.public import public_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.patient import patient_bp
    from app.blueprints.doctor import doctor_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.support import support_bp
    from app.blueprints.api import api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(support_bp, url_prefix='/support')
    app.register_blueprint(api_bp, url_prefix='/api')

    register_error_handlers(app)
    return app

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e): return render_template('errors/400.html'), 400
    @app.errorhandler(401)
    def unauthorized(e): return render_template('errors/401.html'), 401
    @app.errorhandler(403)
    def forbidden(e): return render_template('errors/403.html'), 403
    @app.errorhandler(404)
    def not_found(e): return render_template('errors/404.html'), 404
    @app.errorhandler(429)
    def too_many_requests(e): return render_template('errors/429.html'), 429
    @app.errorhandler(500)
    def internal_server_error(e): return render_template('errors/500.html'), 500
