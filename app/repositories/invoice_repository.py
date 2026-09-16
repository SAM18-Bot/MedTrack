from app.repositories.base_repository import BaseRepository

class InvoiceRepository(BaseRepository):
    TABLE = "Invoices"

    def get_patient_invoices(self, patient_id):
        return self.query_index(self.TABLE, "patient-index", "PatientID = :pid", {":pid": patient_id})

    def get_doctor_invoices(self, doctor_id):
        # Fallback to scan since no doctor-index exists
        table = self._get_table(self.TABLE)
        from boto3.dynamodb.conditions import Attr
        return self._execute_with_retry(table.scan, FilterExpression=Attr("DoctorID").eq(doctor_id)).get('Items', [])
