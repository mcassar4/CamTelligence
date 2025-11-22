import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


def test_health_endpoint():
    app = create_app()
    client = TestClient(app)
    response = client.get("/admin/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
