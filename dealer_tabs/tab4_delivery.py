
import streamlit as st
import database
import pandas as pd
from datetime import datetime, date

def render():
    st.markdown("### 🚚 Daily Delivery Progress & Route Tracking")
    st.info("ℹ️ QR ස්කෑන් මඟින් ඩීලර් ටීම් එක විසින් සාප්පු වෙත භාර දෙන ලද ඩිලිවරි තොරතුරු සහ දෛනික ප්‍රග්‍රස් එක.")

    current_dealer_user = st.session_state.get("username")
    if not current_dealer_user:
        st.error("❌ Error: No active user found in session! Please log in.")
        return

    # --- 1. DATE NAVIGATION (දවස් පාලනය) ---
    col_d1, col_d2 = st.columns([2, 2])
    with col_d1:
        selected_date = st.date_input("Select Delivery Date", value=date.today(), key="delivery_progress_date")
    
    date_str = selected_date.strftime("%Y-%m-%d")

    # --- 2. FETCH DELIVERIES DATA FROM SUPABASE ---
    deliveries_list = []
    
    # ඩීලර්ගේ යූසර් නේම් වෙනස්වීම් (alpha / dealer_alpha) ආවරණය කරගැනීමට
    search_dealer_ids = [current_dealer_user]
    if current_dealer_user == "alpha":
        search_dealer_ids.append("dealer_alpha")
    elif current_dealer_user == "dealer_alpha":
        search_dealer_ids.append("alpha")

    try:
        if hasattr(database, 'supabase'):
            # deliveries ටේබල් එකෙන් අදාළ ඩීලර්ගේ ඩිලිවරි ඩේටා ලබා ගැනීම
            res = database.supabase.table("deliveries").select("*").in_("dealer_username", search_dealer_ids).execute()
            if res.data:
                for d in res.data:
                    d_date = str(d.get("delivery_date", ""))
                    c_at = str(d.get("created_at", ""))
                    # තෝරාගත් දිනයට අදාළ ඩිලිවරි පමණක් ෆිල්ටර් කිරීම
                    if date_str in d_date or date_str in c_at:
                        deliveries_list.append(d)
    except Exception as e:
        st.warning(f"⚠️ Note fetching deliveries data: {e}")

    # --- 3. TOP SUMMARY KPI METRICS ---
    total_delivery_revenue = sum(float(item.get("total_delivery_amount", 0)) for item in deliveries_list)
    total_shops_visited = len(set(item.get("shop_name") for item in deliveries_list if item.get("shop_name")))

    st.markdown("---")
    st.markdown(f"#### 📈 Delivery Summary for Date: **{date_str}**")
    
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label="Total Delivered Value (Today)", value=f"Rs. {total_delivery_revenue:,.2f}")
    with kpi2:
        st.metric(label="Shops Visited / Loaded", value=f"{total_shops_visited} Shops")
    with kpi3:
        pi_approx = total_delivery_revenue / 100.0
        st.metric(label="Estimated Pi Value", value=f"~ {pi_approx:,.2f} Pi")

    st.markdown("---")

    # --- 4. DETAILED DELIVERIES TABLE ---
    st.markdown("#### 📋 Route & Shop-wise Delivery Details")
    
    if deliveries_list:
        df_deliveries = pd.DataFrame(deliveries_list)
        
        # පෙන්විය යුතු ප්‍රධාන කොලම් තෝරාගැනීම
        display_cols = ["delivery_time", "shop_name", "items_summary", "total_delivery_amount", "created_at"]
        avail_cols = [c for c in display_cols if c in df_deliveries.columns]
        
        # වගුව ලස්සනට පෙන්වීම
        st.dataframe(df_deliveries[avail_cols], use_container_width=True)
    else:
        st.info(f"ℹ️ No delivery records found for date **{date_str}**. (QR සෙවීමේදී බඩු ඩිලිවර් කළ පසු මෙහි වාර්තා පෙන්වනු ඇත).")