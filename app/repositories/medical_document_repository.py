from app.repositories.base_repository import BaseRepository

class MedicalDocumentRepository(BaseRepository):
    TABLE = "MedicalDocuments"
    
    def get_patient_documents(self, patient_id):
        return self.query_index(
            self.TABLE,
            "patient-index",
            "PatientID = :pid",
            {":pid": patient_id}
        )
