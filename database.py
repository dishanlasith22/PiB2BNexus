import streamlit as st
from supabase import create_client, Client

# Supabase URL සහ Key එක කෙලින්ම ලබා දීම (හෝ st.secrets භාවිත කරන්නේ නම් නිවැරදි Keys මඟින්)
SUPABASE_URL = "https://prqgmqisnwabhpetdjzx.supabase.co"
SUPABASE_KEY = "sb_publishable_2UyjDSqXYF2KKrw22d68BQ_BecGxidg"

# ⚠️ 💡 ඔබගේ (פלאットフォーム අයිතිකරුගේ) නිල Pi Mainnet Wallet Address එක මෙතැනට දාන්න
ADMIN_PI_WALLET_ADDRESS = "GXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

@st.cache_resource
def init_connection() -> Client:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_connection()



# --- 1. ඩීලර් විසින් අයිතමයක් රෙජිස්ටර් කිරීම ---
def register_product(dealer_id, barcode, item_name, buying_price, selling_price, stock_qty):
    try:
        data = {
            "dealer_id": dealer_id,
            "barcode": barcode,
            "item_name": item_name,
            "buying_price": buying_price,
            "selling_price": selling_price,
            "stock_qty": stock_qty
        }
        if supabase:
            supabase.table("products").insert(data).execute()
        return True, "Item successfully registered in database!"
    except Exception as e:
        return False, str(e)

# --- 2. බාර්කෝඩ් එක මඟින් අයිතමය සෙවීම ---
def fetch_product_by_barcode(barcode):
    try:
        if supabase:
            response = supabase.table("products").select("*").eq("barcode", barcode).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
        # Fallback sample data for local testing
        sample_db = {
            "6928802587458": {"name": "Cinnamon Export Grade (100g)", "selling_price": 450.00, "stock_qty": 50},
            "4790012001234": {"name": "Black Pepper Pure (250g)", "selling_price": 350.00, "stock_qty": 30}
        }
        return sample_db.get(barcode)
    except Exception as e:
        return None

# --- 3. බිල්පත් ගනුදෙනු සහ අනිවාර්ය 1% Level 3 Referral බෙදා හැරීම ---
def complete_bill_and_process_referral(shop_id, customer_username, total_amount, cart_items):
    try:
        # අනිවාර්ය 1% රෙෆරල් බෝනස් එක මුළු බිල් මුදලින් ගණනය කිරීම
        total_referral_bonus = total_amount * 0.01 
        
        # Level 3 Referral බෙදීම (L1 = 0.5%, L2 = 0.3%, L3 = 0.2%)
        l1_bonus = total_referral_bonus * 0.50
        l2_bonus = total_referral_bonus * 0.30
        l3_bonus = total_referral_bonus * 0.20
        
        # ඩේටාබේස් වෙත ට්‍රාන්සැක්ෂන් එක සේව් කිරීම
        transaction_data = {
            "shop_id": shop_id,
            "customer": customer_username,
            "total_amount": total_amount,
            "total_referral_bonus": total_referral_bonus,
            "items": str(cart_items)
        }
        if supabase:
            supabase.table("transactions").insert(transaction_data).execute()
            
        return True, total_referral_bonus, (l1_bonus, l2_bonus, l3_bonus)
    except Exception as e:
        return False, 0.0, (0, 0, 0)

# --- 4. දෛනික සෙට්ල්මන්ට් සහ 0.5% Ecosystem Fee (ඔබේ Admin Wallet වෙත යැවීම) ---
def process_daily_settlement_for_admin(total_daily_sales):
    try:
        ecosystem_fee_05 = total_daily_sales * 0.005
        dealer_payout = total_daily_sales - ecosystem_fee_05
        
        settlement_record = {
            "total_sales": total_daily_sales,
            "admin_wallet": ADMIN_PI_WALLET_ADDRESS,
            "ecosystem_fee_05": ecosystem_fee_05,
            "dealer_net_payout": dealer_payout,
            "status": "Ready for Pi Mainnet Transfer"
        }
        
        if supabase:
            supabase.table("daily_settlements").insert(settlement_record).execute()
            
        return True, ecosystem_fee_05, ADMIN_PI_WALLET_ADDRESS
    except Exception as e:
        return False, 0.0, ""
    
    
