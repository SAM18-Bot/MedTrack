from app.repositories.base_repository import BaseRepository

class DiagnosisReportRepository(BaseRepository):
    TABLE = "DiagnosisReports"

    def get_patient_reports(self, patient_id):
        return self.query_index(self.TABLE, "patient-index", "PatientID = :pid", {":pid": patient_id})
