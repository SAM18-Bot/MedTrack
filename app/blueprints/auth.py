from flask import Blueprint, render_template, redirect, url_for, flash, request, session
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
            csrf_tok = session.get('csrf_token')
            session.clear()
            if csrf_tok:
                session['csrf_token'] = csrf_tok
            session['user_id'] = user['UserID']
            session['role'] = user['Role']
            if form.remember_me.data:
                session.permanent = True
            flash("Logged in successfully.", "success")
            
            next_page = request.args.get('next')
            from urllib.parse import urlparse, urljoin
            if next_page:
                ref_url = urlparse(request.host_url)
                test_url = urlparse(urljoin(request.host_url, next_page))
                if test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc:
                    return redirect(next_page)
                    
            if user['Role'] == 'Admin':
                return redirect(url_for('admin.dashboard'))
            elif user['Role'] == 'Doctor':
                return redirect(url_for('doctor.dashboard'))
            else:
                return redirect(url_for('patient.dashboard'))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template('auth/login.html', form=form)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'patient').strip().lower()
        specialization = request.form.get('specialization', 'General Medicine').strip()
        phone = request.form.get('phone', '').strip() or '+1000000000'
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash("All required fields must be filled.", "danger")
            return render_template('auth/signup.html', name=name, email=email, role=role, specialization=specialization, phone=phone)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/signup.html', name=name, email=email, role=role, specialization=specialization, phone=phone)

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template('auth/signup.html', name=name, email=email, role=role, specialization=specialization, phone=phone)

        try:
            if role == 'doctor':
                auth_service.register_doctor(name, email, phone, specialization, 'REG-' + email.split('@')[0], password)
                flash("Doctor registration submitted! Your account is pending admin approval.", "success")
            else:
                auth_service.register_patient(name, email, phone, password)
                flash("Patient registration successful! Please log in.", "success")
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), "danger")
            return render_template('auth/signup.html', name=name, email=email, role=role, specialization=specialization, phone=phone)

    return render_template('auth/signup.html')

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
@limiter.limit("5 per minute")
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        auth_service.generate_otp(form.email.data)
        flash("If the email exists, an OTP has been sent.", "info")
        session['reset_email'] = form.email.data
        return redirect(url_for('auth.reset_password'))
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def reset_password():
    form = ResetPasswordForm()
    if request.method == 'GET':
        form.email.data = session.pop('reset_email', '')
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
    records = repo.get_history(session['user_id'])
    return render_template('auth/login_history.html', history=records)
