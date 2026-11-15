import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="PiPOS B2B2C Platform", page_icon="🛍️", layout="wide")

if 'user_role' not in st.session_state:
    st.session_state.user_role = 'Customer'
if 'pi_authenticated' not in st.session_state:
    st.session_state.pi_authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'cart' not in st.session_state:
    st.session_state.cart = []

st.sidebar.title("PiPOS Ecosystem")
st.sidebar.markdown("---")

if not st.session_state.pi_authenticated:
    st.sidebar.warning("🔒 Please sign in with Pi Network.")
    
    # Pi Network SDK JavaScript Authentication Component
    pi_auth_html = """
    <div style="text-align: center; font-family: sans-serif; padding: 5px;">
        <button id="pi-signin-btn" style="background-color: #7b1fa2; color: white; padding: 10px 15px; border: none; border-radius: 5px; font-size: 14px; font-weight: bold; cursor: pointer; width: 100%;">
            Sign in with Pi
        </button>
        <p id="pi-status" style="margin-top: 8px; font-size: 12px; color: #555;"></p>
    </div>

    <script src="https://sdk.minepi.com/pi-sdk.js"></script>
    <script>
        const Pi = window.Pi;
        // Sandbox mode true කර ඇත. Mainnet යද්දී false කළ යුතුය.
        Pi.init({ version: "2.0", sandbox: true });

        document.getElementById('pi-signin-btn').onclick = async function() {
            const scopes = ['username', 'payments'];
            
            function onIncompletePaymentFound(payment) {
                console.log("Incomplete payment found:", payment);
            }

            try {
                const auth = await Pi.authenticate(scopes, onIncompletePaymentFound);
                document.getElementById('pi-status').innerText = "Success: " + auth.user.username;
                
                // Streamlit වෙතට username එක යැවීම
                const data = { type: 'streamlit:setComponentValue', value: auth.user.username };
                window.parent.postMessage(data, '*');
            } catch (error) {
                console.error(error);
                document.getElementById('pi-status').innerText = "Auth Failed!";
            }
        };
    </script>
    """
    
    # HTML component එක සයිඩ්බාර් එකේ පෙන්වීම
    pi_logged_username = components.html(pi_auth_html, height=120)
    
    # JavaScript එකෙන් Pi Username එක ලැබުණු පසු Session State යාවත්කාලීන කිරීම
    if pi_logged_username and isinstance(pi_logged_username, str) and len(pi_logged_username) > 0:
        st.session_state.pi_authenticated = True
        st.session_state.username = pi_logged_username.strip()
        st.success(f"Welcome, {st.session_state.username}!")
        st.rerun()

else:
    st.sidebar.success(f"🟢 Connected: {st.session_state.username}")
    role_choice = st.sidebar.selectbox("Switch Role", ["Customer", "Shop Owner ", "Dealer "])
    if role_choice != st.session_state.user_role:
        st.session_state.user_role = role_choice
        st.rerun()
        
    if st.sidebar.button("Sign Out"):
        st.session_state.pi_authenticated = False
        st.session_state.user_role = 'Customer'
        st.session_state.cart = []
        st.rerun()

if not st.session_state.pi_authenticated:
    st.title("🌍 Welcome to PiPOS - World's #1 B2B2C Platform")
    st.markdown("### The ultimate paperless, zero-credit economic ecosystem powered by Pi Network.")
    st.info("👈 Please sign in using your Pi Network credentials on the sidebar to get started.")
else:
    role = st.session_state.user_role
    if role == "Customer":
        import customer
        customer.render_page()
    elif role == "Shop Owner ":
        import shop
        shop.render_page()
    elif role == "Dealer ":
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
