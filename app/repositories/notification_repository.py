import uuid
from app.repositories.base_repository import BaseRepository
from app.utils import get_utc_now

class NotificationRepository(BaseRepository):
    TABLE = "Notifications"

    def get_user_notifications(self, user_id):
        items = self.query_index(
            self.TABLE,
            "user-index",
            "UserID = :uid",
            {":uid": user_id}
        )
        return sorted(items, key=lambda x: x.get('CreatedAt', ''), reverse=True)

    def get_unread_count(self, user_id):
        notifications = self.get_user_notifications(user_id)
        return sum(1 for n in notifications if not n.get('IsRead', False))

    def create_notification(self, user_id, message, link=None):
        item = {
            "NotificationID": str(uuid.uuid4()),
            "UserID": user_id,
            "Message": message,
            "Link": link,
            "IsRead": False,
            "CreatedAt": get_utc_now(),
            "IsDeleted": False
        }
        self.put_item(self.TABLE, item)
        return item

    def mark_as_read(self, notif_id):
        item = self.get_item(self.TABLE, {"NotificationID": notif_id})
        if item:
            item['IsRead'] = True
            item['UpdatedAt'] = get_utc_now()
            self.put_item(self.TABLE, item)
            return True
        return False
