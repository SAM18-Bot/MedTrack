import pytest
from botocore.exceptions import ClientError
from app.repositories.appointment_repository import AppointmentRepository

def test_double_booking_prevented(dynamodb_setup):
    repo = AppointmentRepository()
    doc_id = "doc_concurrent"
    pat1 = "pat_1"
    pat2 = "pat_2"
    slot = "2026-10-10T10:00:00Z"
    
    appt1 = {
        "AppointmentID": "appt1", "PatientID": pat1, "DoctorID": doc_id,
        "ScheduledAt": slot, "Status": "Pending"
    }
    repo.create_appointment_with_lock(appt1)
    
    # Book second time exactly the same slot -> should raise Exception
    appt2 = {
        "AppointmentID": "appt2", "PatientID": pat2, "DoctorID": doc_id,
        "ScheduledAt": slot, "Status": "Pending"
    }
    with pytest.raises(ValueError) as exc:
        repo.create_appointment_with_lock(appt2)
    
    assert "already been booked" in str(exc.value)
