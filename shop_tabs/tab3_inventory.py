import streamlit as st
import cv2
import numpy as np
import database
import pandas as pd
import json
import qrcode
from io import BytesIO
import base64

def render():
    st.markdown("### 📦 Shop Stock In & Dealer QR Scanner (Inventory)")
    
    # 💡 කිසිදු ඩමී වැලියු එකක් නොමැතිව සැබෑ ලොගින් වූ යූසර්වරයා (Session state) හරහා පමණක් දත්ත ලබා ගැනීම
    current_shop_user = st.session_state.get("username")
    
    if not current_shop_user:
        st.error("❌ Error: No active shop user found in session! Please log in again to your shop account.")
        return

    # සැබෑ ඩේටාබේස් එකෙන් අදාළ ෂොප් ප්‍රොފައިල් එක ලබා ගැනීම
    shop_profile = database.get_shop_profile(current_shop_user)
    
    if not shop_profile:
        st.error(f"❌ Error: Shop profile for '{current_shop_user}' could not be found in the database.")
        return

    shop_name = shop_profile.get("shop_name")
    shop_reg_no = shop_profile.get("register_code")

    st.info(f"Logged in Shop: **{shop_name}** (Reg: {shop_reg_no}) | Point your camera at the Dealer QR code to load catalog.")

    # Session State මඟින් ස්කෑන් වූ කෝඩ් එක රඳවා තබා ගැනීම
    if "scanned_dealer_code" not in st.session_state:
        st.session_state.scanned_dealer_code = ""

    # --- 1. DEALER IDENTIFICATION & NATIVE CAMERA QR SCANNER ---
    st.markdown("#### 1. Dealer Identification & QR Scan")
    
    camera_image = st.camera_input("📸 Capture Dealer QR Code via Camera")
    
    scanned_code_from_camera = ""
    if camera_image is not None:
        bytes_data = camera_image.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(cv_img)
        
        if data:
            scanned_code_from_camera = data.strip()
            st.session_state.scanned_dealer_code = scanned_code_from_camera
            st.success(f"✅ QR Code Detected: {scanned_code_from_camera}")
        else:
            st.warning("⚠️ No QR code detected in the captured photo. Please ensure good lighting and try again.")

    st.markdown("---")

    default_input_val = st.session_state.scanned_dealer_code if scanned_code_from_camera == "" else scanned_code_from_camera
    
    scanned_dealer_code = st.text_input(
        "Scanned Dealer Code Input", 
        value=default_input_val, 
        placeholder="Scan QR via camera above or type dealer register code..."
    )

    clean_code = scanned_dealer_code.strip()
    detected_dealer_key = None
    dealer_display_name = ""
    dealer_products_raw = [] # සම්පූර්ණ ප්‍රොඩක්ට් විස්තර (බාර්කෝඩ් සමඟ ලබා ගැනීමට)

    if clean_code:
        dealer_info = database.get_dealer_by_code(clean_code) if hasattr(database, 'get_dealer_by_code') else None
        
        if dealer_info:
            detected_dealer_key = clean_code
            dealer_display_name = dealer_info.get('company_name') or dealer_info.get('pi_username', 'Verified Dealer')
            dealer_pi_username = dealer_info.get('pi_username')
            
            # ඩේටාබේස් එකෙන් ඩීලර්ට අදාළ අයිතමවල සම්පූර්ණ විස්තර ලබා ගැනීම (බාර්කෝඩ් සඳහා)
            if hasattr(database, 'supabase'):
                prod_response = database.supabase.table("products").select("*").eq("dealer_id", dealer_pi_username).execute()
                dealer_products_raw = prod_response.data if prod_response.data else []

    if detected_dealer_key and dealer_display_name:
        st.markdown(f"""
            <div style="background-color: #e8f5e9; padding: 15px; border-radius: 8px; border-left: 6px solid #4CAF50; margin-bottom: 20px;">
                <h2 style="color: #2e7d32; margin: 0;">🏢 Dealer: {dealer_display_name}</h2>
                <p style="margin: 5px 0 0 0; color: #555; font-size: 14px;">Register Code: <b>{detected_dealer_key}</b> | Status: Verified Partner 🟢</p>
            </div>
        """, unsafe_allow_html=True)
        
        current_dealer_name = f"{dealer_display_name} ({detected_dealer_key})"
        
        # අයිතම නාම ලැයිස්තුව සකස් කරගැනීම
        available_items = [p['item_name'] for p in dealer_products_raw] if dealer_products_raw else []
        
        if not available_items:
            st.warning("⚠️ No products found in database for this dealer catalog.")
            available_items = ["No items available in database"]
    else:
        if clean_code:
            st.error("❌ Invalid Dealer Code! This register code does not exist in the database.")
        else:
            st.warning("⚠️ Please capture dealer QR code using the camera above or enter a valid register code to load catalog.")
        current_dealer_name = "Unknown Dealer"
        available_items = ["Please scan valid dealer QR first"]
        dealer_products_raw = []

    st.markdown("---")

    # --- 2. ITEM DETAILS & PRICING SECTION ---
    st.markdown("#### 2. Item Selection & Pricing (Stock In)")
    
    with st.form("stock_in_form"):
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            item_name = st.selectbox("Select Item (Loaded from Database Catalog)", options=available_items)
            buying_price = st.number_input("Buying Price (Unit Price - Rs)", min_value=0.0, value=75.0, step=1.0)
        
        with col_i2:
            qty = st.number_input("Quantity (Qty)", min_value=1, value=50, step=1)
            free_qty = st.number_input("Free Qty (Bonus)", min_value=0, value=0, step=1)
            
        total_amount = buying_price * qty
        st.metric("Total Calculated Amount (Rs)", f"Rs. {total_amount:,.2f}")
        
        generate_btn = st.form_submit_button("Generate Stock Handover QR", type="primary")
        
        if generate_btn:
            if not detected_dealer_key or not dealer_display_name or "No items" in available_items:
                st.error("Cannot generate QR! Please ensure a valid dealer with active products is selected.")
            else:
                # 💡 තෝරාගත් අයිතමයට අදාළ බාර්කෝඩ් එක ඩේටාබේස් ප්‍රොඩක්ට් ලිස්ට් එකෙන් සොයා ගැනීම
                selected_barcode = "N/A"
                for p in dealer_products_raw:
                    if p.get('item_name') == item_name:
                        selected_barcode = p.get('barcode', 'N/A')
                        break

                # QR දත්ත තුළට බාර්කෝඩ් එක ද ඇතුළත් කිරීම (POS Billing සඳහා අත්‍යවශ්‍යයි)
                qr_data = {
                    "shop_name": shop_name,
                    "shop_reg": shop_reg_no,
                    "dealer": current_dealer_name,
                    "item": item_name,
                    "barcode": selected_barcode, 
                    "buying_price": buying_price,
                    "qty": qty,
                    "free_qty": free_qty,
                    "total_amount": total_amount
                }
                
                json_string = json.dumps(qr_data)
                st.success("Stock details compiled successfully with Barcode! Scan below QR offline:")
                
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(json_string)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                col_q1, col_q2 = st.columns([1, 2])
                with col_q1:
                    st.markdown(f'<img src="data:image/png;base64,{img_str}" width="200">', unsafe_allow_html=True)
                with col_q2:
                    st.markdown(f"**Shop:** {shop_name} ({shop_reg_no})")
                    st.markdown(f"**Dealer:** {current_dealer_name}")
                    st.markdown(f"**Item:** {item_name}")
                    st.markdown(f"**Barcode:** `{selected_barcode}`")
                    st.markdown(f"**Qty:** {qty} | **Price:** Rs. {buying_price:,.2f}")
                    st.markdown(f"**Total:** Rs. {total_amount:,.2f}")