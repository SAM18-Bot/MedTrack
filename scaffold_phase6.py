import os

files = {
    "app/forms/doctor_forms.py": """from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, FloatField, SubmitField
from wtforms.validators import DataRequired, Optional

class DoctorProfileForm(FlaskForm):
    bio = TextAreaField('Bio', validators=[Optional()])
    clinic_address = TextAreaField('Clinic Address', validators=[Optional()])
    consultation_fee = FloatField('Consultation Fee ($)', validators=[Optional()])
    experience_years = IntegerField('Years of Experience', validators=[Optional()])
    qualifications = StringField('Qualifications (comma-separated)', validators=[Optional()])
    submit = SubmitField('Update Profile')

class AvailabilityForm(FlaskForm):
    date = StringField('Date (YYYY-MM-DD)', validators=[DataRequired()])
    start_time = StringField('Start Time (HH:MM)', validators=[DataRequired()])
    end_time = StringField('End Time (HH:MM)', validators=[DataRequired()])
    slot_duration = IntegerField('Slot Duration (minutes)', default=15, validators=[DataRequired()])
    submit = SubmitField('Set Availability')

class ConsultationForm(FlaskForm):
    symptoms = TextAreaField('Symptoms', validators=[DataRequired()])
    diagnosis = TextAreaField('Diagnosis', validators=[DataRequired()])
    medicines = TextAreaField('Medicines (JSON or text)', validators=[Optional()])
    notes = TextAreaField('Private Notes', validators=[Optional()])
    submit = SubmitField('Complete Consultation')
""",
    "app/repositories/doctor_availability_repository.py": """from app.repositories.base_repository import BaseRepository

class DoctorAvailabilityRepository(BaseRepository):
    TABLE = "DoctorAvailability"
""",
    "app/repositories/diagnosis_report_repository.py": """from app.repositories.base_repository import BaseRepository

class DiagnosisReportRepository(BaseRepository):
    TABLE = "DiagnosisReports"
""",
    "app/repositories/prescription_repository.py": """from app.repositories.base_repository import BaseRepository

class PrescriptionRepository(BaseRepository):
    TABLE = "Prescriptions"
""",
    "app/services/doctor_service.py": """import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.doctor_availability_repository import DoctorAvailabilityRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.diagnosis_report_repository import DiagnosisReportRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.utils import get_utc_now

class DoctorService:
    def __init__(self):
        self.doc_repo = DoctorRepository()
        self.avail_repo = DoctorAvailabilityRepository()
        self.appt_repo = AppointmentRepository()
        self.diag_repo = DiagnosisReportRepository()
        self.rx_repo = PrescriptionRepository()

    def get_profile(self, doc_id):
        return self.doc_repo.get_item(self.doc_repo.TABLE, {"DoctorID": doc_id})

    def update_profile(self, doc_id, data):
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
        self.doc_repo.update_item(self.doc_repo.TABLE, {"DoctorID": doc_id}, expr, vals)

    def set_availability(self, doc_id, date_str, start_t, end_t, duration_mins):
        t = datetime.strptime(start_t, "%H:%M")
        end = datetime.strptime(end_t, "%H:%M")
        delta = timedelta(minutes=duration_mins)
        
        slots = []
        while t + delta <= end:
            slots.append(t.strftime("%H:%M"))
            t += delta
            
        item = {
            "DoctorID": doc_id,
            "Date": date_str,
            "Slots": slots,
            "IsDeleted": False,
            "UpdatedAt": get_utc_now()
        }
        self.avail_repo.put_item(self.avail_repo.TABLE, item)
        return slots

    def get_availability(self, doc_id, date_str):
        return self.avail_repo.get_item(self.avail_repo.TABLE, {"DoctorID": doc_id, "Date": date_str})

    def get_queue(self, doc_id, date_str):
        return self.appt_repo.query_index(
            self.appt_repo.TABLE,
            "doctor-index",
            "DoctorID = :d AND begins_with(ScheduledAt, :prefix)",
            {":d": doc_id, ":prefix": date_str}
        )

    def get_appointment(self, appt_id):
        return self.appt_repo.get_item(self.appt_repo.TABLE, {"AppointmentID": appt_id})

    def update_appointment_status(self, appt_id, status):
        self.appt_repo.update_item(
            self.appt_repo.TABLE,
            {"AppointmentID": appt_id},
            "SET #st = :status, UpdatedAt = :updated",
            {":status": status, ":updated": get_utc_now()},
            expression_attribute_names={"#st": "Status"}
        )

    def complete_consultation(self, appt_id, doc_id, pat_id, symptoms, diagnosis, medicines, notes):
        # Diagnosis
        diag_id = str(uuid.uuid4())
        self.diag_repo.put_item(self.diag_repo.TABLE, {
            "ReportID": diag_id, "AppointmentID": appt_id, "PatientID": pat_id, "DoctorID": doc_id,
            "Symptoms": symptoms, "Diagnosis": diagnosis, "PrivateNotes": notes, "CreatedAt": get_utc_now()
        })
        # Prescription
        if medicines:
            rx_id = str(uuid.uuid4())
            self.rx_repo.put_item(self.rx_repo.TABLE, {
                "PrescriptionID": rx_id, "AppointmentID": appt_id, "PatientID": pat_id, "DoctorID": doc_id,
                "Medicines": medicines, "CreatedAt": get_utc_now()
            })
        # Complete Appt
        self.update_appointment_status(appt_id, "Completed")
""",
    "app/blueprints/doctor.py": """from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.utils import login_required, role_required
from app.forms.doctor_forms import DoctorProfileForm, AvailabilityForm, ConsultationForm
from app.services.doctor_service import DoctorService

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.before_request
@login_required
@role_required('Doctor')
def before_request():
    pass

@doctor_bp.route('/dashboard')
def dashboard():
    svc = DoctorService()
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    queue = svc.get_queue(session['user_id'], today)
    doc = svc.get_profile(session['user_id'])
    # Revenue approx
    completed = [q for q in queue if q['Status'] == 'Completed']
    daily_revenue = len(completed) * float(doc.get('ConsultationFee', 0)) if doc else 0
    return render_template('doctor/dashboard.html', queue=queue, rev=daily_revenue, doctor=doc)

@doctor_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    svc = DoctorService()
    form = DoctorProfileForm()
    if request.method == 'GET':
        p = svc.get_profile(session['user_id'])
        if p:
            form.bio.data = p.get('Bio')
            form.clinic_address.data = p.get('ClinicAddress')
            form.consultation_fee.data = float(p.get('ConsultationFee', 0)) if p.get('ConsultationFee') else None
            form.experience_years.data = p.get('ExperienceYears')
            form.qualifications.data = p.get('Qualifications')
            
    if form.validate_on_submit():
        data = {
            'Bio': form.bio.data,
            'ClinicAddress': form.clinic_address.data,
            'ConsultationFee': form.consultation_fee.data,
            'ExperienceYears': form.experience_years.data,
            'Qualifications': form.qualifications.data
        }
        svc.update_profile(session['user_id'], data)
        flash('Profile updated.', 'success')
        return redirect(url_for('doctor.profile'))
    return render_template('doctor/profile.html', form=form)

@doctor_bp.route('/availability', methods=['GET', 'POST'])
def availability():
    svc = DoctorService()
    form = AvailabilityForm()
    if form.validate_on_submit():
        svc.set_availability(session['user_id'], form.date.data, form.start_time.data, form.end_time.data, form.slot_duration.data)
        flash('Availability slots generated successfully.', 'success')
        return redirect(url_for('doctor.availability'))
    return render_template('doctor/availability.html', form=form)

@doctor_bp.route('/queue')
def queue():
    svc = DoctorService()
    date_str = request.args.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    q = svc.get_queue(session['user_id'], date_str)
    return render_template('doctor/queue.html', queue=q, date=date_str)

@doctor_bp.route('/queue/<id>/status', methods=['POST'])
def update_status(id):
    status = request.form.get('status')
    svc = DoctorService()
    svc.update_appointment_status(id, status)
    flash(f'Status updated to {status}.', 'success')
    return redirect(url_for('doctor.queue'))

@doctor_bp.route('/consultation/<appt_id>', methods=['GET', 'POST'])
def consultation(appt_id):
    svc = DoctorService()
    appt = svc.get_appointment(appt_id)
    if not appt or appt['DoctorID'] != session['user_id']:
        flash('Unauthorized or invalid appointment.', 'danger')
        return redirect(url_for('doctor.queue'))
        
    form = ConsultationForm()
    if form.validate_on_submit():
        svc.complete_consultation(
            appt_id, session['user_id'], appt['PatientID'],
            form.symptoms.data, form.diagnosis.data, form.medicines.data, form.notes.data
        )
        flash('Consultation completed and saved.', 'success')
        return redirect(url_for('doctor.queue'))
        
    return render_template('doctor/consultation.html', form=form, appt=appt)

@doctor_bp.route('/reviews')
def reviews(): return render_template('doctor/reviews.html')

@doctor_bp.route('/revenue')
def revenue(): return render_template('doctor/revenue.html')
""",
    "app/templates/doctor/dashboard.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Doctor Dashboard</h1>
{% if doctor and doctor.Status == 'Pending' %}
<div class="alert alert-warning">Your account is pending admin approval. You cannot receive bookings yet.</div>
{% endif %}
<div class="row">
    <div class="col-md-4"><div class="card p-3 bg-primary text-white mb-3 border-0"><h5>Today's Queue</h5><h2>{{ queue|length }}</h2></div></div>
    <div class="col-md-4"><div class="card p-3 bg-success text-white mb-3 border-0"><h5>Daily Revenue</h5><h2>${{ rev }}</h2></div></div>
</div>
<div class="mt-4">
    <h3>Quick Links</h3>
    <a href="{{ url_for('doctor.queue') }}" class="btn btn-outline-primary">Manage Queue</a>
    <a href="{{ url_for('doctor.availability') }}" class="btn btn-outline-primary">Set Availability</a>
    <a href="{{ url_for('doctor.profile') }}" class="btn btn-outline-primary">My Profile</a>
</div>
{% endblock %}""",
    "app/templates/doctor/profile.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">My Professional Profile</h1>
<form method="POST" class="w-75">
    {{ form.hidden_tag() }}
    <div class="mb-3">{{ form.bio.label }} {{ form.bio(class="form-control") }}</div>
    <div class="mb-3">{{ form.clinic_address.label }} {{ form.clinic_address(class="form-control") }}</div>
    <div class="mb-3">{{ form.consultation_fee.label }} {{ form.consultation_fee(class="form-control") }}</div>
    <div class="mb-3">{{ form.experience_years.label }} {{ form.experience_years(class="form-control") }}</div>
    <div class="mb-3">{{ form.qualifications.label }} {{ form.qualifications(class="form-control") }}</div>
    {{ form.submit(class="btn btn-primary") }}
</form>
{% endblock %}""",
    "app/templates/doctor/availability.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Availability Manager</h1>
<p>Select a date and working hours to automatically generate bookable slots.</p>
<form method="POST" class="w-50 card p-4 shadow-sm border-0">
    {{ form.hidden_tag() }}
    {{ form.date.label }} {{ form.date(class="form-control mb-3", placeholder="YYYY-MM-DD") }}
    {{ form.start_time.label }} {{ form.start_time(class="form-control mb-3", placeholder="09:00") }}
    {{ form.end_time.label }} {{ form.end_time(class="form-control mb-3", placeholder="17:00") }}
    {{ form.slot_duration.label }} {{ form.slot_duration(class="form-control mb-3") }}
    {{ form.submit(class="btn btn-primary") }}
</form>
{% endblock %}""",
    "app/templates/doctor/queue.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Appointment Queue ({{ date }})</h1>
<table class="table table-striped align-middle">
    <tr><th>Time</th><th>Patient ID</th><th>Status</th><th>Notes</th><th>Actions</th></tr>
    {% for q in queue|sort(attribute='ScheduledAt') %}
    <tr>
        <td>{{ q.ScheduledAt.split('T')[1][:5] }}</td>
        <td>{{ q.PatientID }}</td>
        <td><span class="badge bg-secondary">{{ q.Status }}</span></td>
        <td>{{ q.Notes }}</td>
        <td>
            {% if q.Status == 'Pending' %}
            <form method="POST" action="{{ url_for('doctor.update_status', id=q.AppointmentID) }}" class="d-inline">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <input type="hidden" name="status" value="Confirmed"/>
                <button class="btn btn-sm btn-success">Confirm</button>
            </form>
            {% elif q.Status == 'Confirmed' %}
            <a href="{{ url_for('doctor.consultation', appt_id=q.AppointmentID) }}" class="btn btn-sm btn-primary">Start Consultation</a>
            <form method="POST" action="{{ url_for('doctor.update_status', id=q.AppointmentID) }}" class="d-inline">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <input type="hidden" name="status" value="No Show"/>
                <button class="btn btn-sm btn-warning">No Show</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% endfor %}
</table>
{% endblock %}""",
    "app/templates/doctor/consultation.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Consultation</h1>
<div class="row">
    <div class="col-md-4 bg-light p-3 border-end">
        <h4>Patient Context</h4>
        <p><strong>Patient ID:</strong> {{ appt.PatientID }}</p>
        <p><strong>Scheduled:</strong> {{ appt.ScheduledAt }}</p>
        <p><strong>Notes:</strong> {{ appt.Notes }}</p>
        <hr>
        <h5>Medical History</h5>
        <p class="text-muted small">Loaded from patient records...</p>
    </div>
    <div class="col-md-8 p-3">
        <h4>Diagnosis & Prescription</h4>
        <form method="POST">
            {{ form.hidden_tag() }}
            {{ form.symptoms.label }} {{ form.symptoms(class="form-control mb-3", rows="3") }}
            {{ form.diagnosis.label }} {{ form.diagnosis(class="form-control mb-3", rows="3") }}
            {{ form.medicines.label }} {{ form.medicines(class="form-control mb-3", rows="3", placeholder="e.g. Paracetamol 500mg, twice a day") }}
            {{ form.notes.label }} <small class="text-muted">(Not visible to patient)</small> {{ form.notes(class="form-control mb-3", rows="2") }}
            {{ form.submit(class="btn btn-success w-100") }}
        </form>
    </div>
</div>
{% endblock %}""",
    "app/templates/doctor/reviews.html": """{% extends 'base.html' %}{% block content %}<h1>My Reviews</h1><p>Coming soon (Phase 8).</p>{% endblock %}""",
    "app/templates/doctor/revenue.html": """{% extends 'base.html' %}{% block content %}<h1>Revenue Dashboard</h1><p>Coming soon (Phase 8).</p>{% endblock %}""",
    "tests/test_doctor.py": """import pytest
from app.services.doctor_service import DoctorService

def test_availability_generation(dynamodb_setup):
    svc = DoctorService()
    slots = svc.set_availability("doc123", "2026-10-10", "09:00", "10:00", 20)
    assert len(slots) == 4
    assert slots == ["09:00", "09:20", "09:40", "10:00"]
    
    saved = svc.get_availability("doc123", "2026-10-10")
    assert saved['Slots'] == ["09:00", "09:20", "09:40", "10:00"]

def test_complete_consultation(dynamodb_setup):
    svc = DoctorService()
    appt_id = "appt123"
    
    # Mock an appointment
    svc.appt_repo.put_item(svc.appt_repo.TABLE, {
        "AppointmentID": appt_id, "DoctorID": "doc123", "PatientID": "pat123", 
        "ScheduledAt": "2026-10-10T09:00:00Z", "Status": "Confirmed", "IsDeleted": False
    })
    
    svc.complete_consultation(appt_id, "doc123", "pat123", "fever", "viral", "paracetamol", "rest")
    
    # Check status updated
    updated_appt = svc.get_appointment(appt_id)
    assert updated_appt['Status'] == "Completed"
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
