from app.repositories.base_repository import BaseRepository

class PatientRepository(BaseRepository):
    TABLE = "Patients"

    def get_all(self):
        return self._execute_with_retry(self._get_table(self.TABLE).scan).get('Items', [])
