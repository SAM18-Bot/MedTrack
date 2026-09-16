import pytest
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository

def test_patient_registration(client, dynamodb_setup):
    res = client.post('/auth/register/patient', data={
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '1234567890',
        'password': 'Password123!',
        'confirm_password': 'Password123!',
        'submit': True
    }, follow_redirects=True)
    assert b'Registration successful' in res.data
    
    repo = UserRepository()
    user = repo.get_user_by_email('john@example.com')
    assert user is not None
    assert user['Role'] == 'Patient'

def test_login_and_lockout(client, dynamodb_setup):
    svc = AuthService()
    svc.register_patient("Test", "test@test.com", "1234567890", "Pass123!")
    
    for _ in range(5):
        res = client.post('/auth/login', data={'email': 'test@test.com', 'password': 'wrong', 'submit': True}, follow_redirects=True)
        assert (b'Invalid email or password' in res.data) or (b'Account locked' in res.data)
        
    res = client.post('/auth/login', data={'email': 'test@test.com', 'password': 'wrong', 'submit': True}, follow_redirects=True)
    assert b'Account locked due to too many failed attempts' in res.data
