import os

files = {
    "tests/test_roles.py": """import pytest
from flask import session

def test_role_required_unauthorized(client):
    res = client.get('/admin/dashboard')
    assert res.status_code == 302 # Redirects to login

def test_role_required_wrong_role(client, dynamodb_setup):
    with client.session_transaction() as sess:
        sess['user_id'] = 'user123'
        sess['role'] = 'Patient'
    
    res = client.get('/admin/dashboard')
    assert res.status_code == 403 # Forbidden

def test_role_required_allowed(client, dynamodb_setup):
    with client.session_transaction() as sess:
        sess['user_id'] = 'admin123'
        sess['role'] = 'Admin'
    
    res = client.get('/admin/dashboard')
    assert res.status_code == 200 # Allowed
""",
    "tests/test_concurrency.py": """import pytest
from botocore.exceptions import ClientError
from app.repositories.appointment_repository import AppointmentRepository

def test_double_booking_prevented(dynamodb_setup):
    repo = AppointmentRepository()
    doc_id = "doc_concurrent"
    pat1 = "pat_1"
    pat2 = "pat_2"
    slot = "2026-10-10T10:00:00Z"
    
    # Book first time -> should succeed
    appt1 = repo.book_appointment(doc_id, pat1, slot, "Notes1")
    assert appt1 is not None
    
    # Book second time exactly the same slot -> should raise TransactionCanceledException
    with pytest.raises(ClientError) as exc:
        repo.book_appointment(doc_id, pat2, slot, "Notes2")
    
    err_code = exc.value.response['Error']['Code']
    assert err_code == 'TransactionCanceledException'
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
