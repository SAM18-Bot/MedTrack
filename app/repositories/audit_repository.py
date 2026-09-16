from app.repositories.base_repository import BaseRepository
from app.utils import get_utc_now
import uuid

class AuditRepository(BaseRepository):
    TABLE = "AuditLogs"

    def log_action(self, action_type, user_id, resource_id, ip_address="UNKNOWN", user_agent="UNKNOWN", status="Success"):
        item = {
            "LogID": str(uuid.uuid4()),
            "UserID": user_id,
            "ActionType": action_type,
            "ResourceID": resource_id,
            "IPAddress": ip_address,
            "UserAgent": user_agent,
            "Status": status,
            "Timestamp": get_utc_now()
        }
        self.put_item(self.TABLE, item)
