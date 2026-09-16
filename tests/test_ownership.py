import pytest
from app.services.patient_service import PatientService
from app.services.doctor_service import DoctorService

def test_patient_cancel_appointment_ownership(client, dynamodb_setup):
    svc = PatientService()
    appt = svc.book_appointment("doc_test", "pat_owner", "2027-01-01T10:00:00Z", "Reason", "Notes")
    appt_id = appt['AppointmentID']

    with client.session_transaction() as sess:
        sess['user_id'] = 'pat_hacker'
        sess['role'] = 'Patient'
    
    res = client.post(f'/patient/appointments/{appt_id}/cancel')
    assert res.status_code == 403

def test_download_prescription_ownership(client, dynamodb_setup):
    from app.services.pdf_service import PdfService
    svc = PatientService()
    item = {
        'PrescriptionID': 'rx_123',
        'PatientID': 'pat_owner',
        'DoctorID': 'doc_test',
        'Medicines': 'Meds'
    }
    svc.rx_repo.put_item(svc.rx_repo.TABLE, item)

    with client.session_transaction() as sess:
        sess['user_id'] = 'pat_hacker'
        sess['role'] = 'Patient'

    res = client.get('/patient/prescriptions/rx_123/download')
    assert res.status_code == 403

def test_download_document_ownership(client, dynamodb_setup):
    svc = PatientService()
    item = {
        'DocumentID': 'doc_123',
        'PatientID': 'pat_owner',
        'S3Key': 'documents/pat_owner/doc_123.pdf'
    }
    svc.doc_upload_repo.put_item(svc.doc_upload_repo.TABLE, item)

    with client.session_transaction() as sess:
        sess['user_id'] = 'pat_hacker'
        sess['role'] = 'Patient'

    res = client.get(f'/patient/documents/doc_123/download')
    assert res.status_code == 403

def test_doctor_update_status_ownership(client, dynamodb_setup):
    svc = PatientService()
    appt = svc.book_appointment("doc_owner", "pat_test", "2027-01-02T10:00:00Z", "Reason", "Notes")
    appt_id = appt['AppointmentID']

    with client.session_transaction() as sess:
        sess['user_id'] = 'doc_hacker'
        sess['role'] = 'Doctor'
    
    res = client.post(f'/doctor/queue/{appt_id}/status', data={'status': 'Completed'})
    assert res.status_code == 403

def test_doctor_patient_detail_ownership(client, dynamodb_setup):
    svc = PatientService()
    appt = svc.book_appointment("doc_owner", "pat_test", "2027-01-03T10:00:00Z", "Reason", "Notes")
    appt_id = appt['AppointmentID']

    with client.session_transaction() as sess:
        sess['user_id'] = 'doc_hacker'
        sess['role'] = 'Doctor'
    
    res = client.get(f'/doctor/patients/{appt_id}')
    assert res.status_code == 403
