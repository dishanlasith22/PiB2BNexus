import os
os.environ["PI_SESSION_SECRET"] = "test-secret-value-at-least-32-characters-long"
from fastapi.testclient import TestClient
import pi_backend

class FakeResponse:
    status_code = 200
    def json(self):
        return {"sessionToken": "appstudio-session", "user": {"uid": "trusted-uid", "username": "trusted-name"}}

def test_login_uses_appstudio_identity_and_ignores_browser_identity(monkeypatch):
    def fake_post(*args, **kwargs):
        assert kwargs["json"] == {"accessToken": "pi-access-token"}
        return FakeResponse()
    monkeypatch.setattr(pi_backend.requests, "post", fake_post)
    client = TestClient(pi_backend.app)
    response = client.post("/auth/login", json={"accessToken": "pi-access-token", "uid": "attacker-uid", "username": "attacker-name"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"] == {"uid": "trusted-uid", "username": "trusted-name"}
    verified = pi_backend.verified_app_user("Bearer " + data["app_session_token"])
    assert verified == {"uid": "trusted-uid", "username": "trusted-name"}
