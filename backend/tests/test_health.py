def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["env"] == "test"
    assert body["groq"] == "mock"  # no GROQ_API_KEY in tests
