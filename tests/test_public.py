import pytest

def test_public_pages(client):
    pages = ['/', '/about', '/services', '/how-it-works', '/for-doctors', '/faq', '/legal/terms', '/legal/privacy', '/legal/data-protection']
    for p in pages:
        res = client.get(p)
        assert res.status_code == 200

def test_contact_form(client, dynamodb_setup):
    res = client.post('/contact', data={
        'name': 'Tester', 'email': 'test@test.com', 'subject': 'Help', 'message': 'I need help', 'submit': True
    }, follow_redirects=True)
    assert b'Your message has been sent' in res.data
