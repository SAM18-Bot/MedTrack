from app.repositories.base_repository import BaseRepository

class ReviewRepository(BaseRepository):
    TABLE = "Reviews"

    def get_doctor_reviews(self, doctor_id):
        return self.query_index(self.TABLE, "doctor-index", "DoctorID = :did", {":did": doctor_id})

    def get_patient_reviews(self, patient_id):
        return self.query_index(self.TABLE, "patient-index", "PatientID = :pid", {":pid": patient_id})
