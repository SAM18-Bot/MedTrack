from app.repositories.base_repository import BaseRepository
from botocore.exceptions import ClientError
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class AppointmentRepository(BaseRepository):
    TABLE = "Appointments"

    def create_appointment_with_lock(self, appointment):
        doc_id = appointment['DoctorID']
        sched = appointment['ScheduledAt']
        lock_id = f"SLOT#{doc_id}#{sched}"
        
        try:
            self.dynamodb.meta.client.transact_write_items(
                TransactItems=[
                    {
                        'Put': {
                            'TableName': f"{self.table_prefix}{self.TABLE}",
                            'Item': {
                                'AppointmentID': lock_id,
                                'Type': 'SlotLock',
                                'IsDeleted': False
                            },
                            'ConditionExpression': 'attribute_not_exists(AppointmentID)'
                        }
                    },
                    {
                        'Put': {
                            'TableName': f"{self.table_prefix}{self.TABLE}",
                            'Item': appointment
                        }
                    }
                ]
            )
            return appointment
        except ClientError as e:
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                raise ValueError("This slot has already been booked. Please choose another time.")
            logger.error(f"Failed to book appointment: {e}")
            raise ValueError("Failed to book appointment.")

    def get_patient_appointments(self, patient_id):
        return self.query_index(
            self.TABLE,
            "patient-index",
            "PatientID = :pid",
            {":pid": patient_id}
        )
    def release_slot_lock(self, appt_id):
        appt = self.get_item(self.TABLE, {"AppointmentID": appt_id})
        if appt and appt.get('DoctorID') and appt.get('ScheduledAt'):
            lock_id = f"SLOT#{appt['DoctorID']}#{appt['ScheduledAt']}"
            table = self._get_table(self.TABLE)
            self._execute_with_retry(table.delete_item, Key={"AppointmentID": lock_id})
