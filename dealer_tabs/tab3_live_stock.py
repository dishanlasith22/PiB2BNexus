import streamlit as st
import database
import pandas as pd
from datetime import datetime, date

def render():
    st.markdown("### 🏢 Dealer Portal: Live Stock, Settlements & History")
    
    current_dealer_user = st.session_state.get("username")
    if not current_dealer_user:
        st.error("❌ Error: No active dealer user found in session! Please log in.")
        return

    # ඩීලර්ගේ ප්‍රොෆයිල් තොරතුරු ලබා ගැනීම
    dealer_profile = {}
    company_name = current_dealer_user
    try:
        if hasattr(database, 'supabase'):
            d_res = database.supabase.table("dealers").select("*").eq("pi_username", current_dealer_user).execute()
            if d_res.data and len(d_res.data) > 0:
                dealer_profile = d_res.data[0]
                company_name = dealer_profile.get("company_name", current_dealer_user)
    except Exception as e:
        st.warning(f"⚠️ Note fetching dealer profile: {e}")

    st.markdown(f"#### 🌟 Welcome, **{company_name}** (`{current_dealer_user}`)")
    st.markdown("---")

    # --- 1. DATE SELECTION FOR SETTLEMENTS ---
    col_d1, col_d2 = st.columns([2, 2])
    with col_d1:
        selected_date = st.date_input("Select Settlement Date", value=date(2026, 11, 11), key="dealer_settlement_date")
    
    date_str = selected_date.strftime("%Y-%m-%d")

    # --- 2. FETCH DATA FROM SUPABASE ---
    dealer_stock = []
    shop_sales_list = []
    all_settlements = []

    # විකල්ප ඩීලර් අයිඩී (උදා: 'alpha' සහ 'dealer_alpha' යන දෙකම සෙවීම සඳහා)
    search_dealer_ids = [current_dealer_user]
    if current_dealer_user == "alpha":
        search_dealer_ids.append("dealer_alpha")
    elif current_dealer_user == "dealer_alpha":
        search_dealer_ids.append("alpha")

    try:
        if hasattr(database, 'supabase'):
            # අ) මෙම ඩීලර්ට අයත් අයිතම විවිධ සාප්පු වල ස්ටොක් වී ඇති ආකාරය
            stock_res = database.supabase.table("shop_stock").select("*").in_("dealer_id", search_dealer_ids).execute()
            if stock_res.data:
                dealer_stock = stock_res.data

            # ආ) සාප්පු විකුණුම් වාර්තා ලබා ගැනීම
            sales_res = database.supabase.table("shop_sales").select("*").in_("dealer_id", search_dealer_ids).execute()
            if sales_res.data:
                for s in sales_res.data:
                    c_at = str(s.get("created_at", ""))
                    if date_str in c_at:
                        shop_sales_list.append(s)

            # ඉ) සියලුම සෙට්ල්මන්ට් ඉතිහාසය ලබා ගැනීම
            set_res = database.supabase.table("daily_settlements").select("*").execute()
            if set_res.data:
                all_settlements = set_res.data
    except Exception as e:
        st.warning(f"⚠️ Error fetching data: {e}")

    # --- 3. LIVE STOCK ACROSS SHOPS TABLE ---
    st.markdown("#### 📦 Live Stock Across All Retail Shops")
    st.info("ℹ️ විවිධ සාප්පු තුළ ඔබේ සමාගමෙන් ලබා දී ඇති භාණ්ඩවල වත්මන් ස්ටොක් තත්ත්වය.")

    if dealer_stock:
        df_stock = pd.DataFrame(dealer_stock)
        display_stock_cols = ["shop_name", "barcode", "item_name", "current_stock", "buying_price", "custom_selling_price"]
        avail_cols = [c for c in display_stock_cols if c in df_stock.columns]
        st.dataframe(df_stock[avail_cols], use_container_width=True)
    else:
        st.info("ℹ️ No stock records found for your dealer account across shops.")

    st.markdown("---")

    # --- 4. DAILY RECEIVABLE SETTLEMENT / PAYOUT SUMMARY ---
    st.markdown(f"#### 💰 Daily Receivable Payouts for Date: **{date_str}**")
    st.info("ℹ️ අද දවසේ විවිධ සාප්පු වලින් ඔබට ලැබීමට නියමිත මුළු මුදල (Buying Price මත පදනම්ව).")

    shop_grouped_sales = {}
    for sale in shop_sales_list:
        s_name = sale.get("shop_name", "Unknown Shop")
        if s_name not in shop_grouped_sales:
            shop_grouped_sales[s_name] = []
        shop_grouped_sales[s_name].append(sale)

    if shop_grouped_sales:
        total_receivable_all_shops = 0.0

        for shop_name, items in shop_grouped_sales.items():
            shop_payout_total = 0.0
            item_summary_lines = ""

            for itm in items:
                sold_q = float(itm.get("sold_qty", 1))
                unit_b_price = float(itm.get("unit_price", 0)) * 0.8 # Wholesale / Buying Price estimate
                line_total = unit_b_price * sold_q
                shop_payout_total += line_total
                
                item_summary_lines += f"- {itm.get('item_name')} (Qty: {sold_q}) - Rs. {line_total:,.2f}\n"

            total_receivable_all_shops += shop_payout_total

            is_settled = False
            for ds in all_settlements:
                d_time = str(ds.get("created_at", ""))
                if ds.get("shop_name") == shop_name and date_str in d_time:
                    is_settled = True
                    break

            with st.container():
                col_s1, col_s2, col_s3 = st.columns([2, 3, 2])
                
                with col_s1:
                    st.markdown(f"**Retail Shop:**\n### `🏪 {shop_name}`")
                
                with col_s2:
                    st.markdown("**Sold Items Breakdown:**")
                    st.markdown(item_summary_lines if item_summary_lines else "No items sold.")
                    st.markdown(f"**Receivable Amount:** **Rs. {shop_payout_total:,.2f}**")
                
                with col_s3:
                    st.markdown("**Payout Status:**")
                    if is_settled:
                        st.markdown(
                            """
                            <div style="background-color: #d4edda; color: #155724; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; border: 1px solid #c3e6cb;">
                                ✅ Settled & Paid
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            """
                            <div style="background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; border: 1px solid #ffeeba;">
                                ⏳ Pending (EOD 11:50 PM)
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                st.markdown("<hr style='margin: 10px 0px;'>", unsafe_allow_html=True)

        st.metric(label="Total Receivable Across All Shops Today", value=f"Rs. {total_receivable_all_shops:,.2f}")
    else:
        st.info(f"ℹ️ No sales recorded for your items on {date_str}.")

    st.markdown("---")

    # --- 5. SETTLEMENT HISTORY & VISUAL TREND CHART (ගෙවීම් ඉතිහාසය සහ ප්‍රස්ථාරය) ---
    st.markdown("#### 📈 Settlement & Payout History (ගෙවීම් ඉතිහාසය සහ ප්‍රවණතාවය)")
    st.info("ℹ️ පසුගිය දිනවල විවිධ සාප්පු වලින් ලැබුණු ගෙවීම්වල ඉතිහාසය සහ ප්‍රස්ථාරමය දර්ශනය.")

    if all_settlements:
        df_history = pd.DataFrame(all_settlements)
        
        # 💡 Pandas datetime parsing දෝෂය මඟහරවා ගැනීම සඳහා format='mixed' පාවිච්චි කර ඇත
        if "created_at" in df_history.columns:
            df_history["date"] = pd.to_datetime(df_history["created_at"], format='mixed', errors='coerce').dt.strftime("%Y-%m-%d")
        elif "settlement_date" in df_history.columns:
            df_history["date"] = df_history["settlement_date"]

        if "dealer_settlement_amount" in df_history.columns:
            df_history["amount"] = pd.to_numeric(df_history["dealer_settlement_amount"], errors="coerce")
        elif "total_amount" in df_history.columns:
            df_history["amount"] = pd.to_numeric(df_history["total_amount"], errors="coerce")

        show_cols = ["date", "shop_name", "amount", "total_amount"]
        avail_hist_cols = [c for c in show_cols if c in df_history.columns]
        
        st.dataframe(df_history[avail_hist_cols], use_container_width=True)

        st.markdown("##### 📉 Payout Trend Chart (ගෙවීම් ප්‍රස්ථාරය)")
        try:
            chart_data = df_history.groupby("date")["amount"].sum().reset_index()
            chart_data = chart_data.set_index("date")
            st.bar_chart(chart_data)
        except Exception:
            st.warning("⚠️ Chart rendering note: Insufficient grouped date data.")
    else:
        st.info("ℹ️ No past settlement history records found in database.")