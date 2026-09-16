def test_app_starts_and_index_returns_200(client):
    res = client.get('/')
    assert res.status_code == 200

def test_404_error_handler(client):
    res = client.get('/non-existent-route')
    assert res.status_code == 404
    assert b'404' in res.data