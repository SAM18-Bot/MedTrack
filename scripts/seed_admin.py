import uuid
import os
import sys
from werkzeug.security import generate_password_hash

# Adjust path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.repositories.user_repository import UserRepository

def seed_admin():
    repo = UserRepository()
    email = os.environ.get('ADMIN_EMAIL', 'admin@medtrack.local')
    password = os.environ.get('ADMIN_PASSWORD', 'Admin@123!')
    
    existing = repo.get_user_by_email(email)
    if existing:
        print(f"Admin {email} already exists.")
        return

    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    repo.create_user(user_id, email, password_hash, 'Admin')
    print(f"Admin user {email} seeded successfully.")

if __name__ == '__main__':
    seed_admin()
