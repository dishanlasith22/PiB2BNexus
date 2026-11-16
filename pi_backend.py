"""FastAPI backend for Pi identity verification and U2A payments.

The server API key is only read from the backend process environment.
The demo payment amount/memo are server-configured and are not accepted from
the browser as authoritative values.
"""
import os
import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

PI_API_BASE = "https://api.minepi.com/v2"
PI_API_KEY = os.getenv("PI_API_KEY", "").strip()
PI_SANDBOX = os.getenv("PI_SANDBOX", "true").lower() == "true"
PI_PAYMENT_AMOUNT = float(os.getenv("PI_PAYMENT_AMOUNT", "0"))
PI_PAYMENT_MEMO = os.getenv("PI_PAYMENT_MEMO", "PIB2BNexus demo payment")

app = FastAPI(title="PIB2BNexus Pi Platform API", version="1.0.0")

def require_server_key():
    if not PI_API_KEY:
        raise HTTPException(503, "Pi Server API Key is not configured on this backend.")

def pi_api(method: str, path: str, *, token: str = "", payload=None):
    if token:
        authorization = f"Bearer {token}"
    else:
        require_server_key()
        authorization = f"Key {PI_API_KEY}"
    try:
        response = requests.request(
            method, PI_API_BASE + path,
            headers={"Authorization": authorization, "Content-Type": "application/json"},
            json=payload, timeout=20,
        )
    except requests.RequestException:
        raise HTTPException(502, "Could not connect to Pi Platform API.")
    return response

def pioneer_from_header(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Pi access token is required.")
    token = authorization[len("Bearer "):].strip()
    if not token or len(token) > 4096:
        raise HTTPException(401, "Invalid Pi access token.")
    response = pi_api("GET", "/me", token=token)
    if response.status_code != 200:
        raise HTTPException(401, "Pi access token verification failed.")
    user = response.json()
    if not user.get("uid") or not user.get("username"):
        raise HTTPException(401, "Pi did not return a verified Pioneer identity.")
    return user

class PaymentBody(BaseModel):
    paymentId: str = Field(min_length=1, max_length=200)
    txid: str | None = Field(default=None, max_length=200)

@app.get("/health")
def health():
    return {"ok": True, "sandbox": PI_SANDBOX,
            "payments_configured": bool(PI_API_KEY and PI_PAYMENT_AMOUNT > 0)}

@app.post("/auth/verify")
def verify_auth(authorization: str | None = Header(default=None)):
    user = pioneer_from_header(authorization)
    return {"ok": True, "uid": user["uid"], "username": user["username"]}

def verify_payment_belongs_to_user(payment_id: str, uid: str):
    response = pi_api("GET", f"/payments/{payment_id}")
    if response.status_code != 200:
        raise HTTPException(400, "Payment not found in Pi Platform.")
    payment = response.json()
    # PaymentDTO uses user_uid for the Pioneer who initiated the payment.
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
    user = pioneer_from_header(authorization)
    verify_payment_belongs_to_user(body.paymentId, user["uid"])
    response = pi_api("POST", f"/payments/{body.paymentId}/approve")
    if response.status_code not in (200, 201):
        raise HTTPException(response.status_code, "Pi payment approval failed.")
    return response.json()

@app.post("/payments/complete")
def complete_payment(body: PaymentBody, authorization: str | None = Header(default=None)):
    if not body.txid:
        raise HTTPException(400, "Pi transaction ID is required.")
    user = pioneer_from_header(authorization)
    verify_payment_belongs_to_user(body.paymentId, user["uid"])
    response = pi_api("POST", f"/payments/{body.paymentId}/complete", payload={"txid": body.txid})
    if response.status_code not in (200, 201):
        raise HTTPException(response.status_code, "Pi payment completion failed.")
    result = response.json()
    status = result.get("status") or {}
    transaction = result.get("transaction") or {}
    if not status.get("developer_completed") or not status.get("transaction_verified") or not transaction.get("verified"):
        raise HTTPException(409, "Pi Platform has not confirmed transaction completion.")
    # This starter deliberately does not mark a POS sale paid or change stock.
    # Add a server-side Supabase order/payment insert here before fulfillment.
    return {"ok": True, "payment": result}
