import streamlit as st
import cv2
import numpy as np
import database
import json

def render():
    st.markdown("### 🚚 Dealer Stock Handover & Delivery Confirmation")
    st.info("Capture a photo of the delivery confirmation QR code using the camera below to verify items against your dealer profile and securely update shop inventory.")

    # 💡 1. දැනට ලොග් වී සිටින සැබෑ ඩීලර්වරයාගේ තොරතුරු ලබා ගැනීම
    current_dealer_user = st.session_state.get("username")
    
    if not current_dealer_user:
        st.error("❌ Error: No active dealer user found in session! Please log in again.")
        return

    # ඩේටාබේස් එකෙන් ඩීලර්ගේ ප්‍රොފައިල් එක ලබා ගැනීම
    dealer_profile = database.get_dealer_profile(current_dealer_user) if hasattr(database, 'get_dealer_profile') else None
    
    # ඩීලර්ගේ නම හෝ pi_username නිවැරදිව හඳුනාගැනීම
    dealer_company_name = dealer_profile.get("company_name", "") if dealer_profile else ""
    dealer_pi_username = dealer_profile.get("pi_username", current_dealer_user) if dealer_profile else current_dealer_user

    # Session State මඟින් ස්කෑන් වූ QR ඩේටා රඳවා තබා ගැනීම
    if "scanned_qr_data_state" not in st.session_state:
        st.session_state.scanned_qr_data_state = ""

    # --- 2. NATIVE CAMERA & QR SCANNER ---
    st.markdown("#### 1. Capture Delivery QR Code via Camera")
    
    camera_image = st.camera_input("📸 Take a photo of the Delivery QR Code")
    
    scanned_code_from_camera = ""
    if camera_image is not None:
        bytes_data = camera_image.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(cv_img)
        
        if data:
            scanned_code_from_camera = data.strip()
            st.session_state.scanned_qr_data_state = scanned_code_from_camera
            st.success("✅ QR Code Successfully Captured and Decoded!")
        else:
            st.warning("⚠️ No QR code detected in the captured photo. Please ensure good lighting and try again.")

    active_qr_string = scanned_code_from_camera if scanned_code_from_camera else st.session_state.scanned_qr_data_state

    parsed_data = None

    if active_qr_string.strip():
        try:
            parsed_data = json.loads(active_qr_string.strip())
        except json.JSONDecodeError:
            st.error("❌ Invalid QR Data Format! Please capture a valid shop delivery confirmation QR code.")

    # --- 3. ඩේටා සාර්ථකව පාර්ස් වූ පසු ඩීලර් පරීක්ෂාව (Dealer Validation Check) ---
    if parsed_data:
        shop_name = parsed_data.get("shop_name", "Unknown Shop")
        shop_reg = parsed_data.get("shop_reg", "N/A")
        qr_dealer_field = parsed_data.get("dealer", "") # QR එකේ සඳහන් වන ඩීලර් විස්තරය
        item_name = parsed_data.get("item", "N/A")
        item_barcode = parsed_data.get("barcode", "N/A")
        buying_price = float(parsed_data.get("buying_price", 0.0))
        qty = int(parsed_data.get("qty", 0))
        free_qty = int(parsed_data.get("free_qty", 0))
        total_amount = float(parsed_data.get("total_amount", 0.0))

        # 💡 ප්‍රධාන ආරක්ෂිත පරීක්ෂාව: QR එකේ ඇති ඩීලර් සහ දැන් ලොග් වී සිටින ඩීලර් එක සමානදැයි බැලීම
        is_dealer_matched = (dealer_pi_username.lower() in qr_dealer_field.lower()) or (dealer_company_name.lower() in qr_dealer_field.lower())

        if not is_dealer_matched:
            # 🛑 වැරදි ඩීලර් කෙනෙක් නම් බරපතල ලෙස වළක්වා මැසේජ් එකක් පෙන්වීම
            st.error(f"🚨 **Security Warning: Invalid Dealer Stock!**")
            st.error(f"මෙම QR කෝඩ් එක වෙනත් ඩීලර්වරයෙකුට (`{qr_dealer_field if 'qr_data_dealer' in locals() else qr_dealer_field}`) අයත් එකකි. මෙය ඔබගේ (`{dealer_company_name or dealer_pi_username}`) ප්‍රොފައިලයට අදාළ භාණ්ඩ තොගයක් නොවන බැවින් ඩේටාබේස් එකට ඇතුළත් කළ නොහැක!")
            return # මෙතනින් ඉදිරියට කෝඩ් එක ක්‍රියාත්මක වීම සම්පූර්ණයෙන්ම නවතී.

        # 🟢 ඩීලර් හරි නම් පමණක් ඉදිරි සාරාංශය සහ කන්ෆර්මේෂන් පෙන්වීම
        st.markdown(f"""
            <div style="background-color: #e3f2fd; padding: 20px; border-radius: 10px; border-left: 6px solid #2196F3; margin-bottom: 20px;">
                <h3 style="color: #0d47a1; margin-top: 0;">📋 Delivery Verification Summary</h3>
                <hr style="border: 0; border-top: 1px solid #bbdefb; margin: 10px 0;">
                <p style="margin: 5px 0; font-size: 16px;">🏪 <b>Retail Shop:</b> {shop_name} ({shop_reg})</p>
                <p style="margin: 5px 0; font-size: 16px;">🏢 <b>Verified Dealer Match:</b> <span style="color: #2e7d32; font-weight: bold;">{qr_dealer_field} 🟢</span></p>
                <p style="margin: 5px 0; font-size: 16px;">📦 <b>Item Name:</b> {item_name}</p>
                <p style="margin: 5px 0; font-size: 16px;">📋 <b>Barcode:</b> <span style="color: #2e7d32; font-weight: bold;">{item_barcode}</span></p>
                <p style="margin: 5px 0; font-size: 16px;">📊 <b>Delivered Quantity:</b> <span style="color: #d32f2f; font-weight: bold;">{qty} units</span> {f'(+ {free_qty} Free Bonus)' if free_qty > 0 else ''}</p>
                <p style="margin: 5px 0; font-size: 16px;">💰 <b>Unit Buying Price:</b> Rs. {buying_price:,.2f}</p>
                <h4 style="color: #1565c0; margin: 10px 0 0 0;">Total Delivery Value: Rs. {total_amount:,.2f}</h4>
            </div>
        """, unsafe_allow_html=True)

        st.warning("⚠️ Please cross-check the physical goods, barcodes, and quantities with the above summary before confirming.")

        # --- 4. ඩීලර් තහවුරු කර ඩේටාබේස් එකට යැවීමේ බටන් එක ---
        if st.button("✅ Confirm & Update Shop Inventory Database", type="primary"):
            try:
                global supabase
                if database.supabase:
                    total_qty_to_add = qty + free_qty

                    # 1. shop_stock ටේබල් එකේ barcode එක මඟින් අයිතමය පවතියිදැයි පරීක්ෂා කිරීම
                    existing_stock = database.supabase.table("shop_stock").select("*").eq("shop_name", shop_name).eq("barcode", item_barcode).execute()
                    
                    if existing_stock.data and len(existing_stock.data) > 0:
                        # පවතියි නම් current_stock ප්‍රමාණය වැඩි කිරීම (Update)
                        current_qty = existing_stock.data[0].get("current_stock", 0)
                        new_total_stock = current_qty + total_qty_to_add
                        
                        database.supabase.table("shop_stock").update({
                            "current_stock": new_total_stock,
                            "buying_price": buying_price,
                            "item_name": item_name
                        }).eq("shop_name", shop_name).eq("barcode", item_barcode).execute()
                    else:
                        # නොපවතියි නම් අලුතින් ෂොප් ස්ටොක් එකට බාර්කෝඩ් එකත් සමඟ ඇතුළත් කිරීම (Insert)
                        database.supabase.table("shop_stock").insert({
                            "shop_name": shop_name,
                            "item_name": item_name,
                            "barcode": item_barcode, 
                            "current_stock": total_qty_to_add,
                            "buying_price": buying_price
                        }).execute()

                    # 2. deliveries ටේබල් එකටත් වාර්තාවක් සේව් කර තැබීම
                    try:
                        database.supabase.table("deliveries").insert({
                            "shop_name": shop_name,
                            "dealer_username": dealer_pi_username,
                            "items_summary": f"{item_name} ({item_barcode}) - {qty} units",
                            "total_delivery_amount": total_amount
                        }).execute()
                    except Exception:
                        pass

                    st.success(f"🎉 Delivery successfully verified! {total_qty_to_add} units of '{item_name}' (Barcode: {item_barcode}) added to {shop_name} inventory.")
                    st.balloons()
                else:
                    st.error("❌ Database connection error!")

            except Exception as e:
                st.error(f"❌ Error updating inventory database: {str(e)}")
    else:
        st.warning("⚠️ Please capture a photo of the retail shop's delivery confirmation QR code above to proceed.")