from app.repositories.base_repository import BaseRepository

class PrescriptionRepository(BaseRepository):
    TABLE = "Prescriptions"

    def get_patient_prescriptions(self, patient_id):
        return self.query_index(self.TABLE, 'patient-index', 'PatientID = :pid', {':pid': patient_id})
        
    def get_doctor_prescriptions(self, doctor_id):
        return self.query_index(self.TABLE, 'doctor-index', 'DoctorID = :did', {':did': doctor_id})
