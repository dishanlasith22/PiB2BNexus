
"""PIB2BNexus FastAPI backend.

Pi SDK access tokens are exchanged server-side with Pi App Studio. Only the
identity returned by App Studio is trusted; browser-supplied identity is ignored.
A short-lived HMAC app session is issued after App Studio validates the token.
Pi Server API key is used only for server-side Pi payment operations.
"""

import os
import time
import json
import hmac
import hashlib
import base64

import requests
from supabase import create_client, Client
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel, Field


PI_API_BASE = "https://api.minepi.com/v2"
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(503, "Supabase backend credentials are not configured.")
    if _supabase is None:
        try:
            _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        except Exception:
            raise HTTPException(503, "Supabase connection could not be initialized.")
    return _supabase
PI_APP_STUDIO_LOGIN_URL = "https://backend.appstudio-u7cm9zhmha0ruwv8.piappengine.com/pi/auth/v1/login"

PI_API_KEY = os.getenv("PI_API_KEY", "").strip()
PI_SANDBOX = os.getenv("PI_SANDBOX", "true").lower() == "true"

PI_PAYMENT_AMOUNT = float(os.getenv("PI_PAYMENT_AMOUNT", "0"))
PI_PAYMENT_MEMO = os.getenv(
    "PI_PAYMENT_MEMO",
    "PIB2BNexus demo payment"
)

PI_SESSION_SECRET = os.getenv("PI_SESSION_SECRET", "").strip()
SESSION_TTL_SECONDS = int(
    os.getenv("PI_SESSION_TTL_SECONDS", "43200")
)