# --- ඩීලර්ගේ ප්‍රොෆයිල්, වොලට් සහ රෙජිස්ටර් කෝඩ් සේව් / අප්ඩේට් කිරීම ---
def save_or_update_dealer_profile(pi_username, company_name, phone_number, address, wallet_address, register_code):
    try:
        global supabase
        if supabase:
            data = {
                "pi_username": pi_username,
                "company_name": company_name,
                "phone_number": phone_number,
                "address": address,
                "wallet_address": wallet_address,
                "register_code": register_code,
                "kyc_verified": True
            }
            supabase.table("dealers").upsert(data, on_conflict="pi_username").execute()
            return True, "Dealer profile, wallet and register code successfully saved!"
    except Exception as e:
        return False, str(e)

# --- 2. ඩීලර්ගේ ප්‍රොފައިල් විස්තර ලබා ගැනීම ---
def get_dealer_profile(pi_username):
    try:
        if supabase:
            response = supabase.table("dealers").select("*").eq("pi_username", pi_username).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
        return None
    except Exception as e:
        return None





 # --- අදාළ ඩීලර්ට පමණක් අයත් කැටලොග් අයිතම ලබා ගැනීම ---
def fetch_dealer_products(dealer_id):
    try:
        global supabase
        if supabase:
            response = supabase.table("products").select("item_name, barcode, selling_price, stock_qty").eq("dealer_id", dealer_id).execute()
            if response.data and len(response.data) > 0:
                return response.data
        return []
    except Exception as e:
        return []



    # 4. Registered Catalog Table View (ඩේටාබේස් එකෙන් ලයිව් දත්ත ලබා ගැනීම)
    st.markdown("---")
    st.markdown("### 📊 Existing Master Catalog Items")
    
    catalog_items = database.fetch_all_dealer_products()
    if catalog_items:
        st.table(catalog_items)
    else:
        st.info("No items registered in catalog yet, or database not connected.")


        # --- දෛනික විකුණුම්, මුළු මුදල සහ 11:59 PM ඩීලර් වොලට් සෙට්ල්මන්ට් ලබා ගැනීම ---
def fetch_dealer_daily_sales_with_settlement(target_date):
    try:
        global supabase
        if supabase:
            # transactions හෝ daily_settlements ටේබල් එකෙන් දත්ත ලබා ගැනීම
            response = supabase.table("daily_settlements").select(
                "shop_name, items_breakdown_summary, total_amount, dealer_settlement_amount, settlement_date"
            ).eq("settlement_date", target_date).execute()
            
            if response.data:
                return response.data
        return []
    except Exception as e:
        return []

# -- ORIGINAL YATA


