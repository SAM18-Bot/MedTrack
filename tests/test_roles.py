import pytest
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
