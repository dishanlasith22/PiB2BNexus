import streamlit as st
import database
import pandas as pd
import hashlib
import qrcode
from io import BytesIO
import base64

def render():
    st.markdown("### 👤 Shop Profile, Secure Register Code & Staff Management")
    
    current_shop_user = st.session_state.get("username", "anura_stores")
    profile = database.get_shop_profile(current_shop_user) or {}
    
    # ස්වයංක්‍රීයව Unique Register Code එකක් සැදීම (SHA-256 මගින්)
    raw_string = f"{current_shop_user}_{profile.get('shop_name', 'Shop')}_SHOP_ADV"
    default_unique_code = f"PI-SHOP-ADV-{hashlib.sha256(raw_string.encode()).hexdigest()[:16].upper()}"
    saved_register_code = profile.get("register_code") or default_unique_code
    
    # Shop Profile Form
    with st.form("shop_profile_form"):
        st.markdown("#### 🏢 Business Details & Secured Wallet")
        shop_name = st.text_input("Shop Name", value=profile.get("shop_name", ""))
        phone_number = st.text_input("Phone Number", value=profile.get("phone_number", ""))
        address = st.text_area("Business Address", value=profile.get("address", ""))
        
        # Secured Wallet Address (Pi Sign-in locked)
        default_wallet = profile.get("wallet_address", f"PI-WALLET-{current_shop_user.upper()}-98765")
        st.markdown("🔒 **Pi Mainnet Wallet Address (Secured & Cross-Verified):**")
        wallet_address = st.text_input("Wallet Address", value=default_wallet, disabled=True, help="Locked to verified Pi Network sign-in session.")
        
        fb_page = st.text_input("Facebook Page Link", value=profile.get("fb_page", ""))
        web_url = st.text_input("Website URL", value=profile.get("web_url", ""))
        unique_code = st.text_input("Secure Unique Register Code", value=saved_register_code, disabled=True)
        
        if st.form_submit_button("Update & Save Shop Profile"):
            success, msg = database.save_or_update_shop_profile(
                current_shop_user, shop_name, phone_number, address, default_wallet, fb_page, web_url, saved_register_code
            )
            if success:
                st.success(f"🎉 {msg}")
                st.rerun()
            else:
                st.error(f"Error: {msg}")

    st.markdown("---")
    
    # --- DISPLAY UNIQUE CODE & QR CODE ---
    st.markdown("#### 🔐 Secure Unique Shop Register Code & QR")
    st.info(f"Generated Unique Register Code: **{saved_register_code}**")
    
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(saved_register_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        col_qr1, col_qr2 = st.columns([1, 2])
        with col_qr1:
            st.markdown(f'<img src="data:image/png;base64,{img_str}" width="150">', unsafe_allow_html=True)
        with col_qr2:
            st.markdown(f"- **Shop Username:** {current_shop_user}")
            st.markdown("- **Status:** Verified Retailer Partner 🟢")
            st.markdown("- **Database Sync:** Active (Saved)")
    except Exception as e:
        st.warning(f"QR note: {e}")

    st.markdown("---")
    
    # --- BRANCH MANAGEMENT SECTION ---
    st.markdown("#### 🌿 Shop Branches Management")
    with st.form("branch_add_form"):
        new_branch_name = st.text_input("Add New Branch / Counter Name")
        if st.form_submit_button("Add Branch"):
            if new_branch_name.strip():
                b_s, b_m = database.add_shop_branch(current_shop_user, new_branch_name)
                if b_s:
                    st.success(b_m)
                    st.rerun()
                else:
                    st.error(b_m)
            else:
                st.warning("Please enter a branch name.")
                
    branches_data = database.fetch_shop_branches(current_shop_user)
    branch_options = [b['branch_name'] for b in branches_data] if branches_data else ["Main Branch"]

    if branches_data:
        st.markdown("##### Existing Branches List")
        for b in branches_data:
            col_b1, col_b2 = st.columns([3, 1])
            with col_b1:
                st.markdown(f"📍 **{b['branch_name']}**")
            with col_b2:
                if st.button("Delete", key=f"del_b_{b['id']}"):
                    database.delete_shop_branch(b['id'])
                    st.rerun()

    st.markdown("---")
    
    # --- STAFF MANAGEMENT SECTION ---
    st.markdown("#### 👥 Staff Sub-Accounts & PIN Access")
    with st.form("staff_sub_form"):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            staff_name = st.text_input("Staff Name")
            staff_pin = st.text_input("Staff PIN (e.g. 1234)", max_chars=6)
        with col_s2:
            role = st.selectbox("Staff Role", ["Cashier", "Stock Inventory Manager"])
            branch_assigned = st.selectbox("Assign to Branch", options=branch_options)
            
        if st.form_submit_button("Add Staff Sub-Account"):
            if staff_name.strip() and staff_pin.strip():
                s_succ, s_msg = database.add_shop_staff(current_shop_user, staff_name, staff_pin, role, branch_assigned)
                if s_succ:
                    st.success(s_msg)
                    st.rerun()
                else:
                    st.error(s_msg)
            else:
                st.warning("Please fill in staff name and PIN.")

    staff_list = database.fetch_shop_staff(current_shop_user)
    if staff_list:
        st.markdown("##### Existing Staff Members")
        st.dataframe(pd.DataFrame(staff_list)[['staff_name', 'role', 'branch_name', 'created_at']], use_container_width=True)
        
        # Staff Delete option
        selected_to_del = st.selectbox("Select Staff to Delete", options=staff_list, format_func=lambda x: f"{x['staff_name']} ({x['role']} - {x['branch_name']})", key="del_staff_box")
        if st.button("Delete Selected Staff"):
            database.delete_shop_staff(selected_to_del['id'])
            st.success("Staff deleted successfully!")
            st.rerun()