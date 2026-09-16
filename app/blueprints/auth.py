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
