import streamlit as st
import database
import pandas as pd
from PIL import Image
import io
from datetime import date

def render():
    st.markdown("### 📢 Manage Promotions & New Arrivals")
    st.info("ℹ️ විශේෂ ප්‍රමෝෂන් දීමනා හෝ අලුතින් පැමිණි භාණ්ඩ (New Arrivals) මෙතැනින් එකතු කරන්න සහ කළමනාකරණය කරන්න.")

    current_shop_user = st.session_state.get("username")
    if not current_shop_user:
        st.error("❌ Error: No active shop user found!")
        return

    shop_profile = database.get_shop_profile(current_shop_user) or {}
    shop_name = shop_profile.get("shop_name", current_shop_user)

    # --- 1. CLEAR TRIGGER CHECK ---
    if st.session_state.get("clear_form", False):
        st.session_state["form_item_name"] = ""
        st.session_state["form_selling_price"] = 0.0
        st.session_state["form_original_price"] = 0.0
        st.session_state["form_stock"] = 10
        st.session_state["clear_form"] = False

    # --- 2. SUBMISSION FORM WITH NATIVE CLEAR MECHANISM ---
    with st.form("promo_creation_form", clear_on_submit=True):
        st.markdown("#### 📝 Add New Campaign / Arrival")
        
        ad_type = st.selectbox("Ad Category", ["🔥 Special Promotion", "📦 New Arrival"], key="form_ad_type")
        item_name = st.text_input("Item Name (භාණ්ඩයේ නම - උදා: Butter 250g)", key="form_item_name")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            selling_price = st.number_input("Selling Price / Promo Price (Rs.)", min_value=0.0, step=10.0, key="form_selling_price")
        with col_p2:
            original_price = st.number_input("Original Market Price (Rs.)", min_value=0.0, step=10.0, key="form_original_price")
            
        start_date = date.today()
        end_date = date.today()
        
        if ad_type == "🔥 Special Promotion":
            st.markdown("---")
            st.markdown("🕒 **Promotion Schedule (പ്രമോഷൻ കാലസීමාව)**")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                start_date = st.date_input("Promotion Start Date", value=date.today(), key="form_start_date")
            with col_d2:
                end_date = st.date_input("Promotion End Date", value=date.today(), key="form_end_date")

        current_stock = st.number_input("Current Available Stock", min_value=1,  key="form_stock")
        uploaded_image = st.file_uploader("Upload Item Photo (JPG/PNG)", type=["jpg", "jpeg", "png"], key="form_img_uploader")
        
        submitted = st.form_submit_button("🚀 Publish / Save Ad")

        if submitted:
            if not item_name or selling_price <= 0:
                st.error("⚠️ කරුණාකර භාණ්ඩයේ නම සහ නිවැරදි මිලක් ඇතුළත් කරන්න.")
            elif ad_type == "🔥 Special Promotion" and start_date > end_date:
                st.error("⚠️ ආරම්භක දිනය (Start Date) අවසන් දිනයට (End Date) වඩා පසුපසින් තිබිය නොහැක.")
            else:
                image_url = ""
                if uploaded_image is not None:
                    try:
                        img = Image.open(uploaded_image)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        
                        output_io = io.BytesIO()
                        img.save(output_io, format="JPEG", quality=80, optimize=True)
                        output_io.seek(0)
                        
                        file_name = f"{shop_name}_{int(pd.Timestamp.now().timestamp())}.jpg".replace(" ", "_")
                        
                        if hasattr(database, 'supabase'):
                            database.supabase.storage.from_("promos").upload(
                                file_name, 
                                output_io.getvalue(), 
                                file_options={"content-type": "image/jpeg", "upsert": "true"}
                            )
                            image_url = database.supabase.storage.from_("promos").get_public_url(file_name)
                    except Exception as img_err:
                        st.warning(f"⚠️ Image upload note: {img_err}")

                savings = max(0.0, original_price - selling_price) if original_price > selling_price else 0.0

                final_start = str(start_date) if ad_type == "🔥 Special Promotion" else str(date.today())
                final_end = str(end_date) if ad_type == "🔥 Special Promotion" else str(date.today().replace(year=date.today().year + 1))

                promo_data = {
                    "shop_name": shop_name,
                    "item_name": item_name,
                    "category": ad_type,
                    "original_price": original_price,
                    "selling_price": selling_price,
                    "savings_amount": savings,
                    "current_stock": current_stock,
                    "image_url": image_url,
                    "start_date": final_start,
                    "end_date": final_end
                }

                try:
                    if hasattr(database, 'supabase'):
                        database.supabase.table("promotions_arrivals").insert(promo_data).execute()
                        st.success("✅ දැන්වීම සාර්ථਕව ප්‍රකාශයට පත් කරන ලදී!")
                except Exception as db_err:
                    st.error(f"❌ Database error: {db_err}")

    st.markdown("---")
    
    # --- 3. EXISTING ADS MANAGEMENT TABLE (UPDATE & DELETE) ---
    st.markdown("### 🛠️ Active Ads & Arrivals Management")
    st.info("ℹ️ ඔබ විසින් පළ කරන ලද දැන්වීම් මෙතැනින් පරීක්ෂා කිරීමට, මිල යාවත්කාලීන කිරීමට හෝ ඉවත් කිරීමට (Delete) හැක.")

    try:
        if hasattr(database, 'supabase'):
            res = database.supabase.table("promotions_arrivals").select("*").eq("shop_name", shop_name).execute()
            ads_list = res.data if res.data else []
            
            if not ads_list:
                st.info("ℹ️ තවම ප්‍රකාශිත දැන්වීම් කිසිවක් නොමැත.")
                return

            for ad in ads_list:
                with st.expander(f"📌 {ad.get('item_name')} ({ad.get('category')})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_sell_price = st.number_input("Update Selling Price (Rs.)", value=float(ad.get("selling_price", 0)), key=f"price_{ad.get('id')}")
                        new_stock = st.number_input("Update Stock", value=int(ad.get("current_stock", 0)), key=f"stock_{ad.get('id')}")
                    with col2:
                        st.write(f"**Original Price:** Rs. {ad.get('original_price'):,.2f}")
                        st.write(f"**Category:** {ad.get('category')}")
                        st.write(f"**Valid Till:** {ad.get('end_date')}")

                    c_upd, c_del = st.columns(2)
                    with c_upd:
                        if st.button("🔄 Update Ad", key=f"upd_btn_{ad.get('id')}"):
                            database.supabase.table("promotions_arrivals").update({
                                "selling_price": new_sell_price,
                                "current_stock": new_stock
                            }).eq("id", ad.get("id")).execute()
                            st.success("✅ දැන්වීම යාවත්කාලීන කරන ලදී!")
                            st.rerun()
                            
                    with c_del:
                        if st.button("🗑️ Delete Ad", key=f"del_btn_{ad.get('id')}"):
                            database.supabase.table("promotions_arrivals").delete().eq("id", ad.get("id")).execute()
                            st.warning("🗑️ දැන්වීම ඉවත් කරන ලදී!")
                            st.rerun()
                            
    except Exception as e:
        st.warning(f"⚠️ Error loading management table: {e}")