import pytest
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

def test_patient_update_profile_reserved_keyword(dynamodb_setup):
    auth = AuthService()
    auth.register_patient("Test Pat", "tp@p.com", "123", "Pass123!")
    p_user = auth.user_repo.get_user_by_email('tp@p.com')
    
    svc = PatientService()
    svc.update_profile(p_user['UserID'], {'Name': 'Updated Pat', 'Address': '123 New St', 'Status': 'Active'})
    
    updated = svc.get_profile(p_user['UserID'])
    assert updated['Name'] == 'Updated Pat'
    assert updated['Address'] == '123 New St'
    assert updated['Status'] == 'Active'
