import streamlit as st
import streamlit.components.v1 as components
import database
from customer_tabs import promotions
from customer_tabs import history
from customer_tabs import pay


def render_page():
    st.title(f"👤 C2B Customer Portal (Pi Wallet Connected)")
    st.markdown(f"**Welcome back, {st.session_state.username}!** Explore your personalized promotions, scan bills, and track your decentralized multi-tier rewards.")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📢 Promotions & New Arrivals", 
        "💳 Pay From Pi (QR Scan)", 
        "📜 Transaction History", 
        "🪙 Referral & Affiliate (Level 3)"
    ])
    
    # --- TAB 1: Personalized Promotions & New Arrivals ---
    with tab1:
    
     promotions.render_customer_promotions_tab()




    # --- TAB 2: Pay From Pi (QR Scan) ---
    with tab2:
        pay.render_pay_from_pi_tab()


        
        
        if 'customer_pay_scanner' not in st.session_state:
            st.session_state.customer_pay_scanner = False
            
        col_cp1, col_cp2 = st.columns(2)
        with col_cp1:
            if not st.session_state.customer_pay_scanner:
                if st.button("📷 Open Payment Scanner", type="primary"):
                    st.session_state.customer_pay_scanner = True
                    st.rerun()
        with col_cp2:
            if st.session_state.customer_pay_scanner:
                if st.button("❌ Close Payment Scanner", type="secondary"):
                    st.session_state.customer_pay_scanner = False
                    st.rerun()
                
        if st.session_state.customer_pay_scanner:
            customer_scanner_html = """
            <div style="width: 100%; max-width: 400px; margin: auto; text-align: center;">
                <div style="width: 100%; height: 260px; border: 3px solid #00E676; border-radius: 12px; background: #000;" id="customer-pay-reader"></div>
            </div>
            <audio id="beep-sound" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>
            <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
            <script>
            function onCustomerScanSuccess(decodedText) {
                var audio = document.getElementById('beep-sound');
                if(audio) { audio.play(); }
                const inputField = window.parent.document.querySelector('input[aria-label="Scanned Shop Bill Data"]');
                if (inputField) {
                    inputField.value = decodedText;
                    inputField.dispatchEvent(new Event('input', { bubbles: true }));
                }
                document.getElementById('customer-pay-result').innerHTML = "<b style='color:green; font-size:18px;'>✅ Bill Scanned: " + decodedText + "</b>";
            }
            let html5CustomerQrCode = new Html5Qrcode("customer-pay-reader");
            html5CustomerQrCode.start({ facingMode: "environment" }, { fps: 15, qrbox: { width: 220, height: 220 }, experimentalFeatures: { useBarCodeDetectorIfSupported: true } }, onCustomerScanSuccess).catch(err => {});
            </script>
            <div id="customer-pay-result" style="text-align: center; margin-top: 10px; color: green; font-weight: bold;"></div>
            """
            components.html(customer_scanner_html, height=320)
            
        scanned_bill_input = st.text_input("Scanned Shop Bill Data", placeholder="Shop QR bill details appear here after scanning...")
        if scanned_bill_input:
            st.success(f"Bill verified for Shop Data: {scanned_bill_input}")
            payment_amount = st.number_input("Enter Pi / LKR Payment Amount", min_value=0.0, value=1500.0)
            st.warning("QR preview only. Do not treat this as a completed Pi payment. Use the verified Pi Wallet payment flow; POS order settlement is not yet connected to this demo payment component.")



    # --- TAB 3: Transaction History ---
    with tab3:
      history.render_transaction_history_tab()





    # --- TAB 4: Referral & Affiliate (Level 3) ---
    with tab4:
        st.markdown("### 🪙 Referral & Affiliate Program (Level 3 Active)")
        st.success("Your decentralized Level 3 referral tree is active. You earn automated commissions from multi-tier connections.")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Level 1 (0.5%)", "8.20 Pi")
        with col_m2:
            st.metric("Level 2 (0.3%)", "4.10 Pi")
        with col_m3:
            st.metric("Level 3 (0.2%)", "2.20 Pi")
            
        st.markdown("---")
        st.markdown("#### 🔗 Your Unique Referral Link")
        st.code(f"https://pipos.network/invite?ref={st.session_state.username}", language="text")
        st.write("Share this link with other customers or shop owners to expand your Level 3 earning network.")