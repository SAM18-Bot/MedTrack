import os

files = {
    "app/forms/admin_forms.py": """from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

class SpecializationForm(FlaskForm):
    name = StringField('Specialization Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Add Specialization')
""",
    "app/repositories/specialization_repository.py": """from app.repositories.base_repository import BaseRepository

class SpecializationRepository(BaseRepository):
    TABLE = "Specializations"
""",
    "app/services/admin_service.py": """import uuid
from app.repositories.user_repository import UserRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.support_ticket_repository import SupportTicketRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.specialization_repository import SpecializationRepository
from app.services.notification_service import NotificationService
from app.utils import get_utc_now

class AdminService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.doc_repo = DoctorRepository()
        self.ticket_repo = SupportTicketRepository()
        self.audit_repo = AuditRepository()
        self.spec_repo = SpecializationRepository()
        self.notification = NotificationService()

    def _scan(self, repo):
        table = repo.dynamodb.Table(f"{repo.table_prefix}{repo.TABLE}")
        return table.scan().get('Items', [])

    def get_dashboard_stats(self):
        users = self._scan(self.user_repo)
        pending_docs = self.get_pending_doctors()
        tickets = self._scan(self.ticket_repo)
        open_tickets = [t for t in tickets if t.get('Status') == 'Open']
        
        return {
            "total_users": len(users),
            "pending_doctors": len(pending_docs),
            "open_tickets": len(open_tickets)
        }

    def get_pending_doctors(self):
        return self.doc_repo.query_index(
            self.doc_repo.TABLE,
            "status-index",
            "#st = :status",
            {":status": "Pending"},
            expression_attribute_names={"#st": "Status"}
        )

    def approve_doctor(self, doc_id):
        self.doc_repo.update_item(
            self.doc_repo.TABLE,
            {"DoctorID": doc_id},
            "SET #st = :status, UpdatedAt = :u",
            {":status": "Approved", ":u": get_utc_now()},
            {"#st": "Status"}
        )
        self.notification.notify_admin("Doctor Approved", f"Doctor {doc_id} was approved.")

    def reject_doctor(self, doc_id):
        self.doc_repo.update_item(
            self.doc_repo.TABLE,
            {"DoctorID": doc_id},
            "SET #st = :status, UpdatedAt = :u",
            {":status": "Rejected", ":u": get_utc_now()},
            {"#st": "Status"}
        )

    def get_all_users(self):
        return self._scan(self.user_repo)

    def ban_user(self, user_id):
        self.user_repo.update_item(
            self.user_repo.TABLE,
            {"UserID": user_id},
            "SET IsDeleted = :d, UpdatedAt = :u",
            {":d": True, ":u": get_utc_now()}
        )

    def get_specializations(self):
        return self._scan(self.spec_repo)

    def add_specialization(self, name, description):
        spec_id = str(uuid.uuid4())
        self.spec_repo.put_item(self.spec_repo.TABLE, {
            "SpecializationID": spec_id,
            "Name": name,
            "Description": description,
            "IsDeleted": False,
            "CreatedAt": get_utc_now()
        })

    def get_support_tickets(self):
        return self._scan(self.ticket_repo)

    def resolve_ticket(self, ticket_id):
        self.ticket_repo.update_item(
            self.ticket_repo.TABLE,
            {"TicketID": ticket_id},
            "SET #st = :status, UpdatedAt = :u",
            {":status": "Resolved", ":u": get_utc_now()},
            {"#st": "Status"}
        )

    def get_audit_logs(self):
        logs = self._scan(self.audit_repo)
        return sorted(logs, key=lambda x: x.get('Timestamp', ''), reverse=True)
""",
    "app/blueprints/admin.py": """from flask import Blueprint, render_template, redirect, url_for, flash
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
""",
    "app/templates/admin/dashboard.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Admin Dashboard</h1>
<div class="row">
    <div class="col-md-4"><div class="card p-3 bg-primary text-white border-0 mb-3"><h5>Total Users</h5><h2>{{ stats.total_users }}</h2></div></div>
    <div class="col-md-4"><div class="card p-3 bg-warning text-dark border-0 mb-3"><h5>Pending Doctors</h5><h2>{{ stats.pending_doctors }}</h2></div></div>
    <div class="col-md-4"><div class="card p-3 bg-danger text-white border-0 mb-3"><h5>Open Support Tickets</h5><h2>{{ stats.open_tickets }}</h2></div></div>
</div>
<div class="mt-4">
    <h3>Quick Links</h3>
    <a href="{{ url_for('admin.doctors_pending') }}" class="btn btn-outline-primary">Review Doctors</a>
    <a href="{{ url_for('admin.users') }}" class="btn btn-outline-primary">Manage Users</a>
    <a href="{{ url_for('admin.tickets') }}" class="btn btn-outline-primary">Support Desk</a>
    <a href="{{ url_for('admin.specializations') }}" class="btn btn-outline-primary">Specializations</a>
    <a href="{{ url_for('admin.audit') }}" class="btn btn-outline-primary">Audit Logs</a>
</div>
{% endblock %}""",
    "app/templates/admin/doctors_pending.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Pending Doctor Verifications</h1>
<table class="table table-striped align-middle">
    <tr><th>Doctor Name</th><th>Email</th><th>Specialization</th><th>Reg No.</th><th>Actions</th></tr>
    {% for doc in doctors %}
    <tr>
        <td>{{ doc.Name }}</td><td>{{ doc.Email }}</td><td>{{ doc.SpecializationID }}</td><td>{{ doc.RegistrationNumber }}</td>
        <td>
            <form method="POST" action="{{ url_for('admin.approve_doctor', id=doc.DoctorID) }}" class="d-inline">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <button class="btn btn-sm btn-success">Approve</button>
            </form>
            <form method="POST" action="{{ url_for('admin.reject_doctor', id=doc.DoctorID) }}" class="d-inline">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <button class="btn btn-sm btn-danger">Reject</button>
            </form>
        </td>
    </tr>
    {% else %}
    <tr><td colspan="5">No pending doctors.</td></tr>
    {% endfor %}
</table>
{% endblock %}""",
    "app/templates/admin/users.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">User Management</h1>
<table class="table table-striped align-middle">
    <tr><th>User ID</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr>
    {% for u in users %}
    <tr>
        <td>{{ u.UserID[:8] }}...</td><td>{{ u.Email }}</td><td>{{ u.Role }}</td>
        <td>
            {% if u.IsDeleted %}<span class="badge bg-danger">Suspended</span>
            {% else %}<span class="badge bg-success">Active</span>{% endif %}
        </td>
        <td>
            {% if not u.IsDeleted and u.Role != 'Admin' %}
            <form method="POST" action="{{ url_for('admin.ban_user', id=u.UserID) }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <button class="btn btn-sm btn-warning">Suspend</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% endfor %}
</table>
{% endblock %}""",
    "app/templates/admin/specializations.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Manage Specializations</h1>
<form method="POST" class="mb-5 card p-3 shadow-sm border-0 w-50">
    {{ form.hidden_tag() }}
    {{ form.name.label }} {{ form.name(class="form-control mb-2") }}
    {{ form.description.label }} {{ form.description(class="form-control mb-3") }}
    {{ form.submit(class="btn btn-primary") }}
</form>
<table class="table table-striped">
    <tr><th>Specialization</th><th>Description</th></tr>
    {% for s in specializations %}
    <tr><td>{{ s.Name }}</td><td>{{ s.Description }}</td></tr>
    {% endfor %}
</table>
{% endblock %}""",
    "app/templates/admin/tickets.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Support Desk</h1>
<table class="table table-striped">
    <tr><th>Subject</th><th>Priority</th><th>Status</th><th>Description</th><th>Actions</th></tr>
    {% for t in tickets %}
    <tr>
        <td>{{ t.Subject }}</td><td>{{ t.Priority }}</td>
        <td>
            {% if t.Status == 'Resolved' %}<span class="badge bg-success">Resolved</span>
            {% else %}<span class="badge bg-danger">Open</span>{% endif %}
        </td>
        <td>{{ t.Description[:50] }}...</td>
        <td>
            {% if t.Status != 'Resolved' %}
            <form method="POST" action="{{ url_for('admin.resolve_ticket', id=t.TicketID) }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <button class="btn btn-sm btn-success">Resolve</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% endfor %}
</table>
{% endblock %}""",
    "app/templates/admin/audit_logs.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">System Audit Logs</h1>
<table class="table table-sm table-striped" style="font-size: 0.9rem;">
    <tr><th>Timestamp</th><th>Action</th><th>User ID</th><th>Status</th><th>IP Address</th></tr>
    {% for l in logs %}
    <tr>
        <td>{{ l.Timestamp }}</td><td>{{ l.ActionType }}</td>
        <td>{{ l.UserID[:8] }}</td><td>{{ l.Status }}</td><td>{{ l.IPAddress }}</td>
    </tr>
    {% endfor %}
</table>
{% endblock %}""",
    "tests/test_admin.py": """import pytest
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService

def test_admin_dashboard_stats(dynamodb_setup):
    svc = AdminService()
    stats = svc.get_dashboard_stats()
    assert 'total_users' in stats
    assert stats['pending_doctors'] == 0

def test_approve_doctor(dynamodb_setup):
    auth = AuthService()
    auth.register_doctor("Doc", "doc2@doc.com", "123", "Spec", "Reg", "Pass123!")
    
    svc = AdminService()
    pending = svc.get_pending_doctors()
    assert len(pending) == 1
    
    doc_id = pending[0]['DoctorID']
    svc.approve_doctor(doc_id)
    
    pending_after = svc.get_pending_doctors()
    assert len(pending_after) == 0

def test_ban_user_prevents_login(dynamodb_setup):
    auth = AuthService()
    user = auth.register_patient("BadPat", "bad@pat.com", "123", "Pass123!")
    
    svc = AdminService()
    svc.ban_user(user['UserID'])
    
    with pytest.raises(ValueError, match="suspended"):
        auth.authenticate("bad@pat.com", "Pass123!", "127.0.0.1", "test")
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# Patch auth_service.py to enforce IsDeleted check
with open('app/services/auth_service.py', 'r') as f:
    auth_code = f.read()

if "suspended" not in auth_code:
    auth_code = auth_code.replace(
        "user_id = user['UserID']",
        "if user.get('IsDeleted'):\\n            raise ValueError('This account has been suspended.')\\n        user_id = user['UserID']"
    )
    with open('app/services/auth_service.py', 'w') as f:
        f.write(auth_code)