# --- ඩීලර් විසින් QR ස්කෑන් කර ඩිලිවරි තහවුරු කිරීම සහ සියලු ටේබල් අප්ඩේට් කිරීම ---
def record_dealer_delivery(dealer_username, shop_name, items_summary, total_amount, delivery_date, delivery_time):
    try:
        global supabase
        if supabase:
            # 1. Deliveries ටේබල් එකට ඩේටා ඇතුළත් කිරීම
            delivery_data = {
                "dealer_username": dealer_username,
                "shop_name": shop_name,
                "items_summary": items_summary,
                "total_delivery_amount": total_amount,
                "delivery_date": delivery_date,
                "delivery_time": delivery_time
            }
            supabase.table("deliveries").insert(delivery_data).execute()
            
            # 2. Shop Stock ටේබල් එකට ස්ටොක් එක ඇතුළත් කිරීම
            stock_data = {
                "shop_name": shop_name,
                "item_name": items_summary,
                "barcode": "N/A",
                "current_stock": 10 # ඩිලිවරි කළ ප්‍රමාණය
            }
            supabase.table("shop_stock").insert(stock_data).execute()

            # 3. Daily Settlements (2 වන වගුව සඳහා JSON ඩේටා ඇතුළත් කිරීම)
            settlement_data = {
                "shop_name": shop_name,
                "items_json": {items_summary: 10},
                "total_amount": total_amount,
                "dealer_settlement_amount": total_amount * 0.9, # 90% ඩීලර් වොලට් එකට
                "settlement_date": delivery_date
            }
            supabase.table("daily_settlements").insert(settlement_data).execute()
            
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- දෛනික විකුණුම් සහ සෙට්ල්මන්ට් දත්ත ලබා ගැනීම ---
def fetch_dealer_daily_sales_with_settlement(target_date):
    try:
        global supabase
        if supabase:
            response = supabase.table("daily_settlements").select(
                "shop_name, items_json, total_amount, dealer_settlement_amount, settlement_date"
            ).eq("settlement_date", target_date).execute()
            if response.data:
                return response.data
        return []
    except Exception as e:
        return []

# --- MEKE UDA

    # --- අද දිනට අදාළ ඩීලර්ගේ ඩිලිවරි ප්‍රග්‍රස් දත්ත ලබා ගැනීම ---
def fetch_dealer_todays_deliveries(dealer_username, target_date):
    try:
        global supabase
        if supabase:
            response = supabase.table("deliveries").select(
                "shop_name, delivery_time, items_summary, total_delivery_amount"
            ).eq("dealer_username", dealer_username).eq("delivery_date", target_date).execute()
            
            if response.data:
                return response.data
        return []
    except Exception as e:
        return []


    # --- ඩීලර් විසින් රෙජිස්ටර් කළ සියලුම අයිතම කැටලොග් එකෙන් ලබා ගැනීම ---
def fetch_all_dealer_products():
    try:
        # මෙහිදී global supabase භාවිත කිරීමෙන් ඩේටාබේස් කනෙක්ෂන් එක නිවැරදිව ලබාගත හැක
        global supabase 
        if supabase:
            response = supabase.table("products").select("item_name, barcode, selling_price, stock_qty").execute()
            if response.data and len(response.data) > 0:
                return response.data
        return []
    except Exception as e:
        return []



    # --- 1. කඩවල් අනුව ඩීලර්ගේ භාණ්ඩවල ලයිව් ස්ටොක් ලබා ගැනීම ---
def fetch_dealer_shop_live_stock():
    try:
        global supabase
        if supabase:
            response = supabase.table("shop_stock").select("shop_name, item_name, barcode, current_stock").execute()
            if response.data:
                return response.data
        return []
    except Exception as e:
        return []


    # --- දෛනික විකුණුම් සහ අයිතම බ්‍රේක්ඩවුන් වගු දත්ත ලබා ගැනීම ---
def fetch_dealer_daily_sales_with_settlement(target_date):
    try:
        global supabase
        if supabase:
            response = supabase.table("daily_settlements").select(
                "shop_name, item_1_qty, item_2_qty, item_3_qty, item_4_qty, item_5_qty, total_amount, dealer_settlement_amount, settlement_date"
            ).eq("settlement_date", target_date).execute()
            if response.data:
                return response.data
        return []
    except Exception as e:
        return []


    # --- Shop Profile Functions ---
def save_or_update_shop_profile(pi_username, shop_name, phone_number, address, wallet_address, fb_page, web_url, register_code):
    try:
        global supabase
        if supabase:
            data = {
                "pi_username": pi_username,
                "shop_name": shop_name,
                "phone_number": phone_number,
                "address": address,
                "wallet_address": wallet_address,
                "fb_page": fb_page,
                "web_url": web_url,
                "register_code": register_code
            }
            supabase.table("shops").upsert(data, on_conflict="pi_username").execute()
            return True, "Shop profile and Register Code successfully saved to database!"
    except Exception as e:
        return False, str(e)

