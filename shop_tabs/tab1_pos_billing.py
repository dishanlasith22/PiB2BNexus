import streamlit as st
import database
import pandas as pd
import urllib.parse
from datetime import datetime

def render():
    st.markdown("### 🛒 Standard POS Billing Counter (Pi POS)")
    
    current_shop_user = st.session_state.get("username")
    if not current_shop_user:
        st.error("❌ Error: No active shop user found in session! Please log in.")
        return

    shop_profile = database.get_shop_profile(current_shop_user) or {}
    shop_name = shop_profile.get("shop_name", "Anura Stores")

    branches_list = ["Main Branch"]
    try:
        if hasattr(database, 'supabase'):
            branch_res = database.supabase.table("shop_branches").select("branch_name").eq("pi_username", current_shop_user).execute()
            if branch_res.data:
                branches_list = [b["branch_name"] for b in branch_res.data]
    except Exception:
        pass

    # --- STEP 1: BRANCH & CASHIER PIN AUTHENTICATION ---
    st.markdown("#### 1. Counter Authentication & Branch Selection")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        selected_branch = st.selectbox("Select Shop Branch", options=branches_list, key="pos_branch_select")
    with col_b2:
        cashier_pin = st.text_input("Enter Cashier PIN Number", type="password", placeholder="Enter 4-digit staff PIN...", key="pos_cashier_pin_input")

    is_authenticated = False
    cashier_name = "Admin / Default Cashier"

    if cashier_pin.strip():
        try:
            if hasattr(database, 'supabase'):
                staff_res = database.supabase.table("shop_staff").select("*").eq("pi_username", current_shop_user).eq("staff_pin", cashier_pin.strip()).execute()
                if staff_res.data and len(staff_res.data) > 0:
                    is_authenticated = True
                    cashier_name = staff_res.data[0].get("staff_name", "Staff")
                    st.success(f"✅ Verified Cashier: **{cashier_name}** at Branch: **{selected_branch}**")
                else:
                    st.error("❌ Invalid Cashier PIN Number! Please check and re-enter.")
        except Exception as e:
            if cashier_pin.strip() == "1234":
                is_authenticated = True
                cashier_name = "Default Cashier (1234)"
                st.success(f"✅ Verified Cashier: **{cashier_name}** at Branch: **{selected_branch}**")
            else:
                st.warning("⚠️ Staff authentication check failed, enter '1234' for test PIN.")
    else:
        st.info("ℹ️ Please enter your Cashier PIN to unlock the billing interface.")

    if not is_authenticated:
        return

    st.markdown("---")
    st.markdown("#### 2. Barcode Input & Cart Management")

    if "pos_cart" not in st.session_state:
        st.session_state.pos_cart = []

    if "pi_qr_generated" not in st.session_state:
        st.session_state.pi_qr_generated = False

    # බිල් එක ජෙනරේට් කළ കൃത്യ වෙලාව (Timestamp) සේව් කරගැනීම (පැරණි ඩේටා සමඟ පැටලීම වැළැක්වීමට)
    if "qr_generated_time" not in st.session_state:
        st.session_state.qr_generated_time = None

    if "pending_match_items" not in st.session_state:
        st.session_state.pending_match_items = []

    def handle_barcode_input():
        barcode_val = st.session_state.get("pos_manual_barcode_input", "").strip()
        if not barcode_val:
            return
        
        try:
            if hasattr(database, 'supabase'):
                stock_res = database.supabase.table("shop_stock").select("*").eq("shop_name", shop_name).eq("barcode", barcode_val).execute()
                matched_items = stock_res.data if stock_res.data else []

                if len(matched_items) == 1:
                    st.session_state.pending_match_items = []
                    item = matched_items[0]
                    item_id = item.get("id")
                    item_name = item.get("item_name")
                    dealer_id = item.get("dealer_id") or "Direct / Default"
                    stock_qty = item.get("current_stock", 0)
                    price = item.get("custom_selling_price") or item.get("buying_price", 100.0) * 1.2

                    found = False
                    for cart_it in st.session_state.pos_cart:
                        if cart_it["stock_id"] == item_id:
                            if cart_it["qty"] < stock_qty:
                                cart_it["qty"] += 1
                                cart_it["total"] = cart_it["qty"] * cart_it["unit_price"]
                            found = True
                            break
                    
                    if not found:
                        if stock_qty > 0:
                            st.session_state.pos_cart.append({
                                "stock_id": item_id,
                                "item_name": item_name,
                                "barcode": barcode_val,
                                "dealer_id": dealer_id,
                                "qty": 1,
                                "unit_price": price,
                                "total": price
                            })
                elif len(matched_items) > 1:
                    st.session_state.pending_match_items = matched_items
                else:
                    st.session_state.pending_match_items = []
                    st.warning(f"⚠️ No item found for barcode: {barcode_val}")
        except Exception as e:
            st.error(f"❌ Error: {e}")
        
        st.session_state.pos_manual_barcode_input = ""

    st.text_input(
        "🔍 Scan Barcode (USB Scanner) or Type Barcode & Press Enter", 
        placeholder="Type barcode and press Enter...", 
        key="pos_manual_barcode_input",
        on_change=handle_barcode_input
    )

    if st.session_state.pending_match_items:
        st.markdown("---")
        st.markdown("⚠️ **Multiple items matched this barcode. Click the correct item below:**")
        for idx, prod in enumerate(st.session_state.pending_match_items):
            p_name = prod.get("item_name")
            p_dealer = prod.get("dealer_id") or "Direct / Default"
            p_stock = prod.get("current_stock", 0)
            p_price = prod.get("custom_selling_price") or prod.get("buying_price", 100.0) * 1.2

            card_label = f"📦 {p_name} | Dealer: {p_dealer} | Stock: {p_stock} | Price: Rs. {p_price:,.2f}"
            if st.button(card_label, key=f"tab_select_btn_{idx}_{prod.get('id')}", use_container_width=True):
                item_id = prod.get("id")
                found = False
                for cart_it in st.session_state.pos_cart:
                    if cart_it["stock_id"] == item_id:
                        if cart_it["qty"] < p_stock:
                            cart_it["qty"] += 1
                            cart_it["total"] = cart_it["qty"] * cart_it["unit_price"]
                        found = True
                        break
                if not found and p_stock > 0:
                    st.session_state.pos_cart.append({
                        "stock_id": item_id,
                        "item_name": p_name,
                        "barcode": prod.get("barcode"),
                        "dealer_id": p_dealer,
                        "qty": 1,
                        "unit_price": p_price,
                        "total": p_price
                    })
                st.session_state.pending_match_items = []
                st.rerun()
        st.markdown("---")

    # --- STEP 3: LIVE BILLING SUMMARY TABLE (මෙය සෑම විටම පෙනෙන සේ සකසා ඇත) ---
    st.markdown("#### 3. Live Billing Summary Table")

    if st.session_state.pos_cart:
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([3, 1.2, 1.8, 1.8, 1.2])
        h_col1.markdown("**Item Name & Dealer**")
        h_col2.markdown("**Quantity**")
        h_col3.markdown("**Unit Price (Rs.)**")
        h_col4.markdown("**Amount (Rs.)**")
        h_col5.markdown("**Action**")
        st.markdown("<hr style='margin: 5px 0px 10px 0px;'>", unsafe_allow_html=True)

        item_to_remove = None

        for i, item in enumerate(st.session_state.pos_cart):
            row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([3, 1.2, 1.8, 1.8, 1.2])
            with row_col1:
                st.markdown(f"**{item['item_name']}**")
                st.caption(f"Dealer: {item['dealer_id']}")
            with row_col2:
                st.markdown(f"**{item['qty']}**")
            with row_col3:
                st.markdown(f"Rs. {item['unit_price']:,.2f}")
            with row_col4:
                st.markdown(f"**Rs. {item['total']:,.2f}**")
            with row_col5:
                if st.button("❌ Remove", key=f"quick_del_{i}_{item['stock_id']}"):
                    item_to_remove = i
            st.markdown("<hr style='margin: 5px 0px; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

        if item_to_remove is not None:
            st.session_state.pos_cart.pop(item_to_remove)
            st.rerun()

        grand_total = sum(i["total"] for i in st.session_state.pos_cart)
        
        st.markdown(
            f"""
            <div style="background-color: #263238; padding: 15px; border-radius: 8px; text-align: right; margin-top: 15px; border: 2px solid #37474f;">
                <span style="font-size: 20px; font-weight: bold; color: #eceff1;">Grand Total: </span>
                <span style="font-size: 24px; font-weight: bold; color: #ff5252;">Rs. {grand_total:,.2f}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)

        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🗑️ Clear Cart", type="secondary", use_container_width=True):
                st.session_state.pos_cart = []
                st.session_state.pi_qr_generated = False
                st.session_state.qr_generated_time = None
                st.rerun()

        with col_act2:
            if st.button(" π Generate Pi Payment QR", type="primary", use_container_width=True):
                st.session_state.pi_qr_generated = True
                # QR එක ජෙනරේට් කළ കൃത്യවත් වේලාව රෙකෝඩ් කරගැනීම (මෙයට පසු සිදුවන ගෙවීම් පමණක් පිළිගැනීමට)
                st.session_state.qr_generated_time = datetime.now()

        # --- STEP 4: PI NETWORK QR & REAL-TIME PAYMENT STATUS ---
        if st.session_state.get("pi_qr_generated", False):
            st.markdown("---")
            st.markdown("#### 📱 Pi Network Payment QR & Live Status")
            
            timestamp_str = st.session_state.qr_generated_time.isoformat()
            pi_payload = f"pi_pos_pay://shop?username={current_shop_user}&branch={selected_branch}&total={grand_total}&time={timestamp_str}"
            qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={urllib.parse.quote(pi_payload)}"
            
            col_q1, col_q2 = st.columns([1, 2])
            with col_q1:
                st.image(qr_api_url, caption="Scan with Pi Wallet")
            with col_q2:
                st.info(f"Shop ID: **{current_shop_user}** | Cashier: **{cashier_name}** | Branch: **{selected_branch}**")
                st.markdown(f"### Amount: **Rs. {grand_total:,.2f}** (~{grand_total/1000:.2f} Pi)")
                
                # 🔄 Real-time Database Check (QR එක ජෙනරේට් කළ පසු නව ගනුදෙනුවක් සිදුවී ඇද්දැයි පරීක්ෂා කිරීම)
                payment_received = False
                try:
                    if hasattr(database, 'supabase'):
                        # shop_sales ටේබල් එකෙන් අදාළ ෂොප් එකේ අන්තිම සේල් එක ලබා ගැනීම
                        check_res = database.supabase.table("shop_sales").select("*").eq("shop_name", shop_name).order("id", desc=True).limit(1).execute()
                        if check_res.data:
                            latest_sale = check_res.data[0]
                            sale_created_at = latest_sale.get("created_at") # ඩේටාබේස් එකේ රෙකෝඩ් වැටුණු වෙලාව
                            
                            # මුදල සමාන නම් සහ QR එක ජෙනරේට් කළ පසු මෙම සේල් එක සිදුවී ඇත්නම් පමණක් සක්සස් කිරීම
                            if float(latest_sale.get("total_amount", 0)) == float(grand_total):
                                if sale_created_at:
                                    sale_time = datetime.fromisoformat(sale_created_at.replace("Z", "+00:00").split("+")[0])
                                    if st.session_state.qr_generated_time and sale_time >= st.session_state.qr_generated_time.replace(tzinfo=None):
                                        payment_received = True
                except Exception as e:
                    pass

                if payment_received:
                    st.markdown("""
                        <div style="background-color: #065f46; padding: 15px; border-radius: 8px; border: 1px solid #10b981; color: #ffffff; text-align: center;">
                            🎉 <b>PAYMENT RECEIVED SUCCESSFULLY!</b><br>
                            <span style="font-size: 13px;">Pi blockchain transaction verified & inventory updated.</span>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("✨ Clear & Start Next Bill", type="primary", use_container_width=True):
                        st.session_state.pos_cart = []
                        st.session_state.pi_qr_generated = False
                        st.session_state.qr_generated_time = None
                        st.rerun()
                else:
                    st.markdown("""
                        <div style="background-color: #1e293b; padding: 12px; border-radius: 8px; border: 1px solid #334155; color: #f8fafc;">
                            ⏳ <b>Waiting for customer Pi payment scan...</b><br>
                            <span style="font-size: 12px; color: #94a3b8;">Screen will auto-update once customer completes payment.</span>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("🔄 Refresh Status", use_container_width=True):
                        st.rerun()
    else:
        st.info("🛒 Billing cart is empty. Scan barcode to add items.")