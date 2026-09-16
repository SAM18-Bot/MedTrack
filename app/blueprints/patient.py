import json
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
