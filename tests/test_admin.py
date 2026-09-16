import pytest
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService

def test_admin_dashboard_stats(dynamodb_setup):
    svc = AdminService()
    stats = svc.get_dashboard_stats()
    assert 'total_users' in stats
    assert stats['pending_doctors'] == 0

def test_approve_doctor(dynamodb_setup):
    auth = AuthService()
    auth.register_doctor("Doc", "doc2@doc.com", "123", "Spec", "Reg", "Pass123!")
    
    svc = AdminService()
    pending = svc.get_pending_doctors()
    assert len(pending) == 1
    
    doc_id = pending[0]['DoctorID']
    svc.approve_doctor(doc_id)
    
    pending_after = svc.get_pending_doctors()
    assert len(pending_after) == 0

def test_ban_user_prevents_login(dynamodb_setup):
    auth = AuthService()
    user = auth.register_patient("BadPat", "bad@pat.com", "123", "Pass123!")
    
    svc = AdminService()
    svc.ban_user(user['UserID'])
    
    with pytest.raises(ValueError, match="Invalid email or password."):
        auth.authenticate("bad@pat.com", "Pass123!", "127.0.0.1", "test")
