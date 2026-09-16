from flask import Blueprint, render_template, redirect, url_for, flash
from app.utils import login_required, role_required
from app.services.admin_service import AdminService
from app.forms.admin_forms import SpecializationForm

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
@role_required('Admin')
def before_request():
    pass

@admin_bp.route('/dashboard')
def dashboard():
    svc = AdminService()
    stats = svc.get_dashboard_stats()
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/doctors/pending')
def doctors_pending():
    svc = AdminService()
    docs = svc.get_pending_doctors()
    return render_template('admin/doctors_pending.html', doctors=docs)

@admin_bp.route('/doctors/<id>/approve', methods=['POST'])
def approve_doctor(id):
    svc = AdminService()
    svc.approve_doctor(id)
    flash('Doctor approved successfully.', 'success')
    return redirect(url_for('admin.doctors_pending'))

@admin_bp.route('/doctors/<id>/reject', methods=['POST'])
def reject_doctor(id):
    svc = AdminService()
    svc.reject_doctor(id)
    flash('Doctor rejected.', 'info')
    return redirect(url_for('admin.doctors_pending'))

@admin_bp.route('/users')
def users():
    svc = AdminService()
    users = svc.get_all_users()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<id>/ban', methods=['POST'])
def ban_user(id):
    svc = AdminService()
    svc.ban_user(id)
    flash('User account has been suspended.', 'warning')
    return redirect(url_for('admin.users'))

@admin_bp.route('/specializations', methods=['GET', 'POST'])
def specializations():
    svc = AdminService()
    form = SpecializationForm()
    if form.validate_on_submit():
        svc.add_specialization(form.name.data, form.description.data)
        flash('Specialization added.', 'success')
        return redirect(url_for('admin.specializations'))
    specs = svc.get_specializations()
    return render_template('admin/specializations.html', form=form, specializations=specs)

@admin_bp.route('/tickets')
def tickets():
    svc = AdminService()
    t = svc.get_support_tickets()
    return render_template('admin/tickets.html', tickets=t)

@admin_bp.route('/tickets/<id>/resolve', methods=['POST'])
def resolve_ticket(id):
    svc = AdminService()
    svc.resolve_ticket(id)
    flash('Ticket resolved.', 'success')
    return redirect(url_for('admin.tickets'))

@admin_bp.route('/audit')
def audit():
    svc = AdminService()
    logs = svc.get_audit_logs()
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/content', methods=['GET', 'POST'])
def content():
    return "Content Editor"
