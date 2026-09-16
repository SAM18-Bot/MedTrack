import os

files = {
    "app/forms/patient_forms.py": """from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Optional

class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    dob = StringField('Date of Birth (YYYY-MM-DD)', validators=[Optional()])
    gender = SelectField('Gender', choices=[('', 'Select'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[Optional()])
    blood_group = SelectField('Blood Group', choices=[('', 'Select'), ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')], validators=[Optional()])
    height = FloatField('Height (cm)', validators=[Optional()])
    weight = FloatField('Weight (kg)', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    emergency_contact = StringField('Emergency Contact', validators=[Optional()])
    insurance_provider = StringField('Insurance Provider', validators=[Optional()])
    policy_number = StringField('Policy Number', validators=[Optional()])
    allergies = StringField('Allergies (comma-separated)', validators=[Optional()])
    chronic_conditions = StringField('Chronic Conditions (comma-separated)', validators=[Optional()])
    submit = SubmitField('Update Profile')

class DoctorSearchForm(FlaskForm):
    specialization = StringField('Specialization', validators=[Optional()])
    city = StringField('City', validators=[Optional()])
    max_fee = FloatField('Max Fee', validators=[Optional()])
    submit = SubmitField('Search')

class BookingForm(FlaskForm):
    date = StringField('Date (YYYY-MM-DD)', validators=[DataRequired()])
    time = StringField('Time (HH:MM)', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Confirm Booking')

class VitalsForm(FlaskForm):
    blood_pressure = StringField('Blood Pressure (e.g. 120/80)', validators=[DataRequired()])
    sugar_level = FloatField('Sugar Level (mg/dL)', validators=[DataRequired()])
    weight = FloatField('Weight (kg)', validators=[DataRequired()])
    heart_rate = IntegerField('Heart Rate (bpm)', validators=[DataRequired()])
    submit = SubmitField('Log Vitals')
""",
    "app/repositories/appointment_repository.py": """from app.repositories.base_repository import BaseRepository
from botocore.exceptions import ClientError
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class AppointmentRepository(BaseRepository):
    TABLE = "Appointments"

    def create_appointment_with_lock(self, appointment):
        doc_id = appointment['DoctorID']
        sched = appointment['ScheduledAt']
        lock_id = f"SLOT#{doc_id}#{sched}"
        
        try:
            self.dynamodb.meta.client.transact_write_items(
                TransactItems=[
                    {
                        'Put': {
                            'TableName': f"{self.table_prefix}{self.TABLE}",
                            'Item': {
                                'AppointmentID': lock_id,
                                'Type': 'SlotLock',
                                'IsDeleted': False
                            },
                            'ConditionExpression': 'attribute_not_exists(AppointmentID)'
                        }
                    },
                    {
                        'Put': {
                            'TableName': f"{self.table_prefix}{self.TABLE}",
                            'Item': appointment
                        }
                    }
                ]
            )
            return appointment
        except ClientError as e:
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                raise ValueError("This slot has already been booked. Please choose another time.")
            logger.error(f"Failed to book appointment: {e}")
            raise ValueError("Failed to book appointment.")

    def get_patient_appointments(self, patient_id):
        return self.query_index(
            self.TABLE,
            "patient-index",
            "PatientID = :pid",
            {":pid": patient_id}
        )
""",
    "app/repositories/vitals_repository.py": """from app.repositories.base_repository import BaseRepository

class VitalsRepository(BaseRepository):
    TABLE = "Vitals"

    def get_vitals(self, patient_id):
        items = self.query_index(
            table_name=self.TABLE,
            index_name=None,
            key_condition_expression="PatientID = :pid",
            expression_attribute_values={":pid": patient_id}
        )
        return sorted(items, key=lambda x: x['RecordedAt'])
""",
    "app/services/patient_service.py": """import uuid
from decimal import Decimal
from app.repositories.patient_repository import PatientRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.vitals_repository import VitalsRepository
from app.services.notification_service import NotificationService
from app.utils import get_utc_now

class PatientService:
    def __init__(self):
        self.patient_repo = PatientRepository()
        self.doctor_repo = DoctorRepository()
        self.appointment_repo = AppointmentRepository()
        self.vitals_repo = VitalsRepository()
        self.notification = NotificationService()

    def get_profile(self, patient_id):
        return self.patient_repo.get_item(self.patient_repo.TABLE, {"PatientID": patient_id})

    def update_profile(self, patient_id, data):
        # Convert float to Decimal
        for k, v in data.items():
            if isinstance(v, float):
                data[k] = Decimal(str(v))
        
        expr = "SET "
        vals = {":updated": get_utc_now()}
        expr_parts = ["UpdatedAt = :updated"]
        
        for k, v in data.items():
            if v is not None and v != '':
                expr_parts.append(f"{k} = :{k}")
                vals[f":{k}"] = v
        
        expr += ", ".join(expr_parts)
        self.patient_repo.update_item(self.patient_repo.TABLE, {"PatientID": patient_id}, expr, vals)

    def search_doctors(self, spec=None, city=None, max_fee=None):
        items = self.doctor_repo.query_index(
            self.doctor_repo.TABLE,
            "status-index",
            "#st = :status",
            {":status": "Approved"},
            expression_attribute_names={"#st": "Status"}
        )
        results = []
        for doc in items:
            if spec and spec.lower() not in doc.get('SpecializationID', '').lower(): continue
            if city and city.lower() not in doc.get('ClinicAddress', '').lower(): continue
            if max_fee and float(doc.get('ConsultationFee', 0)) > float(max_fee): continue
            results.append(doc)
        return results

    def get_doctor(self, doc_id):
        return self.doctor_repo.get_item(self.doctor_repo.TABLE, {"DoctorID": doc_id})

    def book_appointment(self, patient_id, doc_id, date_str, time_str, notes):
        dt_str = f"{date_str}T{time_str}:00Z"
        appt = {
            "AppointmentID": str(uuid.uuid4()),
            "PatientID": patient_id,
            "DoctorID": doc_id,
            "ScheduledAt": dt_str,
            "Notes": notes,
            "Status": "Pending",
            "IsDeleted": False,
            "CreatedAt": get_utc_now(),
            "UpdatedAt": get_utc_now()
        }
        # Conditional write to prevent double-booking
        self.appointment_repo.create_appointment_with_lock(appt)
        
        # Notify
        self.notification.notify_admin("New Appointment", f"Appointment {appt['AppointmentID']} booked.")
        return appt

    def cancel_appointment(self, appt_id):
        self.appointment_repo.update_item(
            self.appointment_repo.TABLE,
            {"AppointmentID": appt_id},
            "SET #st = :status, UpdatedAt = :updated",
            {":status": "Cancelled", ":updated": get_utc_now()},
            expression_attribute_names={"#st": "Status"}
        )

    def get_appointments(self, patient_id):
        return self.appointment_repo.get_patient_appointments(patient_id)

    def log_vitals(self, patient_id, bp, sugar, weight, hr):
        item = {
            "PatientID": patient_id,
            "RecordedAt": get_utc_now(),
            "BloodPressure": bp,
            "SugarLevel": Decimal(str(sugar)),
            "Weight": Decimal(str(weight)),
            "HeartRate": Decimal(str(hr)),
            "IsDeleted": False
        }
        self.vitals_repo.put_item(self.vitals_repo.TABLE, item)

    def get_vitals(self, patient_id):
        return self.vitals_repo.get_vitals(patient_id)
""",
    "app/blueprints/patient.py": """import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.utils import login_required, role_required, DecimalEncoder
from app.forms.patient_forms import ProfileForm, DoctorSearchForm, BookingForm, VitalsForm
from app.services.patient_service import PatientService

patient_bp = Blueprint('patient', __name__)

@patient_bp.before_request
@login_required
@role_required('Patient')
def before_request():
    pass

@patient_bp.route('/dashboard')
def dashboard():
    svc = PatientService()
    appts = svc.get_appointments(session['user_id'])
    upcoming = [a for a in appts if a['Status'] in ['Pending', 'Confirmed']]
    return render_template('patient/dashboard.html', upcoming=upcoming)

@patient_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    svc = PatientService()
    form = ProfileForm()
    if request.method == 'GET':
        p = svc.get_profile(session['user_id'])
        if p:
            form.name.data = p.get('Name')
            form.dob.data = p.get('DOB')
            form.gender.data = p.get('Gender')
            form.blood_group.data = p.get('BloodGroup')
            form.height.data = float(p.get('Height', 0)) if p.get('Height') else None
            form.weight.data = float(p.get('Weight', 0)) if p.get('Weight') else None
            form.address.data = p.get('Address')
            form.allergies.data = p.get('Allergies')
            form.chronic_conditions.data = p.get('ChronicConditions')
    
    if form.validate_on_submit():
        data = {
            'Name': form.name.data,
            'DOB': form.dob.data,
            'Gender': form.gender.data,
            'BloodGroup': form.blood_group.data,
            'Height': form.height.data,
            'Weight': form.weight.data,
            'Address': form.address.data,
            'Allergies': form.allergies.data,
            'ChronicConditions': form.chronic_conditions.data
        }
        svc.update_profile(session['user_id'], data)
        flash('Profile updated.', 'success')
        return redirect(url_for('patient.profile'))
    return render_template('patient/profile.html', form=form)

@patient_bp.route('/doctors', methods=['GET', 'POST'])
def doctors():
    form = DoctorSearchForm()
    svc = PatientService()
    results = []
    if form.validate_on_submit():
        results = svc.search_doctors(form.specialization.data, form.city.data, form.max_fee.data)
    else:
        results = svc.search_doctors()
    return render_template('patient/doctors.html', form=form, doctors=results)

@patient_bp.route('/doctors/<id>', methods=['GET', 'POST'])
def doctor_detail(id):
    svc = PatientService()
    doc = svc.get_doctor(id)
    if not doc:
        return "Not found", 404
        
    form = BookingForm()
    if form.validate_on_submit():
        try:
            svc.book_appointment(session['user_id'], id, form.date.data, form.time.data, form.notes.data)
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('patient.appointments'))
        except ValueError as e:
            flash(str(e), 'danger')
            
    return render_template('patient/doctor_detail.html', doctor=doc, form=form)

@patient_bp.route('/appointments')
def appointments():
    svc = PatientService()
    appts = svc.get_appointments(session['user_id'])
    return render_template('patient/appointments.html', appointments=appts)

@patient_bp.route('/appointments/<id>/cancel', methods=['POST'])
def cancel_appointment(id):
    svc = PatientService()
    svc.cancel_appointment(id)
    flash('Appointment cancelled.', 'info')
    return redirect(url_for('patient.appointments'))

@patient_bp.route('/vitals', methods=['GET', 'POST'])
def vitals():
    svc = PatientService()
    form = VitalsForm()
    if form.validate_on_submit():
        svc.log_vitals(session['user_id'], form.blood_pressure.data, form.sugar_level.data, form.weight.data, form.heart_rate.data)
        flash('Vitals logged.', 'success')
        return redirect(url_for('patient.vitals'))
        
    v_data = svc.get_vitals(session['user_id'])
    v_json = json.dumps(v_data, cls=DecimalEncoder)
    return render_template('patient/vitals.html', form=form, vitals=v_data, vitals_json=v_json)

@patient_bp.route('/records')
def records(): return render_template('patient/records.html')

@patient_bp.route('/invoices')
def invoices(): return render_template('patient/invoices.html')

@patient_bp.route('/documents', methods=['GET', 'POST'])
def documents(): return render_template('patient/documents.html')
""",
    "app/templates/patient/dashboard.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Patient Dashboard</h1>
<div class="row">
    <div class="col-md-4"><div class="card p-3 shadow-sm mb-3 border-0 bg-primary text-white"><h5>Upcoming Appointments</h5><h2>{{ upcoming|length }}</h2></div></div>
    <div class="col-md-4"><div class="card p-3 shadow-sm mb-3 border-0 bg-info text-white"><h5>Recent Prescriptions</h5><h2>0</h2></div></div>
    <div class="col-md-4"><div class="card p-3 shadow-sm mb-3 border-0 bg-secondary text-white"><h5>Unread Notifications</h5><h2>0</h2></div></div>
</div>
<div class="mt-4">
    <h3>Quick Actions</h3>
    <a href="{{ url_for('patient.doctors') }}" class="btn btn-outline-primary">Find a Doctor</a>
    <a href="{{ url_for('patient.vitals') }}" class="btn btn-outline-primary">Log Vitals</a>
    <a href="{{ url_for('patient.profile') }}" class="btn btn-outline-primary">My Profile</a>
</div>
{% endblock %}""",
    "app/templates/patient/profile.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">My Profile</h1>
<form method="POST" class="w-75">
    {{ form.hidden_tag() }}
    <div class="row">
        <div class="col-md-6 mb-3">{{ form.name.label }} {{ form.name(class="form-control") }}</div>
        <div class="col-md-6 mb-3">{{ form.dob.label }} {{ form.dob(class="form-control") }}</div>
        <div class="col-md-6 mb-3">{{ form.gender.label }} {{ form.gender(class="form-control") }}</div>
        <div class="col-md-6 mb-3">{{ form.blood_group.label }} {{ form.blood_group(class="form-control") }}</div>
        <div class="col-md-6 mb-3">{{ form.height.label }} {{ form.height(class="form-control") }}</div>
        <div class="col-md-6 mb-3">{{ form.weight.label }} {{ form.weight(class="form-control") }}</div>
        <div class="col-md-12 mb-3">{{ form.address.label }} {{ form.address(class="form-control") }}</div>
        <div class="col-md-12 mb-3">{{ form.allergies.label }} {{ form.allergies(class="form-control") }}</div>
        <div class="col-md-12 mb-3">{{ form.chronic_conditions.label }} {{ form.chronic_conditions(class="form-control") }}</div>
    </div>
    {{ form.submit(class="btn btn-primary") }}
</form>
{% endblock %}""",
    "app/templates/patient/doctors.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Search Doctors</h1>
<form method="POST" class="mb-4 d-flex gap-2 align-items-end">
    {{ form.hidden_tag() }}
    <div>{{ form.specialization.label }} {{ form.specialization(class="form-control") }}</div>
    <div>{{ form.city.label }} {{ form.city(class="form-control") }}</div>
    <div>{{ form.max_fee.label }} {{ form.max_fee(class="form-control") }}</div>
    <div>{{ form.submit(class="btn btn-primary") }}</div>
</form>
<div class="list-group">
    {% for doc in doctors %}
    <a href="{{ url_for('patient.doctor_detail', id=doc.DoctorID) }}" class="list-group-item list-group-item-action">
        <h5 class="mb-1">{{ doc.Name }} - {{ doc.SpecializationID }}</h5>
        <p class="mb-1">Fee: ${{ doc.ConsultationFee }} | Experience: {{ doc.ExperienceYears }} years</p>
    </a>
    {% else %}
    <p>No doctors found.</p>
    {% endendfor %}
</div>
{% endblock %}""",
    "app/templates/patient/doctor_detail.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-2">{{ doctor.Name }}</h1>
<p class="text-muted">{{ doctor.SpecializationID }} | {{ doctor.ExperienceYears }} Years Experience</p>
<p>{{ doctor.Bio }}</p>
<hr>
<h3>Book Appointment</h3>
<form method="POST" class="w-50">
    {{ form.hidden_tag() }}
    {{ form.date.label }} {{ form.date(class="form-control mb-2", placeholder="YYYY-MM-DD") }}
    {{ form.time.label }} {{ form.time(class="form-control mb-2", placeholder="HH:MM") }}
    {{ form.notes.label }} {{ form.notes(class="form-control mb-2") }}
    {{ form.submit(class="btn btn-success mt-2") }}
</form>
{% endblock %}""",
    "app/templates/patient/appointments.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">My Appointments</h1>
<table class="table table-striped">
    <tr><th>Doctor ID</th><th>Date/Time</th><th>Status</th><th>Actions</th></tr>
    {% for appt in appointments %}
    <tr>
        <td>{{ appt.DoctorID }}</td>
        <td>{{ appt.ScheduledAt }}</td>
        <td><span class="badge bg-primary">{{ appt.Status }}</span></td>
        <td>
            {% if appt.Status == 'Pending' or appt.Status == 'Confirmed' %}
            <form method="POST" action="{{ url_for('patient.cancel_appointment', id=appt.AppointmentID) }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <button type="submit" class="btn btn-danger btn-sm">Cancel</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% endfor %}
</table>
{% endblock %}""",
    "app/templates/patient/vitals.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Vitals Tracker</h1>
<div class="row">
    <div class="col-md-4">
        <form method="POST" class="card p-3 shadow-sm border-0">
            {{ form.hidden_tag() }}
            {{ form.blood_pressure.label }} {{ form.blood_pressure(class="form-control mb-2") }}
            {{ form.sugar_level.label }} {{ form.sugar_level(class="form-control mb-2") }}
            {{ form.weight.label }} {{ form.weight(class="form-control mb-2") }}
            {{ form.heart_rate.label }} {{ form.heart_rate(class="form-control mb-3") }}
            {{ form.submit(class="btn btn-primary") }}
        </form>
    </div>
    <div class="col-md-8">
        <div class="card p-3 shadow-sm border-0">
            <canvas id="vitalsChart"></canvas>
        </div>
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
    const ctx = document.getElementById('vitalsChart');
    const vitalsData = {{ vitals_json | safe }};
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: vitalsData.map(v => new Date(v.RecordedAt).toLocaleDateString()),
            datasets: [
                {label: 'Heart Rate', data: vitalsData.map(v => v.HeartRate), borderColor: 'red'},
                {label: 'Weight', data: vitalsData.map(v => v.Weight), borderColor: 'blue'}
            ]
        }
    });
</script>
{% endblock %}""",
    "app/templates/patient/records.html": """{% extends 'base.html' %}{% block content %}<h1>Medical Records</h1><p>Coming soon (Phase 8).</p>{% endblock %}""",
    "app/templates/patient/invoices.html": """{% extends 'base.html' %}{% block content %}<h1>Invoices</h1><p>Coming soon (Phase 8).</p>{% endblock %}""",
    "app/templates/patient/documents.html": """{% extends 'base.html' %}{% block content %}<h1>Documents</h1><p>Coming soon (Phase 8).</p>{% endblock %}""",
    "tests/test_patient.py": """import pytest
from app.services.auth_service import AuthService
from app.services.patient_service import PatientService

def test_patient_dashboard_requires_login(client):
    res = client.get('/patient/dashboard', follow_redirects=True)
    assert b'Please log in' in res.data

def test_patient_booking_and_double_book(client, dynamodb_setup):
    auth = AuthService()
    auth.register_patient("Pat", "p@p.com", "123", "Pass123!")
    auth.register_doctor("Doc", "d@d.com", "123", "Cardio", "Reg123", "Pass123!")
    p_user = auth.user_repo.get_user_by_email('p@p.com')
    d_user = auth.user_repo.get_user_by_email('d@d.com')

    # Approve doctor
    auth.doctor_repo.update_item(auth.doctor_repo.TABLE, {'DoctorID': d_user['UserID']}, "SET #st = :s", {':s': 'Approved'}, {'#st': 'Status'})

    svc = PatientService()
    appt = svc.book_appointment(p_user['UserID'], d_user['UserID'], "2026-10-10", "10:00", "Notes")
    assert appt is not None

    with pytest.raises(ValueError, match="already been booked"):
        svc.book_appointment(p_user['UserID'], d_user['UserID'], "2026-10-10", "10:00", "Notes2")
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
