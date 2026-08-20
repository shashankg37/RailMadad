"""Contract smoke tests; run with DATABASE_URL=sqlite:// pytest."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("LOCAL_STORAGE_PATH", "C:/tmp/railmadad-storage")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    assert client.get("/api/v1/health").json()["status"] == "ok"

def test_register_and_login():
    response = client.post("/api/v1/auth/register", json={"name":"Passenger", "email":"passenger@example.com", "password":"password123"})
    assert response.status_code == 201
    response = client.post("/api/v1/auth/login", json={"email":"passenger@example.com", "password":"password123"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
