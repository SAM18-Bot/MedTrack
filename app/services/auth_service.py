import uuid
import secrets
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.repositories.user_repository import UserRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.login_history_repository import LoginHistoryRepository
from app.services.notification_service import NotificationService
from app.utils import get_utc_now

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.patient_repo = PatientRepository()
        self.doctor_repo = DoctorRepository()
        self.audit_repo = AuditRepository()
        self.login_history_repo = LoginHistoryRepository()
        self.notification_service = NotificationService()

    def register_patient(self, name: str, email: str, phone: str, password: str) -> dict:
        if self.user_repo.get_user_by_email(email):
            raise ValueError("Email already registered.")
        
        user_id = str(uuid.uuid4())
        pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')
        user = self.user_repo.create_user(user_id, email, pwd_hash, 'Patient', phone)
        
        patient = {
            "PatientID": user_id,
            "Email": email,
            "Name": name,
            "IsDeleted": False,
            "CreatedAt": get_utc_now(),
            "UpdatedAt": get_utc_now()
        }
        self.patient_repo.put_item(self.patient_repo.TABLE, patient)
        self.audit_repo.log_action("REGISTER_PATIENT", user_id, "User Registered", status="Success")
        return user

    def register_doctor(self, name: str, email: str, phone: str, spec_id: str, reg_number: str, password: str) -> dict:
        if self.user_repo.get_user_by_email(email):
            raise ValueError("Email already registered.")
        
        user_id = str(uuid.uuid4())
        pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')
        user = self.user_repo.create_user(user_id, email, pwd_hash, 'Doctor', phone)
        
        doctor = {
            "DoctorID": user_id,
            "Email": email,
            "Name": name,
            "SpecializationID": spec_id,
            "RegistrationNumber": reg_number,
            "Status": "Pending",
            "IsDeleted": False,
            "CreatedAt": get_utc_now(),
            "UpdatedAt": get_utc_now()
        }
        self.doctor_repo.put_item(self.doctor_repo.TABLE, doctor)
        self.audit_repo.log_action("REGISTER_DOCTOR", user_id, "Doctor Registered", status="Success")
        return user

    def authenticate(self, email: str, password: str, ip_address: str, user_agent: str) -> dict:
        user = self.user_repo.get_user_by_email(email)
        if not user:
            self.audit_repo.log_action("LOGIN_ATTEMPT", "UNKNOWN", f"Failed login for {email}", ip_address, user_agent, "Failed")
            raise ValueError("Invalid email or password.")
        
        if user.get('IsDeleted'):
            raise ValueError('This account has been suspended.')
        user_id = user['UserID']
        now = datetime.now(timezone.utc)
        
        lockout_until_str = user.get('LockoutUntil')
        if lockout_until_str:
            lockout_until = datetime.fromisoformat(lockout_until_str)
            if now < lockout_until:
                self.audit_repo.log_action("LOGIN_ATTEMPT", user_id, "Account locked", ip_address, user_agent, "Failed")
                raise ValueError("Account locked due to too many failed attempts. Try again later.")

        if not check_password_hash(user['PasswordHash'], password):
            attempts = user.get('FailedLoginAttempts', 0) + 1
            updates = {':attempts': attempts, ':updated': get_utc_now()}
            expr = "SET FailedLoginAttempts = :attempts, UpdatedAt = :updated"
            
            if attempts >= 5:
                lockout = (now + timedelta(minutes=15)).isoformat()
                expr += ", LockoutUntil = :lockout"
                updates[':lockout'] = lockout
            
            self.user_repo.update_item(self.user_repo.TABLE, {'UserID': user_id}, expr, updates)
            self.login_history_repo.log_login(user_id, ip_address, user_agent, "Failed")
            self.audit_repo.log_action("LOGIN_ATTEMPT", user_id, "Invalid password", ip_address, user_agent, "Failed")
            raise ValueError("Invalid email or password.")
        
        # Reset attempts on success. DynamoDB REMOVE is safe even if attribute doesn't exist
        expr = "SET FailedLoginAttempts = :attempts, UpdatedAt = :updated REMOVE LockoutUntil"
        updates = {':attempts': 0, ':updated': get_utc_now()}
        self.user_repo.update_item(self.user_repo.TABLE, {'UserID': user_id}, expr, updates)
        
        self.login_history_repo.log_login(user_id, ip_address, user_agent, "Success")
        self.audit_repo.log_action("LOGIN", user_id, "User logged in", ip_address, user_agent, "Success")
        return user

    def generate_otp(self, email: str) -> None:
        user = self.user_repo.get_user_by_email(email)
        if not user:
            return
        
        otp = str(secrets.randbelow(1000000)).zfill(6)
        expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        
        self.user_repo.update_item(
            self.user_repo.TABLE,
            {'UserID': user['UserID']},
            "SET ResetOTP = :otp, ResetOTPExpiry = :expiry, UpdatedAt = :updated",
            {':otp': generate_password_hash(otp, method='pbkdf2:sha256'), ':expiry': expiry, ':updated': get_utc_now()}
        )
        
        phone = user.get('Phone', '+10000000000')
        self.notification_service.send_otp(phone, otp)
        self.audit_repo.log_action("FORGOT_PASSWORD", user['UserID'], "OTP Generated", status="Success")

    def reset_password(self, email: str, otp: str, new_password: str) -> None:
        user = self.user_repo.get_user_by_email(email)
        if not user:
            raise ValueError("Invalid details.")
        
        stored_otp_hash = user.get('ResetOTP')
        expiry_str = user.get('ResetOTPExpiry')
        
        if not stored_otp_hash or not expiry_str:
            raise ValueError("Invalid or expired OTP.")
        
        expiry = datetime.fromisoformat(expiry_str)
        if datetime.now(timezone.utc) > expiry:
            raise ValueError("OTP has expired.")
            
        if not check_password_hash(stored_otp_hash, otp):
            raise ValueError("Invalid OTP.")
            
        pwd_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        self.user_repo.update_item(
            self.user_repo.TABLE,
            {'UserID': user['UserID']},
            "SET PasswordHash = :pwd, UpdatedAt = :updated REMOVE ResetOTP, ResetOTPExpiry",
            {':pwd': pwd_hash, ':updated': get_utc_now()}
        )
        self.audit_repo.log_action("RESET_PASSWORD", user['UserID'], "Password reset", status="Success")
