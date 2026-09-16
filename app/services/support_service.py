import uuid
from app.repositories.support_ticket_repository import SupportTicketRepository
from app.services.notification_service import NotificationService
from app.utils import get_utc_now

class SupportService:
    def __init__(self):
        self.ticket_repo = SupportTicketRepository()
        self.notification = NotificationService()

    def raise_ticket(self, user_id, category, priority, subject, description, is_guest=False):
        ticket_id = str(uuid.uuid4())
        ticket = {
            "TicketID": ticket_id,
            "UserID": user_id if not is_guest else "GUEST",
            "Category": category,
            "Priority": priority,
            "Subject": subject,
            "Description": description,
            "Status": "Open",
            "IsDeleted": False,
            "CreatedAt": get_utc_now(),
            "UpdatedAt": get_utc_now()
        }
        self.ticket_repo.put_item(self.ticket_repo.TABLE, ticket)
        msg = f"Priority [{priority}] - {subject}: {description[:100]}..."
        self.notification.notify_admin("New Support Ticket", msg)
        return ticket_id
