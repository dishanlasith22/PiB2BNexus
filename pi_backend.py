"""PIB2BNexus FastAPI backend.

Authentication is verified by Pi App Studio's login exchange. The browser's
uid/username are never trusted. A short-lived HMAC app session is issued after
App Studio returns its verified identity. Pi Server API key is used only for
Pi payments, not for authentication.
"""
import os, time, json, hmac, hashlib, base64
import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

APP_STUDIO_LOGIN = "https://backend.appstudio-u7cm9zhmha0ruwv8.piappengine.com/pi/auth/v1/login"
PI_API_BASE = "https://api.minepi.com/v2"
PI_API_KEY = os.getenv("PI_API_KEY", "").strip()  # Payments only
PI_SANDBOX = os.getenv("PI_SANDBOX", "true").lower() == "true"
PI_PAYMENT_AMOUNT = float(os.getenv("PI_PAYMENT_AMOUNT", "0"))
PI_PAYMENT_MEMO = os.getenv("PI_PAYMENT_MEMO", "PIB2BNexus demo payment")
PI_SESSION_SECRET = os.getenv("PI_SESSION_SECRET", "").strip()
SESSION_TTL_SECONDS = int(os.getenv("PI_SESSION_TTL_SECONDS", "43200"))

app = FastAPI(title="PIB2BNexus Pi Integration", version="2.0.0")

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def issue_app_session(uid: str, username: str) -> str:
    if not PI_SESSION_SECRET or len(PI_SESSION_SECRET) < 32:
        raise HTTPException(503, "PI_SESSION_SECRET must be set to a random secret of at least 32 characters.")
    payload = {"uid": uid, "username": username, "exp": int(time.time()) + SESSION_TTL_SECONDS}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(PI_SESSION_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return body + "." + signature

def verified_app_user(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "App session token is required.")
    token = authorization[7:].strip()
    try:
        body, signature = token.split(".", 1)
        expected = _b64(hmac.new(PI_SESSION_SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        uid, username = payload.get("uid"), payload.get("username")
        if not uid or not username:
            raise ValueError("identity")
        return {"uid": str(uid), "username": str(username)}
    except Exception:
        raise HTTPException(401, "Invalid or expired app session. Please sign in again.")

def require_payment_key():
    if not PI_API_KEY:
        raise HTTPException(503, "PI_API_KEY is required for Pi payments only.")

def pi_api(method: str, path: str, payload=None):
    require_payment_key()
    try:
        response = requests.request(method, PI_API_BASE + path,
            headers={"Authorization": f"Key {PI_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=20)
    except requests.RequestException:
        raise HTTPException(502, "Could not connect to Pi Platform API.")
    return response

class AuthBody(BaseModel):
    accessToken: str = Field(min_length=1, max_length=4096)

class PaymentBody(BaseModel):
    paymentId: str = Field(min_length=1, max_length=200)
    txid: str | None = Field(default=None, max_length=200)

@app.get("/health")
def health():
    return {"ok": True, "sandbox": PI_SANDBOX,
            "auth_provider": "Pi App Studio", "payments_configured": bool(PI_API_KEY and PI_PAYMENT_AMOUNT > 0)}

@app.post("/auth/login")
def login(body: AuthBody):
    # The only identity source is the App Studio response. Do not use client uid/username.
    try:
        response = requests.post(APP_STUDIO_LOGIN,
            headers={"Content-Type": "application/json"},
            json={"accessToken": body.accessToken}, timeout=20)
    except requests.RequestException:
        raise HTTPException(502, "Could not connect to Pi App Studio authentication service.")
    if response.status_code != 200:
        raise HTTPException(401, "Pi App Studio could not verify this Pi sign-in.")
    try:
        result = response.json()
        appstudio_session = result.get("sessionToken")
        user = result.get("user") or {}
        uid, username = user.get("uid"), user.get("username")
    except (ValueError, AttributeError):
        raise HTTPException(502, "Pi App Studio returned an invalid authentication response.")
    if not appstudio_session or not uid or not username:
        raise HTTPException(401, "Pi App Studio did not return a verified Pioneer identity.")
    own_session = issue_app_session(str(uid), str(username))
   return {
    "ok": True,
    "verified": True,
    "app_session_token": own_session,
    "uid": str(uid),
    "username": str(username)
}

def verify_payment_belongs_to_user(payment_id: str, uid: str):
    response = pi_api("GET", f"/payments/{payment_id}")
    if response.status_code != 200:
        raise HTTPException(400, "Payment not found in Pi Platform.")
    payment = response.json()
    if payment.get("user_uid") != uid:
        raise HTTPException(403, "Payment owner could not be verified for this Pioneer.")
    if PI_PAYMENT_AMOUNT <= 0:
        raise HTTPException(503, "Set PI_PAYMENT_AMOUNT on the backend before enabling payments.")
    if float(payment.get("amount", -1)) != PI_PAYMENT_AMOUNT:
        raise HTTPException(400, "Payment amount does not match the server-configured amount.")
    if payment.get("memo") != PI_PAYMENT_MEMO:
        raise HTTPException(400, "Payment memo does not match the server configuration.")
    return payment

@app.post("/payments/approve")
def approve_payment(body: PaymentBody, authorization: str | None = Header(default=None)):
    user = verified_app_user(authorization)
    verify_payment_belongs_to_user(body.paymentId, user["uid"])
    response = pi_api("POST", f"/payments/{body.paymentId}/approve")
    if response.status_code not in (200, 201):
        raise HTTPException(response.status_code, "Pi payment approval failed.")
    return response.json()

@app.post("/payments/complete")
def complete_payment(body: PaymentBody, authorization: str | None = Header(default=None)):
    if not body.txid:
        raise HTTPException(400, "Pi transaction ID is required.")
    user = verified_app_user(authorization)
    verify_payment_belongs_to_user(body.paymentId, user["uid"])
    response = pi_api("POST", f"/payments/{body.paymentId}/complete", payload={"txid": body.txid})
    if response.status_code not in (200, 201):
        raise HTTPException(response.status_code, "Pi payment completion failed.")
    result = response.json(); status = result.get("status") or {}; transaction = result.get("transaction") or {}
    if not status.get("developer_completed") or not status.get("transaction_verified") or not transaction.get("verified"):
        raise HTTPException(409, "Pi Platform has not confirmed transaction completion.")
    # No POS sale/inventory is marked paid by this demo endpoint.
    return {"ok": True, "payment": result}