app = FastAPI(
    title="PIB2BNexus Pi Integration",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pib2bnexus.onrender.com",
        "https://pib2bnexus.com",
        "https://www.pib2bnexus.com",
        "https://pib2bnexus-web-preview.onrender.com",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def issue_app_session(uid: str, username: str) -> str:
    if not PI_SESSION_SECRET or len(PI_SESSION_SECRET) < 32:
        raise HTTPException(
            503,
            "PI_SESSION_SECRET must be set to a random secret of at least 32 characters."
        )

    payload = {
        "uid": uid,
        "username": username,
        "exp": int(time.time()) + SESSION_TTL_SECONDS
    }

    body = _b64(
        json.dumps(payload, separators=(",", ":")).encode()
    )

    signature = _b64(
        hmac.new(
            PI_SESSION_SECRET.encode(),
            body.encode(),
            hashlib.sha256
        ).digest()
    )

    return body + "." + signature


def verified_app_user(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            401,
            "App session token is required."
        )

    token = authorization[7:].strip()

    try:
        body, signature = token.split(".", 1)

        expected = _b64(
            hmac.new(
                PI_SESSION_SECRET.encode(),
                body.encode(),
                hashlib.sha256
            ).digest()
        )

        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")

        padded = body + "=" * (-len(body) % 4)

        payload = json.loads(
            base64.urlsafe_b64decode(padded.encode())
        )

        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")

        uid = payload.get("uid")
        username = payload.get("username")

        if not uid or not username:
            raise ValueError("identity")

        return {
            "uid": str(uid),
            "username": str(username)
        }

    except Exception:
        raise HTTPException(
            401,
            "Invalid or expired app session. Please sign in again."
        )


def require_payment_key():
    if not PI_API_KEY:
        raise HTTPException(
            503,
            "PI_API_KEY is required for Pi payments only."
        )


def pi_api(method: str, path: str, payload=None):
    require_payment_key()

    try:
        response = requests.request(
            method,
            PI_API_BASE + path,
            headers={
                "Authorization": f"Key {PI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

    except requests.RequestException:
        raise HTTPException(
            502,
            "Could not connect to Pi Platform API."
        )

    return response


class AuthBody(BaseModel):
    accessToken: str = Field(
        min_length=1,
        max_length=4096
    )


class PaymentBody(BaseModel):
    paymentId: str = Field(
        min_length=1,
        max_length=200
    )

    txid: str | None = Field(
        default=None,
        max_length=200
    )


@app.get("/", response_class=HTMLResponse)
def pi_login_page():
    """Serve the top-level Pi Browser page so the SDK is not trapped in a Streamlit iframe."""
    page = Path(__file__).with_name("pi_login.html")
    if not page.is_file():
        raise HTTPException(503, "Pi login page is not installed.")
    nonce = base64.b64encode(os.urandom(18)).decode("ascii")
    html = page.read_text(encoding="utf-8").replace("__CSP_NONCE__", nonce)
    response = HTMLResponse(html)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://sdk.minepi.com 'nonce-" + nonce + "'; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' https://socialchain.app; "
        "frame-src 'self' https://pib2bnexus.onrender.com; "
        "frame-ancestors 'self' https://*.pinet.com https://*.minepi.com; "
        "base-uri 'self'; object-src 'none'"
    )
    if "X-Frame-Options" in response.headers:
        del response.headers["X-Frame-Options"]
    return response


@app.get("/public-config")
def public_config():
    """Only non-secret payment settings are exposed to the Pi login page."""
    return {
        "payments_enabled": bool(PI_API_KEY and PI_PAYMENT_AMOUNT > 0),
        "payment_amount": PI_PAYMENT_AMOUNT,
        "payment_memo": PI_PAYMENT_MEMO,
        "sandbox": PI_SANDBOX,
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "sandbox": PI_SANDBOX,
        "auth_provider": "Pi Platform API",
        "payments_configured": bool(
            PI_API_KEY and PI_PAYMENT_AMOUNT > 0
        )
    }


@app.get("/auth/session")
def get_session(authorization: str | None = Header(default=None)):
    """Return the verified identity for an existing signed application session."""
    return {"ok": True, "user": verified_app_user(authorization)}


@app.post("/auth/login")
def login(body: AuthBody):
    """Exchange the Pi SDK access token with Pi App Studio and trust only its identity."""
    try:
        response = requests.post(
            PI_APP_STUDIO_LOGIN_URL,
            headers={"Content-Type": "application/json"},
            json={"accessToken": body.accessToken},
            timeout=20
        )
    except requests.RequestException:
        raise HTTPException(
            502,
            "Could not connect to Pi App Studio to verify your Pioneer account."
        )

    if response.status_code == 401:
        raise HTTPException(401, "Pi access token is invalid or expired. Please sign in again.")
    if response.status_code != 200:
        raise HTTPException(
            502,
            "Pi App Studio could not verify this sign-in. Please try again."
        )

    try:
        verified = response.json()
        session_token = verified.get("sessionToken")
        user = verified.get("user") or {}
        uid = user.get("uid")
        username = user.get("username")
    except (ValueError, AttributeError):
        raise HTTPException(502, "Pi App Studio returned an invalid identity response.")

    if not session_token or not uid or not username:
        raise HTTPException(401, "Pi App Studio did not return a verified Pioneer identity.")

    own_session = issue_app_session(str(uid), str(username))
    return {
        "ok": True,
        "app_session_token": own_session,
        "user": {"uid": str(uid), "username": str(username)}
    }

def verify_payment_belongs_to_user(
    payment_id: str,
    uid: str
):
    response = pi_api(
        "GET",
        f"/payments/{payment_id}"
    )

    if response.status_code != 200:
        raise HTTPException(
            400,
            "Payment not found in Pi Platform."
        )

    payment = response.json()

    if payment.get("user_uid") != uid:
        raise HTTPException(
            403,
            "Payment owner could not be verified for this Pioneer."
        )

    if PI_PAYMENT_AMOUNT <= 0:
        raise HTTPException(
            503,
            "Set PI_PAYMENT_AMOUNT on the backend before enabling payments."
        )

    if float(payment.get("amount", -1)) != PI_PAYMENT_AMOUNT:
        raise HTTPException(
            400,
            "Payment amount does not match the server-configured amount."
        )

    if payment.get("memo") != PI_PAYMENT_MEMO:
        raise HTTPException(
            400,
            "Payment memo does not match the server configuration."
        )

    return payment


@app.post("/payments/approve")
def approve_payment(
    body: PaymentBody,
    authorization: str | None = Header(default=None)
):
    user = verified_app_user(authorization)

    verify_payment_belongs_to_user(
        body.paymentId,
        user["uid"]
    )

    response = pi_api(
        "POST",
        f"/payments/{body.paymentId}/approve"
    )

    if response.status_code not in (200, 201):
        raise HTTPException(
            response.status_code,
            "Pi payment approval failed."
        )

    return response.json()


@app.post("/payments/complete")
def complete_payment(
    body: PaymentBody,
    authorization: str | None = Header(default=None)
):
    if not body.txid:
        raise HTTPException(
            400,
            "Pi transaction ID is required."
        )

    user = verified_app_user(authorization)

    verify_payment_belongs_to_user(
        body.paymentId,
        user["uid"]
    )

    response = pi_api(
        "POST",
        f"/payments/{body.paymentId}/complete",
        payload={
            "txid": body.txid
        }
    )

    if response.status_code not in (200, 201):
        raise HTTPException(
            response.status_code,
            "Pi payment completion failed."
        )

    result = response.json()

    status = result.get("status") or {}
    transaction = result.get("transaction") or {}

    if (
        not status.get("developer_completed")
        or not status.get("transaction_verified")
        or not transaction.get("verified")
    ):
        raise HTTPException(
            409,
            "Pi Platform has not confirmed transaction completion."
        )

    # This demo endpoint does not mark POS sales or inventory as paid.
    return {
        "ok": True,
        "payment": result
    }


@app.get("/health/supabase")
def supabase_health():
    """Check server-side database connectivity without exposing credentials or data."""
    db = get_supabase()
    try:
        result = db.table("nexus_shops").select("id", count="exact").limit(1).execute()
        return {"ok": True, "connected": True, "sample_query_count": result.count}
    except Exception:
        raise HTTPException(503, "Supabase is configured but the schema is not ready or the query failed.")


@app.get("/api/me")
def api_me(authorization: str | None = Header(default=None)):
    """Resolve the signed Pi identity to database records; never trust a browser-supplied UID."""
    user = verified_app_user(authorization)
    db = get_supabase()
    try:
        customer = db.table("nexus_customers").select("id,pi_uid,pi_username,display_name,home_shop_id").eq("pi_uid", user["uid"]).limit(1).execute().data
        dealer = db.table("nexus_dealers").select("id,dealer_code,business_name,shop_id").eq("pi_uid", user["uid"]).limit(1).execute().data
        shops = db.table("nexus_shops").select("id,shop_code,shop_name,shop_category").eq("owner_pi_uid", user["uid"]).execute().data
        return {"ok": True, "user": user, "customer": customer[0] if customer else None,
                "dealer": dealer[0] if dealer else None, "owned_shops": shops}
    except Exception:
        raise HTTPException(503, "Could not load the signed-in user's database profile.")


@app.get("/api/shops")
def api_shops():
    """Return only the curated sample shop directory; private business records stay protected."""
    db = get_supabase()
    try:
        rows = db.table("nexus_shops").select("id,shop_code,shop_name,shop_category,address").eq("is_sample", True).order("shop_name").execute().data
        return {"ok": True, "shops": rows}
    except Exception:
        raise HTTPException(503, "Shop directory is unavailable; check that Supabase migrations have been applied.")


@app.get("/api/shops/{shop_id}/summary")
def api_shop_summary(shop_id: str, authorization: str | None = Header(default=None)):
    """Shop/dealer data is returned only when the verified Pi UID owns the shop or its dealer account."""
    user = verified_app_user(authorization)
    db = get_supabase()
    try:
        shop = db.table("nexus_shops").select("id,shop_code,shop_name,shop_category,owner_pi_uid").eq("id", shop_id).limit(1).execute().data
        if not shop:
            raise HTTPException(404, "Shop not found.")
        owned = shop[0].get("owner_pi_uid") == user["uid"]
        dealer_rows = db.table("nexus_dealers").select("id,dealer_code,business_name").eq("shop_id", shop_id).eq("pi_uid", user["uid"]).execute().data
        if not owned and not dealer_rows:
            raise HTTPException(403, "This Pi account is not linked to this shop or its dealer accounts.")
        sales = db.table("nexus_sales").select("id,receipt_no,total,payment_status,sold_at").eq("shop_id", shop_id).order("sold_at", desc=True).limit(100).execute().data if owned else []
        products = db.table("nexus_products").select("id,sku,product_name,category,wholesale_price,retail_price").eq("shop_id", shop_id).limit(500).execute().data
        return {"ok": True, "shop": {k:v for k,v in shop[0].items() if k != "owner_pi_uid"},
                "dealer_accounts": dealer_rows, "products": products, "recent_sales": sales}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Could not load authorized shop data.")
