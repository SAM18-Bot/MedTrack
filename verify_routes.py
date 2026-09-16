from app import create_app
app = create_app()
with app.test_client() as client:
    print('--- HITTING / ROUTE ---')
    res = client.get('/')
    print(f"Status: {res.status_code}")
    print(res.data.decode('utf-8')[:250].replace('\n', ' ') + '...')

    print('\n--- HITTING /404 ROUTE ---')
    res404 = client.get('/non-existent')
    print(f"Status: {res404.status_code}")
    print(res404.data.decode('utf-8')[:250].replace('\n', ' ') + '...')

    print('\n--- REGISTERED ROUTES ---')
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
