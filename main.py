import os
import streamlit as st
import streamlit.components.v1 as components
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

# Securely receive the one-time Pi app session from the top-level page.
# The parent and this Streamlit document share the registered app origin.
st.components.v1.html(
    """
    <script>
    (function () {
      const parentWindow = window.parent;
      const handler = async function (event) {
        if (event.origin !== parentWindow.location.origin ||
            event.source !== parentWindow ||
            !event.data || event.data.type !== "PIB2B_PI_SESSION") return;
        const token = event.data.token;
        if (!token || typeof token !== "string") return;
        try {
          const response = await fetch(
            "" + "https://pib2bnexus-pi-backend.onrender.com/auth/session",
            {headers: {"Authorization": "Bearer " + token}}
          );
          const result = await response.json();
          if (!response.ok || !result.user) throw new Error("Session verification failed.");
          parentWindow.postMessage(
            {type:"PIB2B_PI_SESSION_ACCEPTED", token:token, user:result.user},
            event.origin
          );
          window.removeEventListener("message", handler);
        } catch (error) {
          console.error("Pi session handoff failed", error);
        }
      };
      window.addEventListener("message", handler);
    })();
    </script>
    """,
    height=0,
)

# Receive the short-lived, signed app session handed off by the top-level
# Pi SDK page. The token is issued only after the FastAPI backend verifies
# the Pi access token against the Platform API.
# Read the one-time login handoff from the URL fragment via a small
# Streamlit component. Fragments are not sent to the web server in HTTP requests.
_fragment_reader = components.html(
    """
    <script>
    (function(){
      const match = window.parent.location.hash.match(/(?:^#|&)pi_session=([^&]+)/);
      if (match) {
        const token = decodeURIComponent(match[1]);
        window.parent.history.replaceState(null, "", window.parent.location.pathname);
        window.parent.postMessage({type:"PIB2B_PI_SESSION", token:token}, window.parent.location.origin);
      }
    })();
    </script>
    """,
    height=0,
)

payment_amount = float(os.getenv("PI_PAYMENT_AMOUNT", "0"))
payment_memo = os.getenv("PI_PAYMENT_MEMO", "PIB2BNexus demo payment")
payment_enabled = bool(backend_url and payment_amount > 0)

if not st.session_state.pi_authenticated:
    st.sidebar.warning("🔒 Sign in with Pi Network")
    login_url = os.getenv("PI_LOGIN_URL", "https://pib2bnexus.com")
    st.sidebar.link_button("Sign in with Pi", login_url, use_container_width=True)

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
    # Optional Pi payment test panel. Amount and memo are server-configured.
    with st.expander("π Pi Wallet – configured payment test"):
        if not payment_enabled:
            st.warning("Pi payments are disabled until PI_PAYMENT_AMOUNT is configured on Render.")
        pay_result = render_pi_component(
            backend_url=backend_url,
            app_session_token=st.session_state.pi_app_session_token,
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
