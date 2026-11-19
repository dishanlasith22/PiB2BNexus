
"""PIB2BNexus FastAPI backend using the official Pi Platform API.

Pi SDK access tokens are verified server-side with GET /v2/me. Only the
identity returned by Pi Platform is trusted. A short-lived HMAC app session is
issued after verification. Pi Server API key is used only for payment operations.
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
    """Verify the Pi SDK access token directly with the official Pi Platform API /me endpoint."""
    try:
        response = requests.get(
            PI_API_BASE + "/me",
            headers={"Authorization": f"Bearer {body.accessToken}"},
            timeout=20
        )
    except requests.RequestException:
        raise HTTPException(
            502,
            "Could not connect to Pi Platform API to verify your Pioneer account."
        )

    if response.status_code == 401:
        raise HTTPException(401, "Pi access token is invalid or expired. Please sign in again.")
    if response.status_code != 200:
        raise HTTPException(502, "Pi Platform API could not verify this sign-in. Please try again.")

    try:
        user = response.json()
        uid = user.get("uid")
        username = user.get("username")
    except (ValueError, AttributeError):
        raise HTTPException(502, "Pi Platform API returned an invalid identity response.")

    if not uid or not username:
        raise HTTPException(401, "Pi Platform API did not return the required Pioneer identity.")

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


# Workspace data API. Every request is scoped to the Pi UID verified in the signed app session.
from typing import Any
from datetime import date
import uuid

class RegisterBody(BaseModel):
    role: str = Field(pattern="^(shop|dealer|customer)$")
    display_name: str = Field(min_length=2, max_length=120)
    shop_name: str | None = Field(default=None, max_length=160)
    shop_category: str | None = Field(default=None, max_length=80)
    shop_id: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=240)

class SaleLine(BaseModel):
    product_id: str
    quantity: float = Field(gt=0, le=10000)

class SaleCreate(BaseModel):
    branch_id: str
    lines: list[SaleLine] = Field(min_length=1, max_length=100)
    discount: float = Field(default=0, ge=0)
    payment_method: str = Field(default="Cash", pattern="^(Cash|Card|Pi)$")
    payment_status: str = Field(default="pending", pattern="^(pending|paid)$")
    pi_payment_id: str | None = None

RESOURCE_TABLES = {
    "products": ("nexus_products", "shop_id"),
    "inventory": ("nexus_inventory", "branch_id"),
    "branches": ("nexus_branches", "shop_id"),
    "orders": ("nexus_orders", "shop_id"),
    "sales": ("nexus_sales", "shop_id"),
    "promotions": ("nexus_promotions", "shop_id"),
    "settlements": ("nexus_settlements", "dealer_id"),
    "ledger": ("nexus_ledger", "shop_id"),
    "customers": ("nexus_customers", "home_shop_id"),
    "dealers": ("nexus_dealers", "shop_id"),
    "stock_lots": ("nexus_stock_lots", "shop_id"),
    "dealer_transactions": ("nexus_dealer_transactions", "shop_id"),
    "sale_items": ("nexus_sale_items", "dealer_id"),
}

def workspace_identity(authorization: str | None):
    user = verified_app_user(authorization)
    db = get_supabase()
    try:
        shops = db.table("nexus_shops").select("id,shop_name,shop_code").eq("owner_pi_uid", user["uid"]).execute().data
        dealers = db.table("nexus_dealers").select("id,business_name,shop_id,dealer_code").eq("pi_uid", user["uid"]).execute().data
        customers = db.table("nexus_customers").select("id,home_shop_id,pi_username").eq("pi_uid", user["uid"]).execute().data
    except Exception:
        raise HTTPException(503, "Could not resolve the Pi account workspace.")
    roles = []
    if shops: roles.append("shop")
    if dealers: roles.append("dealer")
    if customers: roles.append("customer")
    return db, user, {"roles": roles, "shops": shops, "dealers": dealers, "customers": customers}

@app.post("/api/register")
def register_workspace(body: RegisterBody, authorization: str | None = Header(default=None)):
    db, user, identity = workspace_identity(authorization)
    if body.role in identity["roles"]:
        return {"ok": True, "identity": identity, "message": "This role is already registered."}
    try:
        if body.role == "shop":
            if not body.shop_name or not body.shop_category:
                raise HTTPException(400, "Shop name and category are required.")
            code = "PI-SHOP-" + uuid.uuid4().hex[:10].upper()
            shop = db.table("nexus_shops").insert({
                "shop_code": code, "shop_name": body.shop_name, "shop_category": body.shop_category,
                "owner_pi_uid": user["uid"], "phone": body.phone, "address": body.address
            }).execute().data[0]
            db.table("nexus_branches").insert({
                "shop_id": shop["id"], "branch_code": code + "-MAIN",
                "branch_name": "Main Branch", "address": body.address
            }).execute()
        elif body.role == "dealer":
            if not body.shop_id:
                raise HTTPException(400, "Choose the shop you supply.")
            db.table("nexus_shops").select("id").eq("id", body.shop_id).single().execute()
            db.table("nexus_dealers").insert({
                "dealer_code": "PI-DL-" + uuid.uuid4().hex[:10].upper(),
                "business_name": body.display_name, "pi_uid": user["uid"],
                "shop_id": body.shop_id, "phone": body.phone, "address": body.address
            }).execute()
        else:
            home_shop = body.shop_id
            if not home_shop:
                raise HTTPException(400, "Choose your preferred shop.")
            db.table("nexus_customers").insert({
                "pi_uid": user["uid"], "pi_username": user["username"],
                "display_name": body.display_name, "home_shop_id": home_shop, "phone": body.phone
            }).execute()
        _, _, updated = workspace_identity(authorization)
        return {"ok": True, "identity": updated}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Registration could not be saved. Check required fields and try again.")

@app.get("/api/workspace")
def get_workspace(authorization: str | None = Header(default=None)):
    db, user, identity = workspace_identity(authorization)
    return {"ok": True, "user": user, "identity": identity}

@app.get("/api/data/{resource}")
def list_workspace_data(resource: str, authorization: str | None = Header(default=None), limit: int = 100):
    if resource not in RESOURCE_TABLES:
        raise HTTPException(404, "Unknown workspace resource.")
    db, user, identity = workspace_identity(authorization)
    table, scope = RESOURCE_TABLES[resource]
    limit = max(1, min(limit, 500))
    try:
        query = db.table(table).select("*")
        if resource == "branches":
            if not identity["shops"]: raise HTTPException(403, "Shop owner access required.")
            query = query.in_("shop_id", [x["id"] for x in identity["shops"]])
        elif resource == "products":
            shop_ids = [x["id"] for x in identity["shops"]] + [x["shop_id"] for x in identity["dealers"]]
            if not shop_ids: raise HTTPException(403, "Shop or dealer access required.")
            query = query.in_("shop_id", list(set(shop_ids)))
        elif resource == "sales" and identity["customers"]:
            query = query.in_("customer_id", [x["id"] for x in identity["customers"]])
        elif resource == "promotions" and identity["customers"] and not identity["shops"] and not identity["dealers"]:
            query = query.eq("status", "active").gte("ends_at", date.today().isoformat())
        elif resource in ("inventory","orders","sales","promotions","ledger","stock_lots","dealer_transactions"):
            shop_ids = [x["id"] for x in identity["shops"]] + [x["shop_id"] for x in identity["dealers"]]
            if not shop_ids: raise HTTPException(403, "Shop or dealer access required.")
            query = query.in_("shop_id", list(set(shop_ids)))
        elif resource in ("settlements","sale_items"):
            dealer_ids = [x["id"] for x in identity["dealers"]]
            if not dealer_ids: raise HTTPException(403, "Dealer access required.")
            query = query.in_("dealer_id", dealer_ids)
        elif resource == "customers":
            if not identity["shops"]: raise HTTPException(403, "Shop owner access required.")
            query = query.in_("home_shop_id", [x["id"] for x in identity["shops"]])
        elif resource == "dealers":
            shop_ids = [x["id"] for x in identity["shops"]]
            dealer_ids = [x["id"] for x in identity["dealers"]]
            if shop_ids: query = query.in_("shop_id", shop_ids)
            elif dealer_ids: query = query.in_("id", dealer_ids)
            else: raise HTTPException(403, "Shop or dealer access required.")
        result = query.order("created_at", desc=True).limit(limit).execute()
        return {"ok": True, "items": result.data}
    except HTTPException:
        raise
    except Exception:
        # Some ledger tables use event timestamps rather than created_at.
        try:
            query = db.table(table).select("*")
            if scope == "shop_id":
                ids = [x["id"] for x in identity["shops"]] + [x["shop_id"] for x in identity["dealers"]]
                query = query.in_(scope, list(set(ids)))
            elif scope == "dealer_id":
                query = query.in_(scope, [x["id"] for x in identity["dealers"]])
            else:
                raise HTTPException(403, "This resource is not available to this role.")
            return {"ok": True, "items": query.limit(limit).execute().data}
        except HTTPException: raise
        except Exception: raise HTTPException(503, "Could not load workspace data. Confirm the database migrations are installed.")

@app.post("/api/sales")
def create_sale(body: SaleCreate, authorization: str | None = Header(default=None)):
    db, user, identity = workspace_identity(authorization)
    if not identity["shops"]:
        raise HTTPException(403, "Only a registered shop owner can create POS sales.")
    shop_ids = [x["id"] for x in identity["shops"]]
    try:
        branch = db.table("nexus_branches").select("id,shop_id").eq("id", body.branch_id).in_("shop_id", shop_ids).single().execute().data
        product_ids = [line.product_id for line in body.lines]
        products = db.table("nexus_products").select("id,shop_id,product_name,retail_price,wholesale_price,dealer_id").in_("id", product_ids).in_("shop_id", shop_ids).execute().data
        by_id = {p["id"]: p for p in products}
        if len(by_id) != len(set(product_ids)):
            raise HTTPException(400, "One or more products do not belong to this shop.")
        items = []
        subtotal = 0.0
        for line in body.lines:
            p = by_id[line.product_id]
            inv = db.table("nexus_inventory").select("quantity").eq("branch_id", body.branch_id).eq("product_id", line.product_id).single().execute().data
            if float(inv["quantity"]) < line.quantity:
                raise HTTPException(409, f"Insufficient stock for {p['product_name']}.")
            price = float(p["retail_price"])
            subtotal += price * line.quantity
            items.append({"product_id": p["id"], "dealer_id": p.get("dealer_id"), "quantity": line.quantity,
                          "unit_price": price, "unit_cost_snapshot": float(p["wholesale_price"]),
                          "line_total": round(price * line.quantity, 4)})
        if body.discount > subtotal:
            raise HTTPException(400, "Discount cannot exceed subtotal.")
        total = round(subtotal - body.discount, 4)
        receipt = "PIB-" + uuid.uuid4().hex[:12].upper()
        sale = db.table("nexus_sales").insert({
            "receipt_no": receipt, "shop_id": branch["shop_id"], "branch_id": branch["id"],
            "subtotal": subtotal, "discount": body.discount, "total": total,
            "payment_method": body.payment_method, "payment_status": body.payment_status,
            "pi_payment_id": body.pi_payment_id, "created_by": user["uid"]
        }).execute().data[0]
        for item in items:
            item["sale_id"] = sale["id"]
        db.table("nexus_sale_items").insert(items).execute()
        for item in items:
            inv = db.table("nexus_inventory").select("id,quantity").eq("branch_id", body.branch_id).eq("product_id", item["product_id"]).single().execute().data
            db.table("nexus_inventory").update({"quantity": float(inv["quantity"]) - item["quantity"]}).eq("id", inv["id"]).execute()
            db.table("nexus_ledger").insert({
                "event_key": "SALE-" + sale["id"] + "-" + item["product_id"],
                "event_type": "sale", "shop_id": branch["shop_id"], "branch_id": branch["id"],
                "dealer_id": item["dealer_id"], "product_id": item["product_id"],
                "quantity_delta": -item["quantity"], "unit_cost": item["unit_cost_snapshot"],
                "reference_type": "sale", "reference_id": sale["id"]
            }).execute()
        return {"ok": True, "sale": sale, "items": items}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Sale could not be saved. Inventory may have changed; refresh and retry.")



class DataWrite(BaseModel):
    data: dict[str, Any]

class DataUpdate(BaseModel):
    data: dict[str, Any]

WRITE_FIELDS = {
    "products": {"sku","barcode","product_name","category","unit","wholesale_price","retail_price","image_url","is_active","dealer_id"},
    "promotions": {"product_id","title","description","image_url","original_price","offer_price","starts_at","ends_at","status"},
    "orders": {"order_no","dealer_id","branch_id","status","total_cost"},
    "branches": {"branch_code","branch_name","address"},
}

@app.post("/api/data/{resource}")
def create_workspace_record(resource: str, body: DataWrite, authorization: str | None = Header(default=None)):
    if resource not in WRITE_FIELDS:
        raise HTTPException(404, "This resource cannot be created through this endpoint.")
    db, user, identity = workspace_identity(authorization)
    if not identity["shops"]:
        raise HTTPException(403, "Only registered shop owners can create these records.")
    shop = identity["shops"][0]
    payload = {k:v for k,v in body.data.items() if k in WRITE_FIELDS[resource]}
    try:
        if resource == "products":
            if not payload.get("sku") or not payload.get("product_name") or not payload.get("category"):
                raise HTTPException(400, "SKU, product name and category are required.")
            if payload.get("dealer_id"):
                if payload["dealer_id"] not in [d["id"] for d in db.table("nexus_dealers").select("id").eq("shop_id",shop["id"]).execute().data]:
                    raise HTTPException(403, "Dealer does not belong to this shop.")
            payload["shop_id"] = shop["id"]
        elif resource == "promotions":
            if not payload.get("title") or not payload.get("image_url") or not payload.get("offer_price") or not payload.get("starts_at") or not payload.get("ends_at"):
                raise HTTPException(400, "Title, image, offer price and campaign dates are required.")
            payload["shop_id"] = shop["id"]
        elif resource == "orders":
            if not payload.get("order_no") or not payload.get("dealer_id"):
                raise HTTPException(400, "Order number and dealer are required.")
            dealer = db.table("nexus_dealers").select("id").eq("id",payload["dealer_id"]).eq("shop_id",shop["id"]).single().execute().data
            payload.update({"shop_id":shop["id"],"status":"requested"})
        elif resource == "branches":
            if not payload.get("branch_code") or not payload.get("branch_name"):
                raise HTTPException(400, "Branch code and name are required.")
            payload["shop_id"] = shop["id"]
        result = db.table(RESOURCE_TABLES[resource][0]).insert(payload).execute()
        return {"ok":True,"item":result.data[0]}
    except HTTPException: raise
    except Exception: raise HTTPException(400, "Record could not be created. Check duplicate codes, required fields and database schema.")

@app.patch("/api/data/{resource}/{record_id}")
def update_workspace_record(resource: str, record_id: str, body: DataUpdate, authorization: str | None = Header(default=None)):
    if resource not in ("products","promotions","orders","branches"):
        raise HTTPException(404, "This resource cannot be updated.")
    db, user, identity = workspace_identity(authorization)
    if not identity["shops"]:
        raise HTTPException(403, "Shop owner access required.")
    fields = WRITE_FIELDS[resource] - ({"dealer_id"} if resource != "orders" else set())
    payload = {k:v for k,v in body.data.items() if k in fields}
    if not payload:
        raise HTTPException(400, "No supported fields supplied.")
    table = RESOURCE_TABLES[resource][0]
    try:
        result = db.table(table).update(payload).eq("id",record_id).eq("shop_id",identity["shops"][0]["id"]).execute()
        if not result.data: raise HTTPException(404, "Record not found in this shop.")
        return {"ok":True,"item":result.data[0]}
    except HTTPException: raise
    except Exception: raise HTTPException(400, "Update failed. Check the supplied values.")
