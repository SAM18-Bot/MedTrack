import pytest
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
