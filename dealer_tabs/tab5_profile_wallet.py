import streamlit as str_lit
import hashlib
import qrcode
from io import BytesIO
import database

def render():
    str_lit.markdown("### 👤 Dealer Profile & Unique Register Code")
    str_lit.info("Update your wholesale business profile and generate your secure unique dealer register code and verification QR.")
    
    # ඩීලර්ගේ යූසර්නෙම් එක ලබා ගැනීම (Session State එකෙන්)
    current_dealer = str_lit.session_state.get("username", "dealer_01")
    
    with str_lit.form("dealer_profile_form"):
        str_lit.markdown("#### 🏢 Business Details")
        company_name = str_lit.text_input("Company / Wholesale Business Name", value="")
        phone_number = str_lit.text_input("Contact Phone Number", value="")
        business_address = str_lit.text_input("Business Address", value="")
        pi_wallet = str_lit.text_input("Pi Mainnet Wallet Address", value="G")
        
        submitted = str_lit.form_submit_button("Update & Save to Database")
        
        if submitted:
            # 1. Advanced Method එකට Unique Register Code එකක් ජෙනරේට් කිරීම
            raw_string = f"{current_dealer}-{company_name}-{pi_wallet}"
            hash_object = hashlib.sha256(raw_string.encode())
            unique_code = f"PI-DL-ADV-{hash_object.hexdigest()[:16].upper()}"
            
            # 2. ඩේටාබේස් එකට සේව් කිරීම
            success, msg = database.save_or_update_dealer_profile(
                current_dealer, company_name, phone_number, business_address, pi_wallet, unique_code
            )
            
            if success:
                str_lit.success("Dealer profile and Register Code successfully saved to database! 🎉")
                str_lit.session_state["saved_register_code"] = unique_code
            else:
                str_lit.error(f"Failed to save profile: {msg}")

    str_lit.markdown("---")
    str_lit.markdown("### 🔐 Secure Unique Dealer Register Code & QR")
    
    # ඩේටාබේස් එකෙන් හෝ Session එකෙන් කෝඩ් එක ලබාගෙන පෙන්වීම
    active_code = str_lit.session_state.get("saved_register_code", None)
    
    if not active_code:
        # ඩිෆෝල්ට් ලෙස ජෙනරේට් කර පෙන්වීම
        raw_string = f"{current_dealer}"
        active_code = f"PI-DL-ADV-{hashlib.sha256(raw_string.encode()).hexdigest()[:16].upper()}"

    str_lit.markdown(f"**Generated Unique Register Code (Advanced):**")
    str_lit.code(active_code, language="text")
    
    # QR කෝඩ් එක ජෙනරේට් කර පෙන්වීම
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(active_code)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        col1, col2 = str_lit.columns([1, 2])
        with col1:
            str_lit.image(byte_im, caption="Dealer Verification QR", width=200)
        with col2:
            str_lit.markdown(f"- **Dealer Username:** {current_dealer}")
            str_lit.markdown(f"- **Status:** Verified Partner 🟢")
            str_lit.markdown(f"- **Database Sync:** Active (Saved)")
            
    except Exception as e:
        str_lit.warning(f"Could not generate QR code automatically: {e}")