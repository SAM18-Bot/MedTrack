import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from app.forms.support_forms import ContactUsForm
from app.services.support_service import SupportService

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    return render_template('public/landing.html')

@public_bp.route('/dashboard')
def dashboard():
    role = session.get('role')
    if role == 'Admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'Doctor':
        return redirect(url_for('doctor.dashboard'))
    elif role == 'Patient':
        return redirect(url_for('patient.dashboard'))
    return redirect(url_for('auth.login'))

@public_bp.route('/login')
def login_alias():
    return redirect(url_for('auth.login', **request.args))

@public_bp.route('/signup')
def signup_alias():
    return redirect(url_for('auth.signup', **request.args))

@public_bp.route('/logout')
def logout_alias():
    return redirect(url_for('auth.logout'))

@public_bp.route('/appointments')
def appointments_alias():
    role = session.get('role')
    if role == 'Doctor':
        return redirect(url_for('doctor.queue'))
    elif role == 'Patient':
        return redirect(url_for('patient.appointments'))
    elif role == 'Admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))

@public_bp.route('/book-appointment')
def book_appointment_alias():
    return redirect(url_for('patient.doctors'))

@public_bp.route('/profile')
def profile_alias():
    role = session.get('role')
    if role == 'Doctor':
        return redirect(url_for('doctor.profile'))
    elif role == 'Patient':
        return redirect(url_for('patient.profile'))
    return redirect(url_for('auth.login'))

@public_bp.route('/search')
def search_alias():
    role = session.get('role')
    if role == 'Doctor':
        return redirect(url_for('doctor.queue'))
    elif role == 'Admin':
        return redirect(url_for('admin.users'))
    return redirect(url_for('patient.doctors', **request.args))

@public_bp.route('/notifications')
def notifications_alias():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    from app.repositories.notification_repository import NotificationRepository
    notifs = NotificationRepository().get_user_notifications(session['user_id'])
    return render_template('patient/notifications.html', notifications=notifs)

@public_bp.route('/notifications/<notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    from app.repositories.notification_repository import NotificationRepository
    NotificationRepository().mark_as_read(notif_id)
    return redirect(url_for('public.notifications_alias'))

@public_bp.route('/auth/google')
def google_auth():
    flash("Google login is not configured for this demo environment. Use the manual login / signup forms below.", "warning")
    return redirect(url_for('auth.login'))

@public_bp.route('/about')
def about(): return render_template('public/about.html')
@public_bp.route('/services')
def services(): return render_template('public/services.html')
@public_bp.route('/how-it-works')
def how_it_works(): return render_template('public/how_it_works.html')
@public_bp.route('/for-doctors')
def for_doctors(): return render_template('public/for_doctors.html')
@public_bp.route('/faq')
def faq(): return render_template('public/faq.html')

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactUsForm()
    if form.validate_on_submit():
        svc = SupportService()
        msg = f"From: {form.name.data} ({form.email.data}) - {form.message.data}"
        svc.raise_ticket(f'GUEST#{uuid.uuid4()}', 'Other', 'Medium', form.subject.data, msg, is_guest=True)
        flash('Your message has been sent. We will get back to you shortly.', 'success')
        return redirect(url_for('public.contact'))
    return render_template('public/contact.html', form=form)

@public_bp.route('/legal/<page>')
def legal(page):
    valid_pages = ['terms', 'privacy', 'cookies', 'disclaimer', 'refund', 'data-protection', 'accessibility']
    if page not in valid_pages:
        return render_template('errors/404.html'), 404
    return render_template(f'public/legal_{page}.html')

@public_bp.route('/sitemap')
def sitemap(): return render_template('public/sitemap.html')
