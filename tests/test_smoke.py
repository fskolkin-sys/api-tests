def test_docs_available(client):
    r = client.get("/docs")
    assert r.status_code == 200

def test_openapi_available(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "paths" in data
