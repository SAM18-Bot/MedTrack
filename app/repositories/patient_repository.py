from app.repositories.base_repository import BaseRepository

class PatientRepository(BaseRepository):
    TABLE = "Patients"

    def get_patient(self, patient_id):
        return self.get_item(self.TABLE, {"PatientID": patient_id})

    def get_all(self):
        return self._execute_with_retry(self._get_table(self.TABLE).scan).get('Items', [])
