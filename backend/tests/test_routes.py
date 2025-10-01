from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_endpoint():
    response = client.post("/api/chat", json={"user_id": "test_user", "message": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert "ok" in data
    assert "plan" in data
    assert "result" in data
