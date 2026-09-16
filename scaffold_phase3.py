import os

files = {
    "requirements.txt": """Flask==3.0.0
Flask-WTF==1.2.1
python-dotenv==1.0.0
boto3==1.33.0
botocore==1.33.0
pytest==7.4.3
gunicorn==21.2.0
reportlab==4.0.7
moto==5.2.3
Flask-Limiter==3.5.0
email-validator==2.1.0.post1
""",
    "app/extensions.py": """from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
""",
    "app/__init__.py": """from flask import Flask, render_template
from app.config import Config
from app.extensions import csrf, limiter

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    csrf.init_app(app)
    limiter.init_app(app)

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
""",
    "app/utils.py": """import json
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
""",
    "app/forms/__init__.py": "",
    "app/forms/auth_forms.py": """from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class PatientRegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Regexp(r'^\+?1?\d{9,15}$', message="Invalid phone number.")])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters.")])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register as Patient')

class DoctorRegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired()])
    specialization = StringField('Specialization', validators=[DataRequired()])
    registration_number = StringField('Medical Registration Number', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register as Doctor')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send OTP')

class ResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    otp = StringField('OTP', validators=[DataRequired(), Length(min=6, max=6)])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Reset Password')
""",
    "app/repositories/patient_repository.py": """from app.repositories.base_repository import BaseRepository

class PatientRepository(BaseRepository):
    TABLE = "Patients"
""",
    "app/repositories/doctor_repository.py": """from app.repositories.base_repository import BaseRepository

class DoctorRepository(BaseRepository):
    TABLE = "Doctors"
""",
    "app/repositories/audit_repository.py": """from app.repositories.base_repository import BaseRepository
from app.utils import get_utc_now
import uuid

class AuditRepository(BaseRepository):
    TABLE = "AuditLogs"

    def log_action(self, action_type, user_id, resource_id, ip_address="UNKNOWN", user_agent="UNKNOWN", status="Success"):
        item = {
            "LogID": str(uuid.uuid4()),
            "UserID": user_id,
            "ActionType": action_type,
            "ResourceID": resource_id,
            "IPAddress": ip_address,
            "UserAgent": user_agent,
            "Status": status,
            "Timestamp": get_utc_now()
        }
        self.put_item(self.TABLE, item)
""",
    "app/repositories/login_history_repository.py": """from app.repositories.base_repository import BaseRepository
from app.utils import get_utc_now

class LoginHistoryRepository(BaseRepository):
    TABLE = "LoginHistory"

    def log_login(self, user_id, ip_address, user_agent, status):
        item = {
            "UserID": user_id,
            "LoginAt": get_utc_now(),
            "IPAddress": ip_address,
            "UserAgent": user_agent,
            "Status": status
        }
        self.put_item(self.TABLE, item)

    def get_history(self, user_id):
        items = self.query_index(
            table_name=self.TABLE,
            index_name=None, # not a GSI, just query the base table (PK: UserID)
            key_condition_expression="UserID = :uid",
            expression_attribute_values={":uid": user_id}
        )
        # return sorted by time desc
        return sorted(items, key=lambda x: x['LoginAt'], reverse=True)
""",
    "app/services/__init__.py": "",
    "app/services/notification_service.py": """import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.sns = boto3.client('sns', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
        self.topic_arn = os.environ.get('SNS_TOPIC_ARN', None)

    def send_otp(self, phone: str, otp: str) -> bool:
        message = f"Your MedTrack OTP is: {otp}. It is valid for 10 minutes."
        if not self.topic_arn:
            logger.info(f"Simulating SMS to {phone}: {message}")
            return True
        try:
            self.sns.publish(PhoneNumber=phone, Message=message)
            return True
        except ClientError as e:
            logger.error(f"Failed to send OTP via SNS: {e}")
            return False
""",
    "app/services/auth_service.py": """import uuid
import secrets
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.repositories.user_repository import UserRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.login_history_repository import LoginHistoryRepository
from app.services.notification_service import NotificationService
from app.utils import get_utc_now

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.patient_repo = PatientRepository()
        self.doctor_repo = DoctorRepository()
        self.audit_repo = AuditRepository()
        self.login_history_repo = LoginHistoryRepository()
        self.notification_service = NotificationService()

    def register_patient(self, name: str, email: str, phone: str, password: str) -> dict:
        if self.user_repo.get_user_by_email(email):
            raise ValueError("Email already registered.")
        
        user_id = str(uuid.uuid4())
        pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')
        user = self.user_repo.create_user(user_id, email, pwd_hash, 'Patient', phone)
        
        patient = {
            "PatientID": user_id,
            "Email": email,
            "Name": name,
            "IsDeleted": False,
            "CreatedAt": get_utc_now(),
            "UpdatedAt": get_utc_now()
        }
        self.patient_repo.put_item(self.patient_repo.TABLE, patient)
        self.audit_repo.log_action("REGISTER_PATIENT", user_id, "User Registered", status="Success")
        return user

    def register_doctor(self, name: str, email: str, phone: str, spec_id: str, reg_number: str, password: str) -> dict:
        if self.user_repo.get_user_by_email(email):
            raise ValueError("Email already registered.")
        
        user_id = str(uuid.uuid4())
        pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')
        user = self.user_repo.create_user(user_id, email, pwd_hash, 'Doctor', phone)
        
        doctor = {
            "DoctorID": user_id,
            "Email": email,
            "Name": name,
            "SpecializationID": spec_id,
            "RegistrationNumber": reg_number,
            "Status": "Pending",
            "IsDeleted": False,
            "CreatedAt": get_utc_now(),
            "UpdatedAt": get_utc_now()
        }
        self.doctor_repo.put_item(self.doctor_repo.TABLE, doctor)
        self.audit_repo.log_action("REGISTER_DOCTOR", user_id, "Doctor Registered", status="Success")
        return user

    def authenticate(self, email: str, password: str, ip_address: str, user_agent: str) -> dict:
        user = self.user_repo.get_user_by_email(email)
        if not user:
            self.audit_repo.log_action("LOGIN_ATTEMPT", "UNKNOWN", f"Failed login for {email}", ip_address, user_agent, "Failed")
            raise ValueError("Invalid email or password.")
        
        user_id = user['UserID']
        now = datetime.now(timezone.utc)
        
        lockout_until_str = user.get('LockoutUntil')
        if lockout_until_str:
            lockout_until = datetime.fromisoformat(lockout_until_str)
            if now < lockout_until:
                self.audit_repo.log_action("LOGIN_ATTEMPT", user_id, "Account locked", ip_address, user_agent, "Failed")
                raise ValueError("Account locked due to too many failed attempts. Try again later.")

        if not check_password_hash(user['PasswordHash'], password):
            attempts = user.get('FailedLoginAttempts', 0) + 1
            updates = {':attempts': attempts, ':updated': get_utc_now()}
            expr = "SET FailedLoginAttempts = :attempts, UpdatedAt = :updated"
            
            if attempts >= 5:
                lockout = (now + timedelta(minutes=15)).isoformat()
                expr += ", LockoutUntil = :lockout"
                updates[':lockout'] = lockout
            
            self.user_repo.update_item(self.user_repo.TABLE, {'UserID': user_id}, expr, updates)
            self.login_history_repo.log_login(user_id, ip_address, user_agent, "Failed")
            self.audit_repo.log_action("LOGIN_ATTEMPT", user_id, "Invalid password", ip_address, user_agent, "Failed")
            raise ValueError("Invalid email or password.")
        
        # Reset attempts on success. DynamoDB REMOVE is safe even if attribute doesn't exist
        expr = "SET FailedLoginAttempts = :attempts, UpdatedAt = :updated REMOVE LockoutUntil"
        updates = {':attempts': 0, ':updated': get_utc_now()}
        self.user_repo.update_item(self.user_repo.TABLE, {'UserID': user_id}, expr, updates)
        
        self.login_history_repo.log_login(user_id, ip_address, user_agent, "Success")
        self.audit_repo.log_action("LOGIN", user_id, "User logged in", ip_address, user_agent, "Success")
        return user

    def generate_otp(self, email: str) -> None:
        user = self.user_repo.get_user_by_email(email)
        if not user:
            return
        
        otp = str(secrets.randbelow(1000000)).zfill(6)
        expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        
        self.user_repo.update_item(
            self.user_repo.TABLE,
            {'UserID': user['UserID']},
            "SET ResetOTP = :otp, ResetOTPExpiry = :expiry, UpdatedAt = :updated",
            {':otp': generate_password_hash(otp, method='pbkdf2:sha256'), ':expiry': expiry, ':updated': get_utc_now()}
        )
        
        phone = user.get('Phone', '+10000000000')
        self.notification_service.send_otp(phone, otp)
        self.audit_repo.log_action("FORGOT_PASSWORD", user['UserID'], "OTP Generated", status="Success")

    def reset_password(self, email: str, otp: str, new_password: str) -> None:
        user = self.user_repo.get_user_by_email(email)
        if not user:
            raise ValueError("Invalid details.")
        
        stored_otp_hash = user.get('ResetOTP')
        expiry_str = user.get('ResetOTPExpiry')
        
        if not stored_otp_hash or not expiry_str:
            raise ValueError("Invalid or expired OTP.")
        
        expiry = datetime.fromisoformat(expiry_str)
        if datetime.now(timezone.utc) > expiry:
            raise ValueError("OTP has expired.")
            
        if not check_password_hash(stored_otp_hash, otp):
            raise ValueError("Invalid OTP.")
            
        pwd_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        self.user_repo.update_item(
            self.user_repo.TABLE,
            {'UserID': user['UserID']},
            "SET PasswordHash = :pwd, UpdatedAt = :updated REMOVE ResetOTP, ResetOTPExpiry",
            {':pwd': pwd_hash, ':updated': get_utc_now()}
        )
        self.audit_repo.log_action("RESET_PASSWORD", user['UserID'], "Password reset", status="Success")
""",
    "app/blueprints/auth.py": """from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.forms.auth_forms import LoginForm, PatientRegistrationForm, DoctorRegistrationForm, ForgotPasswordForm, ResetPasswordForm
from app.services.auth_service import AuthService
from app.extensions import limiter

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = auth_service.authenticate(
                form.email.data, form.password.data, 
                request.remote_addr or '127.0.0.1', request.user_agent.string or 'unknown'
            )
            session.clear()
            session['user_id'] = user['UserID']
            session['role'] = user['Role']
            if form.remember_me.data:
                session.permanent = True
            flash("Logged in successfully.", "success")
            
            if user['Role'] == 'Admin':
                return redirect(url_for('admin.dashboard'))
            elif user['Role'] == 'Doctor':
                return redirect(url_for('doctor.dashboard'))
            else:
                return redirect(url_for('patient.dashboard'))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register/patient', methods=['GET', 'POST'])
def register_patient():
    form = PatientRegistrationForm()
    if form.validate_on_submit():
        try:
            auth_service.register_patient(form.name.data, form.email.data, form.phone.data, form.password.data)
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template('auth/register_patient.html', form=form)

@auth_bp.route('/register/doctor', methods=['GET', 'POST'])
def register_doctor():
    form = DoctorRegistrationForm()
    if form.validate_on_submit():
        try:
            auth_service.register_doctor(
                form.name.data, form.email.data, form.phone.data, 
                form.specialization.data, form.registration_number.data, form.password.data
            )
            flash("Registration submitted. Wait for admin approval.", "success")
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template('auth/register_doctor.html', form=form)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        auth_service.generate_otp(form.email.data)
        flash("If the email exists, an OTP has been sent.", "info")
        return redirect(url_for('auth.reset_password', email=form.email.data))
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def reset_password():
    form = ResetPasswordForm()
    if request.method == 'GET':
        form.email.data = request.args.get('email', '')
    if form.validate_on_submit():
        try:
            auth_service.reset_password(form.email.data, form.otp.data, form.new_password.data)
            flash("Password reset successfully. Please log in.", "success")
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template('auth/reset_password.html', form=form)

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('public.index'))

@auth_bp.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    from app.repositories.login_history_repository import LoginHistoryRepository
    repo = LoginHistoryRepository()
    logs = repo.get_history(session['user_id'])
    return render_template('auth/login_history.html', logs=logs)
""",
    "app/blueprints/patient.py": """from flask import Blueprint\npatient_bp = Blueprint('patient', __name__)\n@patient_bp.route('/dashboard')\ndef dashboard(): return 'Patient Dashboard'""",
    "app/blueprints/doctor.py": """from flask import Blueprint\ndoctor_bp = Blueprint('doctor', __name__)\n@doctor_bp.route('/dashboard')\ndef dashboard(): return 'Doctor Dashboard'""",
    "app/blueprints/admin.py": """from flask import Blueprint\nadmin_bp = Blueprint('admin', __name__)\n@admin_bp.route('/dashboard')\ndef dashboard(): return 'Admin Dashboard'""",
    "app/templates/auth/login.html": """{% extends "base.html" %}\n{% block content %}\n<h2 class="text-center">Log In</h2>\n<form method="POST" class="w-50 mx-auto">\n{{ form.hidden_tag() }}\n{{ form.email.label }} {{ form.email(class="form-control") }}\n{{ form.password.label }} {{ form.password(class="form-control") }}\n{{ form.remember_me() }} {{ form.remember_me.label }}\n<br><br>\n{{ form.submit(class="btn btn-primary") }}\n<div><a href="{{ url_for('auth.forgot_password') }}">Forgot Password?</a></div>\n</form>\n{% endblock %}""",
    "app/templates/auth/register_patient.html": """{% extends "base.html" %}\n{% block content %}\n<h2 class="text-center">Register as Patient</h2>\n<form method="POST" class="w-50 mx-auto">\n{{ form.hidden_tag() }}\n{% for field in form if field.name != 'csrf_token' and field.name != 'submit' %}\n{{ field.label }} {{ field(class="form-control") }}\n{% for err in field.errors %}<span class="text-danger">{{ err }}</span>{% endfor %}<br>\n{% endfor %}\n{{ form.submit(class="btn btn-primary") }}\n</form>\n{% endblock %}""",
    "app/templates/auth/register_doctor.html": """{% extends "base.html" %}\n{% block content %}\n<h2 class="text-center">Register as Doctor</h2>\n<form method="POST" class="w-50 mx-auto">\n{{ form.hidden_tag() }}\n{% for field in form if field.name != 'csrf_token' and field.name != 'submit' %}\n{{ field.label }} {{ field(class="form-control") }}\n{% for err in field.errors %}<span class="text-danger">{{ err }}</span>{% endfor %}<br>\n{% endfor %}\n{{ form.submit(class="btn btn-primary") }}\n</form>\n{% endblock %}""",
    "app/templates/auth/forgot_password.html": """{% extends "base.html" %}\n{% block content %}\n<h2 class="text-center">Forgot Password</h2>\n<form method="POST" class="w-50 mx-auto">\n{{ form.hidden_tag() }}\n{{ form.email.label }} {{ form.email(class="form-control") }}\n<br>\n{{ form.submit(class="btn btn-primary") }}\n</form>\n{% endblock %}""",
    "app/templates/auth/reset_password.html": """{% extends "base.html" %}\n{% block content %}\n<h2 class="text-center">Reset Password</h2>\n<form method="POST" class="w-50 mx-auto">\n{{ form.hidden_tag() }}\n{{ form.email.label }} {{ form.email(class="form-control") }}\n{{ form.otp.label }} {{ form.otp(class="form-control") }}\n{{ form.new_password.label }} {{ form.new_password(class="form-control") }}\n{{ form.confirm_password.label }} {{ form.confirm_password(class="form-control") }}\n<br>\n{{ form.submit(class="btn btn-primary") }}\n</form>\n{% endblock %}""",
    "app/templates/auth/login_history.html": """{% extends "base.html" %}\n{% block content %}\n<h2>Login History</h2>\n<table class="table table-striped">\n<tr><th>Date</th><th>IP Address</th><th>User Agent</th><th>Status</th></tr>\n{% for log in logs %}\n<tr><td>{{ log.LoginAt }}</td><td>{{ log.IPAddress }}</td><td>{{ log.UserAgent }}</td><td>{{ log.Status }}</td></tr>\n{% endfor %}\n</table>\n{% endblock %}""",
    "tests/conftest.py": """import os
import pytest
from moto import mock_aws
from scripts.create_tables import create_tables
from app import create_app
from app.config import TestConfig

@pytest.fixture(autouse=True)
def aws_credentials():
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['DYNAMODB_PREFIX'] = 'TestTrack-'

@pytest.fixture
def dynamodb_setup(aws_credentials):
    with mock_aws():
        create_tables()
        yield

@pytest.fixture
def app(dynamodb_setup):
    app = create_app(TestConfig)
    app.config['SECRET_KEY'] = 'test-secret'
    yield app

@pytest.fixture
def client(app):
    return app.test_client()
""",
    "tests/test_auth.py": """import pytest
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository

def test_patient_registration(client, dynamodb_setup):
    res = client.post('/auth/register/patient', data={
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '1234567890',
        'password': 'Password123!',
        'confirm_password': 'Password123!',
        'submit': True
    }, follow_redirects=True)
    assert b'Registration successful' in res.data
    
    repo = UserRepository()
    user = repo.get_user_by_email('john@example.com')
    assert user is not None
    assert user['Role'] == 'Patient'

def test_login_and_lockout(client, dynamodb_setup):
    svc = AuthService()
    svc.register_patient("Test", "test@test.com", "1234567890", "Pass123!")
    
    for _ in range(5):
        res = client.post('/auth/login', data={'email': 'test@test.com', 'password': 'wrong', 'submit': True}, follow_redirects=True)
        assert (b'Invalid email or password' in res.data) or (b'Account locked' in res.data)
        
    res = client.post('/auth/login', data={'email': 'test@test.com', 'password': 'wrong', 'submit': True}, follow_redirects=True)
    assert b'Account locked due to too many failed attempts' in res.data
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
