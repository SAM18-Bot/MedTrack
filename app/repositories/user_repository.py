from app.repositories.base_repository import BaseRepository
from app.utils import get_utc_now

class UserRepository(BaseRepository):
    TABLE = "Users"

    def get_user(self, user_id):
        return self.get_item(self.TABLE, {"UserID": user_id})

    def get_user_by_email(self, email):
        items = self.query_index(
            self.TABLE,
            "email-index",
            "Email = :email",
            {":email": email}
        )
        return items[0] if items else None

    def create_user(self, user_id, email, password_hash, role, phone=None):
        item = {
            "UserID": user_id,
            "Email": email,
            "PasswordHash": password_hash,
            "Role": role,
            "Phone": phone,
            "IsDeleted": False,
            "CreatedAt": get_utc_now(),
            "UpdatedAt": get_utc_now()
        }
        self.put_item(self.TABLE, item, condition_expression="attribute_not_exists(UserID)")
        return item
