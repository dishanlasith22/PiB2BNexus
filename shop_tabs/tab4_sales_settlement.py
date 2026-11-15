import streamlit as st
import database
import pandas as pd
from datetime import datetime, date

def render():
    st.markdown("### 📊 Sales & Dealer Auto-Settlement Dashboard")
    
    current_shop_user = st.session_state.get("username")
    if not current_shop_user:
        st.error("❌ Error: No active shop user found in session! Please log in.")
        return

    shop_profile = database.get_shop_profile(current_shop_user) or {}
    shop_name = shop_profile.get("shop_name", "Anura Stores")

    # --- 1. DATE NAVIGATION (ದවස් පාලනය) ---
    st.markdown("#### 1. Select Date for Sales & Settlement Reports")
    col_d1, col_d2 = st.columns([2, 2])
    with col_d1:
        selected_date = st.date_input("Select Date", value=date.today(), key="settlement_date_picker")
    
    date_str = selected_date.strftime("%Y-%m-%d")

    # --- 2. FETCH DATA FROM SUPABASE ---
    daily_sales = []
    current_stock = []
    dealer_settlements_db = []
    item_buying_prices = {} # අයිතමවල buying_price ගබඩා කරගැනීමට ඩික්ෂනරි එකක්

    try:
        if hasattr(database, 'supabase'):
            # අදාළ දිනයට අදාළ විකුණුම් ලබා ගැනීම
            sales_res = database.supabase.table("shop_sales").select("*").eq("shop_name", shop_name).execute()
            if sales_res.data:
                for s in sales_res.data:
                    created_at = str(s.get("created_at", ""))
                    if date_str in created_at:
                        daily_sales.append(s)

            # වත්මන් ස්ටොක් තත්ත්වය ලබා ගැනීම සහ Buying Prices මැප් කිරීම
            stock_res = database.supabase.table("shop_stock").select("*").eq("shop_name", shop_name).execute()
            if stock_res.data:
                raw_stock = stock_res.data
                for item in raw_stock:
                    i_name = item.get("item_name")
                    b_price = float(item.get("buying_price", 0))
                    if i_name:
                        item_buying_prices[i_name] = b_price

                    d_username = item.get("dealer_id")
                    comp_name = d_username
                    if d_username and d_username != "Direct / Default":
                        try:
                            d_prof = database.supabase.table("dealers").select("company_name").eq("pi_username", d_username).execute()
                            if d_prof.data and len(d_prof.data) > 0:
                                comp_name = d_prof.data[0].get("company_name", d_username)
                        except Exception:
                            pass
                    
                    item["company_name"] = comp_name if comp_name else "Direct / Default"
                    current_stock.append(item)

            # ඩීලර් සෙට්ල්මන්ට් වාර්තා ලබා ගැනීම
            try:
                settle_res = database.supabase.table("daily_settlements").select("*").eq("shop_name", shop_name).execute()
                if settle_res.data:
                    for ds in settle_res.data:
                        d_time = str(ds.get("created_at", ""))
                        if date_str in d_time:
                            dealer_settlements_db.append(ds)
            except Exception:
                pass
    except Exception as e:
        st.warning(f"⚠️ Note fetching data: {e}")

    # --- 3. KPI SUMMARY CARDS (සාප්පුවේ ආදායම - Selling Price අනුව) ---
    total_revenue = sum(float(item.get("total_amount", 0)) for item in daily_sales)
    total_bills = len(daily_sales)

    st.markdown("---")
    st.markdown(f"#### 📈 Summary for Date: **{date_str}**")
    
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label="Total Shop Revenue", value=f"Rs. {total_revenue:,.2f}")
    with kpi2:
        st.metric(label="Total Sales Items / Records", value=total_bills)
    with kpi3:
        pi_approx = total_revenue / 100.0
        st.metric(label="Estimated Pi Value", value=f"~ {pi_approx:,.2f} Pi")

    st.markdown("---")

    # --- 4. DAILY SALES TRANSACTIONS TABLE ---
    st.markdown("#### 🛒 Daily Sales Transactions (Customer & Shop)")
    if daily_sales:
        df_sales = pd.DataFrame(daily_sales)
        if "customer_id" not in df_sales.columns and "pi_username" in df_sales.columns:
            df_sales["customer_id"] = df_sales["pi_username"]
        elif "customer_id" not in df_sales.columns:
            df_sales["customer_id"] = current_shop_user

        display_cols = ["created_at", "customer_id", "item_name", "sold_qty", "unit_price", "total_amount", "payment_method"]
        available_cols = [c for c in display_cols if c in df_sales.columns]
        st.dataframe(df_sales[available_cols], use_container_width=True)
    else:
        st.info(f"ℹ️ No sales records found for {date_str}.")

    st.markdown("---")

    # --- 5. DEALER AUTO-SETTLEMENT & PAYOUT SUMMARY (Buying Price අනුව ගණනය කිරීම) ---
    st.markdown("#### 🤝 Dealer End-of-Day Auto-Settlement (11:50 PM Payout)")
    st.info("ℹ️ සෑම දිනකම රාත්‍රී 11:50ට ඩීලර්ට ගෙවිය යුතු මුදල අදාළ භාණ්ඩවල **ගැනුම් මිල (Buying Price)** මත පදනම්ව ස්වයංක්‍රීයව ගණනය වේ.")

    dealer_grouped_items = {}
    for item in daily_sales:
        d_id = item.get("dealer_id") or "Direct / Default"
        c_name = d_id
        if d_id != "Direct / Default":
            try:
                d_prof = database.supabase.table("dealers").select("company_name").eq("pi_username", d_id).execute()
                if d_prof.data and len(d_prof.data) > 0:
                    c_name = d_prof.data[0].get("company_name", d_id)
            except Exception:
                pass

        if c_name not in dealer_grouped_items:
            dealer_grouped_items[c_name] = []
        dealer_grouped_items[c_name].append(item)

    if dealer_grouped_items:
        for company_name, items in dealer_grouped_items.items():
            # 💡 ඩීලර්ට ගෙවිය යුතු මුදල හැදෙන්නේ Buying Price × Sold Qty මඟිනි
            dealer_total_amt = 0.0
            item_breakdown_list = []

            for itm in items:
                i_name = itm.get("item_name")
                sold_qty = float(itm.get("sold_qty", 1))
                # ස්ටොක් එකෙන් Buying Price ලබා ගැනීම (නැත්නම් විකුණුම් මිලෙන් 80%ක් හෝ ඩිෆෝල්ට් අගයක්)
                b_price = item_buying_prices.get(i_name, float(itm.get("unit_price", 0)) * 0.8)
                line_buying_total = b_price * sold_qty
                dealer_total_amt += line_buying_total

                item_breakdown_list.append({
                    "item_name": i_name,
                    "qty": sold_qty,
                    "buying_price": b_price,
                    "total_buying": line_buying_total
                })

            # 🛡️ Safe Null Checks for DB Settlement Status
            is_settled_in_db = False
            first_item_dealer = items[0].get("dealer_id") if items and len(items) > 0 else ""
            if first_item_dealer is None:
                first_item_dealer = ""

            for ds in dealer_settlements_db:
                ds_dealer = ds.get("dealer_id")
                if ds_dealer is not None:
                    if str(ds_dealer) == str(company_name) or str(ds_dealer) == str(first_item_dealer):
                        is_settled_in_db = True
                        break

            with st.container():
                col_box1, col_box2, col_box3 = st.columns([2, 3, 2])
                
                with col_box1:
                    st.markdown(f"**Dealer Company Name:**\n### `🏢 {company_name}`")
                
                with col_box2:
                    st.markdown("**Sold Items Breakdown (Qty & Buying Price Payout):**")
                    item_summary_text = ""
                    for idx, b_item in enumerate(item_breakdown_list[:5], 1):
                        item_summary_text += f"- {b_item['item_name']} (Qty: {b_item['qty']}) [Buy: Rs. {b_item['buying_price']:,.2f}] - **Rs. {b_item['total_buying']:,.2f}**\n"
                    st.markdown(item_summary_text)
                    st.markdown(f"**Total Dealer Payout (Wholesale):** **Rs. {dealer_total_amt:,.2f}**")
                
                with col_box3:
                    st.markdown("**Auto-Transaction Status:**")
                    if is_settled_in_db:
                        st.markdown(
                            """
                            <div style="background-color: #d4edda; color: #155724; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; border: 1px solid #c3e6cb;">
                                ✅ Verified & Success (11:50 PM Payout Done)
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            """
                            <div style="background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; border: 1px solid #ffeeba;">
                                ⏳ Pending (Scheduled at 11:50 PM)
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                st.markdown("<hr style='margin: 10px 0px;'>", unsafe_allow_html=True)
    else:
        st.info("ℹ️ No sales data to generate dealer settlements for this date.")

    st.markdown("---")

    # --- 6. CURRENT INVENTORY STOCK STATUS ---
    st.markdown("#### 📦 Current Inventory Stock Overview")
    if current_stock:
        df_stock = pd.DataFrame(current_stock)
        if "company_name" in df_stock.columns:
            df_stock["dealer_name"] = df_stock["company_name"]
        elif "dealer_id" in df_stock.columns:
            df_stock["dealer_name"] = df_stock["dealer_id"]

        stock_cols = ["barcode", "item_name", "dealer_name", "current_stock", "buying_price", "custom_selling_price"]
        avail_stock_cols = [c for c in stock_cols if c in df_stock.columns]
        st.dataframe(df_stock[avail_stock_cols], use_container_width=True)
    else:
        st.warning("⚠️ No stock items found in inventory.")