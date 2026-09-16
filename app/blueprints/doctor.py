from datetime import datetime, timezone
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
