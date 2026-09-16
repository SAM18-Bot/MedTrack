import uuid
from app.repositories.user_repository import UserRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.support_ticket_repository import SupportTicketRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.specialization_repository import SpecializationRepository
from app.services.notification_service import NotificationService
from app.utils import get_utc_now

class AdminService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.doc_repo = DoctorRepository()
        self.ticket_repo = SupportTicketRepository()
        self.audit_repo = AuditRepository()
        self.spec_repo = SpecializationRepository()
        self.notification = NotificationService()

    def _scan(self, repo):
        table = repo.dynamodb.Table(f"{repo.table_prefix}{repo.TABLE}")
        return table.scan().get('Items', [])

    def get_dashboard_stats(self):
        users = self._scan(self.user_repo)
        pending_docs = self.get_pending_doctors()
        tickets = self._scan(self.ticket_repo)
        open_tickets = [t for t in tickets if t.get('Status') == 'Open']
        
        return {
            "total_users": len(users),
            "pending_doctors": len(pending_docs),
            "open_tickets": len(open_tickets)
        }

    def get_pending_doctors(self):
        return self.doc_repo.query_index(
            self.doc_repo.TABLE,
            "status-index",
            "#st = :status",
            {":status": "Pending"},
            expression_attribute_names={"#st": "Status"}
        )

    def approve_doctor(self, doc_id):
        self.doc_repo.update_item(
            self.doc_repo.TABLE,
            {"DoctorID": doc_id},
            "SET #st = :status, UpdatedAt = :u",
            {":status": "Approved", ":u": get_utc_now()},
            {"#st": "Status"}
        )
        self.notification.notify_admin("Doctor Approved", f"Doctor {doc_id} was approved.")

    def reject_doctor(self, doc_id):
        self.doc_repo.update_item(
            self.doc_repo.TABLE,
            {"DoctorID": doc_id},
            "SET #st = :status, UpdatedAt = :u",
            {":status": "Rejected", ":u": get_utc_now()},
            {"#st": "Status"}
        )

    def get_all_users(self):
        return self._scan(self.user_repo)

    def ban_user(self, user_id):
        self.user_repo.update_item(
            self.user_repo.TABLE,
            {"UserID": user_id},
            "SET IsDeleted = :d, UpdatedAt = :u",
            {":d": True, ":u": get_utc_now()}
        )

    def get_specializations(self):
        return self._scan(self.spec_repo)

    def add_specialization(self, name, description):
        spec_id = str(uuid.uuid4())
        self.spec_repo.put_item(self.spec_repo.TABLE, {
            "SpecializationID": spec_id,
            "Name": name,
            "Description": description,
            "IsDeleted": False,
            "CreatedAt": get_utc_now()
        })

    def get_support_tickets(self):
        return self._scan(self.ticket_repo)

    def resolve_ticket(self, ticket_id):
        self.ticket_repo.update_item(
            self.ticket_repo.TABLE,
            {"TicketID": ticket_id},
            "SET #st = :status, UpdatedAt = :u",
            {":status": "Resolved", ":u": get_utc_now()},
            {"#st": "Status"}
        )

    def get_audit_logs(self):
        logs = self._scan(self.audit_repo)
        return sorted(logs, key=lambda x: x.get('Timestamp', ''), reverse=True)
