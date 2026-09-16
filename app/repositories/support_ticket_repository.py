from app.repositories.base_repository import BaseRepository

class SupportTicketRepository(BaseRepository):
    TABLE = "SupportTickets"

    def get_user_tickets(self, user_id):
        return self.query_index(
            self.TABLE,
            "user-index",
            "UserID = :uid",
            {":uid": user_id}
        )
