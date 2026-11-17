import os
import streamlit as st
from pi_integration import render_pi_component

st.set_page_config(page_title="PiPOS B2B2C Platform", page_icon="🛍️", layout="wide")

for key, default in {
    "user_role": "Customer",
    "pi_authenticated": False,
    "username": "",
    "pi_uid": "",
    "pi_app_session_token": "",
    "cart": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.sidebar.title("PiPOS Ecosystem")
st.sidebar.markdown("---")

backend_url = os.getenv("PI_BACKEND_URL", "").rstrip("/")

payment_amount = float(os.getenv("PI_PAYMENT_AMOUNT", "0"))
payment_memo = os.getenv("PI_PAYMENT_MEMO", "PIB2BNexus demo payment")
payment_enabled = bool(backend_url and payment_amount > 0)

if not st.session_state.pi_authenticated:
    st.sidebar.warning("🔒 Sign in with Pi Network")
    login_url = os.getenv("PI_LOGIN_URL", "https://pib2bnexus-pi-backend.onrender.com")
    st.sidebar.link_button("Sign in with Pi", login_url, use_container_width=True)
    result = render_pi_component(backend_url=backend_url, payment_enabled=False)
    if isinstance(result, dict) and result.get("verified") and result.get("app_session_token"):
        st.session_state.pi_authenticated = True
        st.session_state.pi_app_session_token = result["app_session_token"]
        st.session_state.pi_uid = result["uid"]
        st.session_state.username = result["username"]
        st.rerun()

else:
    st.sidebar.success(f"🟢 Verified Pioneer: {st.session_state.username}")
    role_choice = st.sidebar.selectbox("Switch Role", ["Customer", "Shop Owner", "Dealer"])
    if role_choice != st.session_state.user_role:
        st.session_state.user_role = role_choice
        st.rerun()

    if st.sidebar.button("Sign Out"):
        for key in ("pi_authenticated", "pi_app_session_token", "pi_uid", "username"):
            st.session_state[key] = False if key == "pi_authenticated" else ""
        st.session_state.user_role = "Customer"
        st.session_state.cart = []
        st.rerun()

if not st.session_state.pi_authenticated:
    st.title("🌍 Welcome to PiPOS – B2B2C Platform")
    st.markdown("### A paperless business ecosystem powered by Pi Network.")
    st.info("Open PIB2BNexus in Pi Browser and use the Sign in with Pi button.")
else:
    st.info("Pi test payments are available from the secure Pi login page above the workspace.")

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
