from app.repositories.base_repository import BaseRepository

class VitalsRepository(BaseRepository):
    TABLE = "Vitals"

    def get_vitals(self, patient_id):
        items = self.query_index(
            table_name=self.TABLE,
            index_name=None,
            key_condition_expression="PatientID = :pid",
            expression_attribute_values={":pid": patient_id}
        )
        return sorted(items, key=lambda x: x['RecordedAt'])
