from app.repositories.base_repository import BaseRepository
from app.utils import get_utc_now

class LoginHistoryRepository(BaseRepository):
    TABLE = "LoginHistory"

    def log_login(self, user_id, ip_address, user_agent, status):
        item = {
            "UserID": user_id,
            "LoginAt": get_utc_now(),
            "IPAddress": ip_address,
            "UserAgent": user_agent,
            "Status": status
        }
        self.put_item(self.TABLE, item)

    def get_history(self, user_id):
        items = self.query_index(
            table_name=self.TABLE,
            index_name=None, # not a GSI, just query the base table (PK: UserID)
            key_condition_expression="UserID = :uid",
            expression_attribute_values={":uid": user_id}
        )
        # return sorted by time desc
        return sorted(items, key=lambda x: x['LoginAt'], reverse=True)
