import os
from datetime import datetime

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("LOCAL_STORAGE_PATH", "C:/tmp/railmadad-storage")

from fastapi.testclient import TestClient

from app.api.v1 import complaints
from app.main import app
from app.services.ai_pipeline import AIResult, PipelineState


client = TestClient(app)


def test_text_complaint_reaches_database(monkeypatch):
    email = f"integration-{datetime.utcnow().timestamp()}@example.com"
    registration = client.post(
        "/api/v1/auth/register",
        json={"name": "Passenger", "email": email, "password": "password123"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    ).json()["access_token"]

    async def fake_pipeline(_media_type, _media_path=None, _user_text=None):
        return (
            AIResult(
                category="garbage",
                subcategory="coach waste",
                severity=2,
                summary="Waste was reported in the coach.",
                suggested_action="Dispatch housekeeping.",
                department="Housekeeping / Sanitation",
                evidence=[{"source": "text", "text": "Waste in coach"}],
                confidence=0.88,
            ),
            PipelineState(status="classified"),
        )

    monkeypatch.setattr(complaints, "analyze_complaint", fake_pipeline)
    response = client.post(
        "/api/v1/complaints",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "There is waste in my coach", "media_ids": []},
    )
    assert registration.status_code == 201
    assert response.status_code == 201
    assert response.json()["status"] == "classified"
    complaint_id = response.json()["complaint_id"]
    detail = client.get(
        f"/api/v1/complaints/{complaint_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.json()["category"] == "garbage"
    assert detail.json()["department"] == "Housekeeping / Sanitation"