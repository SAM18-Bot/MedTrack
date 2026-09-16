import uuid
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
        names = {"#UpdatedAt": "UpdatedAt"}
        expr_parts = ["#UpdatedAt = :updated"]
        
        for k, v in data.items():
            if v is not None and v != '':
                expr_parts.append(f"#{k} = :{k}")
                vals[f":{k}"] = v
                names[f"#{k}"] = k
                
        expr += ", ".join(expr_parts)
        self.doc_repo.update_item(
            self.doc_repo.TABLE, 
            {"DoctorID": doc_id}, 
            expr, 
            vals, 
            expression_attribute_names=names
        )

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
        if status in ['Cancelled', 'NoShow']:
            self.appt_repo.release_slot_lock(appt_id)
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
