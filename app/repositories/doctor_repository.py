from app.repositories.base_repository import BaseRepository

class DoctorRepository(BaseRepository):
    TABLE = "Doctors"

    def get_by_status(self, status):
        return self.query_index(self.TABLE, "status-index", "#st = :status", {":status": status}, {"#st": "Status"})

    def get_all(self):
        return self._execute_with_retry(self._get_table(self.TABLE).scan).get('Items', [])
