import uuid
import os
import sys
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

# Adjust path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.repositories.user_repository import UserRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.doctor_repository import DoctorRepository
from app.utils import get_utc_now

def seed_admin():
    user_repo = UserRepository()
    patient_repo = PatientRepository()
    doctor_repo = DoctorRepository()

    # 1. Admin Accounts
    admin_accounts = [
        (os.environ.get('ADMIN_EMAIL', 'admin@medtrack.local'), os.environ.get('ADMIN_PASSWORD', 'Admin@123!')),
        ('admin@medtrack.com', 'Admin@123!'),
        ('admin@medtrack.demo', 'password123')
    ]

    for email, pwd in admin_accounts:
        try:
            existing = user_repo.get_user_by_email(email)
        except Exception as e:
            if "email-index" in str(e) or "ValidationException" in str(e):
                print(f"\n⚠️ The 'MedTrack-Users' table does not have the required 'email-index'.")
                return
            raise e

        if not existing:
            user_id = str(uuid.uuid4())
            h = generate_password_hash(pwd, method='pbkdf2:sha256')
            user_repo.create_user(user_id, email, h, 'Admin')
            print(f"Admin user {email} seeded successfully.")

    # 2. Demo Patient Account
    patient_email = 'patient@medtrack.demo'
    existing_patient = user_repo.get_user_by_email(patient_email)
    if not existing_patient:
        pat_id = str(uuid.uuid4())
        pat_hash = generate_password_hash('password123', method='pbkdf2:sha256')
        user_repo.create_user(pat_id, patient_email, pat_hash, 'Patient', phone='+1234567890')
        patient_repo.put_item(patient_repo.TABLE, {
            'PatientID': pat_id,
            'Email': patient_email,
            'Name': 'Alex Mercer',
            'Phone': '+1234567890',
            'BloodGroup': 'O+',
            'Gender': 'Other',
            'IsDeleted': False,
            'CreatedAt': get_utc_now(),
            'UpdatedAt': get_utc_now()
        })
        print(f"Demo Patient {patient_email} seeded successfully.")

    # 3. Demo Doctor Account
    doctor_email = 'priya.nair@medtrack.demo'
    existing_doctor = user_repo.get_user_by_email(doctor_email)
    if not existing_doctor:
        doc_id = str(uuid.uuid4())
        doc_hash = generate_password_hash('password123', method='pbkdf2:sha256')
        user_repo.create_user(doc_id, doctor_email, doc_hash, 'Doctor', phone='+1987654321')
        doctor_repo.put_item(doctor_repo.TABLE, {
            'DoctorID': doc_id,
            'Email': doctor_email,
            'Name': 'Dr. Priya Nair',
            'SpecializationID': 'Cardiology',
            'RegistrationNumber': 'MED-89214',
            'Status': 'Approved',
            'Bio': 'Senior Consultant Cardiologist specializing in preventive cardiology, echocardiography, and vascular health.',
            'ConsultationFee': 150,
            'ExperienceYears': 12,
            'ClinicAddress': 'Heart Care Pavilion, Suite 400',
            'IsDeleted': False,
            'CreatedAt': get_utc_now(),
            'UpdatedAt': get_utc_now()
        })
        print(f"Demo Doctor {doctor_email} seeded successfully.")

if __name__ == '__main__':
    seed_admin()
