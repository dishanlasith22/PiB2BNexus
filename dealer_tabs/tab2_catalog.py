import streamlit as st
import streamlit.components.v1 as components
import database

def render():
    st.markdown("### 📋 Dealer Catalog & Add Items")
    st.info("Scan item barcodes or enter product details manually to add them to your wholesale master catalog.")
    
    # 1. Scanner Toggle State
    if 'dealer_cat_scanner' not in st.session_state:
        st.session_state.dealer_cat_scanner = False
        
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if not st.session_state.dealer_cat_scanner:
            if st.button("📷 Open Barcode/QR Scanner", type="primary"):
                st.session_state.dealer_cat_scanner = True
                st.rerun()
    with col_b2:
        if st.session_state.dealer_cat_scanner:
            if st.button("❌ Close Scanner", type="secondary"):
                st.session_state.dealer_cat_scanner = False
                st.rerun()
                
    # 2. HTML5 Camera Scanner Component
    if st.session_state.dealer_cat_scanner:
        scanner_html = """
        <div style="width: 100%; max-width: 400px; margin: auto; text-align: center;">
            <div style="width: 100%; height: 250px; border: 3px solid #2979FF; border-radius: 12px; background: #000;" id="catalog-scanner-reader"></div>
        </div>
        <audio id="beep-sound" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>
        <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
        <script>
        function onScanSuccess(decodedText) {
            var audio = document.getElementById('beep-sound');
            if(audio) { audio.play(); }
            const inputField = window.parent.document.querySelector('input[aria-label="Bar Code Input Area"]');
            if (inputField) {
                inputField.value = decodedText;
                inputField.dispatchEvent(new Event('input', { bubbles: true }));
            }
            document.getElementById('scan-result').innerHTML = "<b style='color:green; font-size:16px;'>✅ Scanned: " + decodedText + "</b>";
        }
        let html5QrCode = new Html5Qrcode("catalog-scanner-reader");
        html5QrCode.start({ facingMode: "environment" }, { fps: 15, qrbox: { width: 200, height: 200 } }, onScanSuccess).catch(err => {});
        </script>
        <div id="scan-result" style="text-align: center; margin-top: 8px; color: green; font-weight: bold;"></div>
        """
        components.html(scanner_html, height=300)

    # 3. Add Item Form (আপনার স্কেච් එකේ ඇති අංශ පරිදි)
    with st.form("catalog_add_form"):
        st.markdown("#### ✍️ Product Details Entry")
        
        scanned_barcode = st.text_input("Bar Code Input Area", placeholder="Scan or type barcode here...")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            item_name = st.text_input("භාණ්ඩයේ නම (Good Name)", placeholder="e.g., Cinnamon Export Grade (100g)")
        with col_f2:
            selling_price = st.number_input("මිල / Price (Rs.)", min_value=0.0, value=100.0, step=10.0)
            
        buying_price = st.number_input("Buying / Wholesale Price (Rs.)", min_value=0.0, value=80.0, step=10.0)
        stock_qty = st.number_input("Initial Stock Quantity", min_value=1, value=50)
        
        submitted = st.form_submit_button("➕ Add Item to Catalog", type="primary")
        if submitted:
            if scanned_barcode and item_name:
                current_dealer = st.session_state.get("username", "dealer_01")
                success, msg = database.register_product(
                    current_dealer, scanned_barcode, item_name, buying_price, selling_price, stock_qty
                )
                if success:
                    st.success(f"✅ Successfully added **{item_name}** to master catalog!")
                else:
                    st.error(f"Error: {msg}")
            else:
                st.warning("⚠️ Please provide both Barcode and Good Name.")

    # 4. Registered Catalog Table View (දැනට ලොග් වී සිටින ඩීලර්ට අදාළ අයිතම පමණක් පෙන්වීම)
    st.markdown("---")
    st.markdown("### 📊 Existing Master Catalog Items")
    
    try:
        current_dealer = st.session_state.get("username", "dealer_01")
        catalog_items = database.fetch_dealer_products(current_dealer)
        
        if catalog_items and len(catalog_items) > 0:
            st.table(catalog_items)
        else:
            st.info("No items registered in your catalog yet.")
    except Exception as e:
        st.info("Catalog items will appear here once added.")