def get_shop_profile(pi_username):
    try:
        global supabase
        if supabase:
            res = supabase.table("shops").select("*").eq("pi_username", pi_username).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        return None
    except Exception:
        return None

# --- Branch Management Functions ---
def add_shop_branch(pi_username, branch_name):
    try:
        global supabase
        if supabase:
            supabase.table("shop_branches").insert({"pi_username": pi_username, "branch_name": branch_name}).execute()
            return True, "Branch added successfully!"
    except Exception as e:
        return False, str(e)

def fetch_shop_branches(pi_username):
    try:
        global supabase
        if supabase:
            res = supabase.table("shop_branches").select("*").eq("pi_username", pi_username).execute()
            return res.data if res.data else []
        return []
    except Exception:
        return []

def delete_shop_branch(branch_id):
    try:
        global supabase
        if supabase:
            supabase.table("shop_branches").delete().eq("id", branch_id).execute()
            return True, "Branch deleted successfully!"
    except Exception as e:
        return False, str(e)

# --- Staff Management Functions ---
def add_shop_staff(pi_username, staff_name, staff_pin, role, branch_name):
    try:
        global supabase
        if supabase:
            data = {
                "pi_username": pi_username,
                "staff_name": staff_name,
                "staff_pin": staff_pin,
                "role": role,
                "branch_name": branch_name
            }
            supabase.table("shop_staff").insert(data).execute()
            return True, "Staff member added successfully!"
    except Exception as e:
        return False, str(e)

def fetch_shop_staff(pi_username):
    try:
        global supabase
        if supabase:
            res = supabase.table("shop_staff").select("*").eq("pi_username", pi_username).execute()
            return res.data if res.data else []
        return []
    except Exception:
        return []

def delete_shop_staff(staff_id):
    try:
        global supabase
        if supabase:
            supabase.table("shop_staff").delete().eq("id", staff_id).execute()
            return True, "Staff member deleted successfully!"
    except Exception as e:
        return False, str(e)


def get_dealer_by_code(dealer_code):
    try:
        global supabase
        if supabase:
            # dealers ටේබල් එකෙන් register_code මඟින් ඩීලර් සෙවීම
            response = supabase.table("dealers").select("*").eq("register_code", dealer_code.strip()).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
        return None
    except Exception as e:
        return None

def fetch_dealer_catalog(dealer_identifier):
    try:
        global supabase
        if supabase:
            # 1. products ටේබල් එකේ dealer_id එක pi_username සමඟ මැච් කිරීම
            response = supabase.table("products").select("*").eq("dealer_id", dealer_identifier).execute()
            if response.data:
                return [item['item_name'] for item in response.data]
                
        return []
    except Exception as e:
        return []




from datetime import date

def check_and_revert_expired_promotions(shop_name):
    """ප්‍රමෝෂන් කාලය ඉවර වී ඇති නම්, shop_stock හි මිල මුල් මිලට (original_price) ස්වයංක්‍රීයව මාරු කිරීම"""
    today_str = str(date.today())
    try:
        # 💡 database.supabase වෙනුවට ඩේටාබේස් ෆයිල් එකේ ඇති supabase ඉන්ස්ටන්ස් එක පාවිච්චි කිරීම
        if 'supabase' in globals() or 'supabase' in locals():
            # අද දවසට අවසන් වූ ප්‍රමෝෂන් සෙවීම
            expired_res = supabase.table("promotions_arrivals").select("*").eq("shop_name", shop_name).lt("end_date", today_str).execute()
            
            if expired_res.data:
                for promo in expired_res.data:
                    item_name = promo.get("item_name")
                    orig_price = promo.get("original_price")
                    
                    # shop_stock හි මිල මුල් මිලටම (Original Price) යාවත්කාලීන කිරීම
                    supabase.table("shop_stock").update({
                        "custom_selling_price": orig_price,
                        "is_promotion": False
                    }).eq("shop_name", shop_name).eq("item_name", item_name).execute()
    except Exception as e:
        print(f"Error reverting prices: {e}")


    