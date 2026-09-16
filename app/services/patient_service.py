import uuid
from decimal import Decimal
from app.repositories.patient_repository import PatientRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.vitals_repository import VitalsRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.services.storage_service import StorageService
from app.services.notification_service import NotificationService
from app.utils import get_utc_now

class PatientService:
    def __init__(self):
        self.patient_repo = PatientRepository()
        self.doctor_repo = DoctorRepository()
        self.appointment_repo = AppointmentRepository()
        self.vitals_repo = VitalsRepository()
        self.doc_upload_repo = MedicalDocumentRepository()
        self.rx_repo = PrescriptionRepository()
        self.storage = StorageService()
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
        names = {"#UpdatedAt": "UpdatedAt"}
        expr_parts = ["#UpdatedAt = :updated"]
        
        for k, v in data.items():
            if v is not None and v != '':
                expr_parts.append(f"#{k} = :{k}")
                vals[f":{k}"] = v
                names[f"#{k}"] = k
        
        expr += ", ".join(expr_parts)
        self.patient_repo.update_item(
            self.patient_repo.TABLE, 
            {"PatientID": patient_id}, 
            expr, 
            vals, 
            expression_attribute_names=names
        )

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

    def get_prescriptions(self, patient_id):
        return self.rx_repo.query_index(self.rx_repo.TABLE, 'patient-index', 'PatientID = :pid', {':pid': patient_id})

    def get_prescription_by_id(self, rx_id):
        return self.rx_repo.get_item(self.rx_repo.TABLE, {'PrescriptionID': rx_id})

    def get_documents(self, patient_id):
        return self.doc_upload_repo.get_patient_documents(patient_id)

    def get_document_by_id(self, doc_id):
        return self.doc_upload_repo.get_item(self.doc_upload_repo.TABLE, {'DocumentID': doc_id})

    def upload_document(self, patient_id, title, file_obj, filename):
        doc_id = str(uuid.uuid4())
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'bin'
        s3_key = f"documents/{patient_id}/{doc_id}.{ext}"
        
        # Upload to S3
        self.storage.upload_file(file_obj, s3_key)
        
        # Save metadata
        item = {
            "DocumentID": doc_id,
            "PatientID": patient_id,
            "Title": title,
            "S3Key": s3_key,
            "UploadedAt": get_utc_now(),
            "IsDeleted": False
        }
        self.doc_upload_repo.put_item(self.doc_upload_repo.TABLE, item)
        
    def get_document_url(self, s3_key):
        return self.storage.get_presigned_url(s3_key)
