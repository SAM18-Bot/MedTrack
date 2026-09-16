from app.repositories.base_repository import BaseRepository

class DoctorAvailabilityRepository(BaseRepository):
    TABLE = "DoctorAvailability"

    def get_doctor_availability(self, doctor_id):
        return self.query_index(self.TABLE, 'doctor-index', 'DoctorID = :did', {':did': doctor_id})
