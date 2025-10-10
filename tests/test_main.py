import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_transcribe_invalid_format():
    response = client.post("/transcribe", files={"file": ("test.txt", b"not audio", "text/plain")})
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]

