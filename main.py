import os
import streamlit as st
from pi_integration import render_pi_component

st.set_page_config(page_title="PiPOS B2B2C Platform", page_icon="🛍️", layout="wide")

for key, default in {
    "user_role": "Customer",
    "pi_authenticated": False,
    "username": "",
    "pi_uid": "",
    "pi_access_token": "",
    "cart": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.sidebar.title("PiPOS Ecosystem")
st.sidebar.markdown("---")

backend_url = os.getenv("PI_BACKEND_URL", "").rstrip("/")
sandbox = os.getenv("PI_SANDBOX", "true").lower() == "true"
payment_amount = float(os.getenv("PI_PAYMENT_AMOUNT", "0"))
payment_memo = os.getenv("PI_PAYMENT_MEMO", "PIB2BNexus demo payment")
payment_enabled = bool(backend_url and payment_amount > 0)

if not st.session_state.pi_authenticated:
    st.sidebar.warning("🔒 Sign in with Pi Network")
    if not backend_url:
        st.sidebar.error("PI_BACKEND_URL is missing from Render Environment Variables.")
    result = render_pi_component(
        backend_url=backend_url,
        sandbox=sandbox,
        payment_enabled=False,
    )
    if isinstance(result, dict) and result.get("verified") and result.get("auth_token"):
        # Token is kept only in Streamlit server session memory, never in Supabase.
        st.session_state.pi_authenticated = True
        st.session_state.pi_access_token = result["auth_token"]
        st.session_state.pi_uid = result["uid"]
        st.session_state.username = result["username"]
        st.success(f"Welcome, {st.session_state.username}!")
        st.rerun()
else:
    st.sidebar.success(f"🟢 Verified Pioneer: {st.session_state.username}")
    role_choice = st.sidebar.selectbox("Switch Role", ["Customer", "Shop Owner", "Dealer"])
    if role_choice != st.session_state.user_role:
        st.session_state.user_role = role_choice
        st.rerun()

    if st.sidebar.button("Sign Out"):
        for key in ("pi_authenticated", "pi_access_token", "pi_uid", "username"):
            st.session_state[key] = False if key == "pi_authenticated" else ""
        st.session_state.user_role = "Customer"
        st.session_state.cart = []
        st.rerun()

if not st.session_state.pi_authenticated:
    st.title("🌍 Welcome to PiPOS – B2B2C Platform")
    st.markdown("### A paperless business ecosystem powered by Pi Network.")
    st.info("Open PIB2BNexus in Pi Browser and use the Sign in with Pi button.")
else:
    # Optional Pi payment test panel. Amount and memo are server-configured.
    with st.expander("π Pi Wallet – configured payment test"):
        if not payment_enabled:
            st.warning("Pi payments are disabled until PI_PAYMENT_AMOUNT is configured on Render.")
        pay_result = render_pi_component(
            backend_url=backend_url,
            sandbox=sandbox,
            access_token=st.session_state.pi_access_token,
            payment_enabled=payment_enabled,
            payment_amount=payment_amount,
            payment_memo=payment_memo,
        )
        if isinstance(pay_result, dict) and pay_result.get("payment_verified"):
            st.success("Pi Platform confirmed the payment completion.")

    role = st.session_state.user_role
    if role == "Customer":
        import customer
        customer.render_page()
    elif role == "Shop Owner":
        import shop
        shop.render_page()
    elif role == "Dealer":
        import dealer
        dealer.render_page()

# ==========================================
# PiPOS Footer - Privacy Policy & Terms Links
# ==========================================
st.markdown("---")

# ෆයිල් වලින් ඩේටා කියවා ගැනීම
try:
    with open("privacy.txt", "r", encoding="utf-8") as f:
        privacy_content = f.read()
except FileNotFoundError:
    privacy_content = "Privacy policy file not found."

try:
    with open("terms.txt", "r", encoding="utf-8") as f:
        terms_content = f.read()
except FileNotFoundError:
    terms_content = "Terms of service file not found."

# Expander එකක් හරහා පරිශීලකයාට පහසුවෙන් කියවා බැලීමට සැලැස්වීම
with st.expander("📄 Click here to view full Privacy Policy & Terms of Service"):
    
    # ටැබ් දෙකකට වෙන් කර පෙන්වීම (පැහැදිලිව බලාගැනීමට)
    tab1, tab2 = st.tabs(["🔒 Privacy Policy", "📜 Terms of Service"])
    
    with tab1:
        st.markdown(privacy_content)
        
    with tab2:
        st.markdown(terms_content)
