import streamlit as st
import database
import pandas as pd
from datetime import date

def render_customer_promotions_tab():
    st.markdown("### 🔥 Personalized Promotions & New Arrivals")
    st.info("ℹ️ Active special offers from shops you have transacted with.")

    current_customer_user = st.session_state.get("username")
    if not current_customer_user:
        st.error("❌ Please log in as a customer.")
        return

    # 1. කස්ටමර් ගනුදෙනු කළ සාප්පු සෙවීම
    customer_shops = set()
    try:
        if hasattr(database, 'supabase'):
            sales_res = database.supabase.table("shop_sales").select("shop_name").execute()
            if sales_res.data:
                for s in sales_res.data:
                    if s.get("shop_name"):
                        customer_shops.add(s.get("shop_name"))
    except Exception as e:
        st.warning(f"⚠️ Note fetching customer shops: {e}")

    # 2. ප්‍රමෝෂන් දත්ත ලබා ගැනීම
    promos_list = []
    try:
        if hasattr(database, 'supabase'):
            p_res = database.supabase.table("promotions_arrivals").select("*").execute()
            if p_res.data:
                promos_list = p_res.data
    except Exception as e:
        st.warning(f"⚠️ Error fetching ads: {e}")

    if not promos_list:
        st.info("ℹ️ No active promotion data found.")
        return

    df_promos = pd.DataFrame(promos_list)

    # 3. වත්මන් දිනයට (Today) අදාළව සක්‍රීය ප්‍රමෝෂන් පමණක් ෆිල්ටර් කිරීම
    today_date = date.today()
    filtered_rows = []
    for idx, row in df_promos.iterrows():
        cat = str(row.get("category", ""))
        if "Promotion" in cat or "🔥" in cat:
            end_d_str = row.get("end_date")
            if end_d_str:
                try:
                    e_date = pd.to_datetime(end_d_str).date()
                    if e_date >= today_date:
                        filtered_rows.append(row)
                except:
                    pass
        else:
            # New Arrivals සඳහා දින සීමාවකින් තොරව පෙන්වයි
            filtered_rows.append(row)

    if not filtered_rows:
        st.info("ℹ️ No active promotions or new arrivals for today.")
        return

    df_customer_promos = pd.DataFrame(filtered_rows)

    # කස්ටමර් ගනුදෙනු කළ සාප්පු වලට අදාළව පෙරහන් කිරීම
    if customer_shops and "shop_name" in df_customer_promos.columns:
        df_filtered_shops = df_customer_promos[df_customer_promos["shop_name"].isin(customer_shops)]
        if not df_filtered_shops.empty:
            df_customer_promos = df_filtered_shops

    # --- Modern Sleek CSS Styling ---
    st.markdown("""
        <style>
        .promo-card { background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); border: 1px solid #cbd5e1; border-radius: 10px; overflow: hidden; margin-bottom: 12px; box-shadow: 0 3px 10px rgba(0, 0, 0, 0.04); }
        .promo-img-box { width: 100%; height: 140px; overflow: hidden; background: #e2e8f0; }
        .promo-img-box img { width: 100%; height: 100%; object-fit: cover; }
        .promo-details { padding: 10px 12px; }
        .promo-tag { font-size: 10px; font-weight: 700; color: #dc2626; text-transform: uppercase; margin-bottom: 2px; }
        .promo-heading { font-size: 14px; font-weight: 700; color: #1e293b; margin: 0 0 4px 0; }
        .old-prc { color: #94a3b8; font-size: 12px; text-decoration: line-through; margin-bottom: -3px; }
        .new-prc { color: #0d9488; font-size: 17px; font-weight: 800; }
        .save-tag { background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 11px; display: inline-block; margin-top: 3px; }
        .stk-info { font-size: 11px; color: #64748b; margin-top: 4px; }
        .shop-tag { background: #f1f5f9; color: #334155; padding: 6px 10px; font-weight: 600; font-size: 12px; border-top: 1px solid #e2e8f0; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

    cols = st.columns(3)

    for idx, row in df_customer_promos.reset_index(drop=True).iterrows():
        col_idx = idx % 3
        with cols[col_idx]:
            item_name = row.get("item_name", "Product")
            selling_price = float(row.get("selling_price", 0))
            original_price = float(row.get("original_price", 0))
            savings = float(row.get("savings_amount", 0))
            current_stock = int(row.get("current_stock", 0))
            img_url = row.get("image_url", "")
            shop_name = row.get("shop_name", "Retail Shop")
            category = row.get("category", "Promotion")
            end_d = row.get("end_date", "")

            if not img_url:
                img_url = "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=500&q=80"

            # 🛠️ Special Promotion සඳහා පමණක් දිනය පෙන්වීම, New Arrival සඳහා නම පමණක් පෙන්වීම
            if "Promotion" in category or "🔥" in category:
                badge_text = f"🔥 {category} (Expires: {end_d})"
            else:
                badge_text = f"📦 {category}"

            # Clean Single-line HTML String with English texts
            card_html = f'<div class="promo-card"><div class="promo-img-box"><img src="{img_url}" alt="{item_name}"></div><div class="promo-details"><div class="promo-tag">{badge_text}</div><div class="promo-heading">{item_name}</div>'
            
            if original_price > selling_price:
                card_html += f'<div class="old-prc">Rs. {original_price:,.2f}</div><div class="new-prc">Rs. {selling_price:,.2f}</div>'
                if savings > 0:
                    card_html += f'<div><span class="save-tag">💥 Savings: Rs. {savings:,.0f}!</span></div>'
            else:
                card_html += f'<div class="new-prc">Rs. {selling_price:,.2f}</div>'

            card_html += f'<div class="stk-info">📦 Stock Left: <b>{current_stock} units</b></div></div><div class="shop-tag">🏪 {shop_name}</div></div>'
            
            st.markdown(card_html, unsafe_allow_html=True)