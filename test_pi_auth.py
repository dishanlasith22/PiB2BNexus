import os

os.environ["PI_SESSION_SECRET"] = "test-secret-value-at-least-32-characters-long"

from fastapi.testclient import TestClient
import pi_backend


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "sessionToken": "app-studio-session",
            "user": {"uid": "trusted-uid", "username": "trusted-name"},
        }


def test_login_uses_app_studio_identity_and_ignores_browser_identity(monkeypatch):
    def fake_post(url, **kwargs):
        assert url == pi_backend.PI_APP_STUDIO_LOGIN_URL
        assert kwargs["headers"] == {"Content-Type": "application/json"}
        assert kwargs["json"] == {"accessToken": "pi-access-token"}
        return FakeResponse()

    monkeypatch.setattr(pi_backend.requests, "post", fake_post)
    client = TestClient(pi_backend.app)
    response = client.post(
        "/auth/login",
        json={
            "accessToken": "pi-access-token",
            "uid": "attacker-uid",
            "username": "attacker-name",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"] == {"uid": "trusted-uid", "username": "trusted-name"}
    verified = pi_backend.verified_app_user(
        "Bearer " + data["app_session_token"]
    )
    assert verified == {"uid": "trusted-uid", "username": "trusted-name"}


def test_login_rejects_app_studio_response_without_verified_identity(monkeypatch):
    class InvalidResponse:
        status_code = 200

        def json(self):
            return {"sessionToken": "session", "user": {"username": "no-uid"}}

    monkeypatch.setattr(
        pi_backend.requests,
        "post",
        lambda *args, **kwargs: InvalidResponse(),
    )
    response = TestClient(pi_backend.app).post(
        "/auth/login", json={"accessToken": "pi-access-token"}
    )
    assert response.status_code == 401


def test_login_reports_invalid_pi_token(monkeypatch):
    class UnauthorizedResponse:
        status_code = 401

        def json(self):
            return {"detail": "invalid token"}

    monkeypatch.setattr(
        pi_backend.requests,
        "post",
        lambda *args, **kwargs: UnauthorizedResponse(),
    )
    response = TestClient(pi_backend.app).post(
        "/auth/login", json={"accessToken": "expired-token"}
    )
    assert response.status_code == 401


def test_login_page_has_nonce_csp_and_pi_frame_ancestors():
    response = TestClient(pi_backend.app).get("/")
    assert response.status_code == 200
    csp = response.headers["content-security-policy"]
    assert "https://socialchain.app" in csp
    assert "https://*.pinet.com" in csp
    assert "https://*.minepi.com" in csp
    assert "connect-src *" not in csp
    assert "frame-ancestors *" not in csp
    assert "x-frame-options" not in response.headers
    assert 'nonce="' in response.text
