import streamlit as st
import os
import importlib.util

def load_tab_module(file_path, module_name):
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        st.error(f"Error loading module {module_name}: {e}")
        return None

def render_page():
    st.markdown("## 🏪 Retail Shop Portal (Retailer Dashboard)")
    st.info("Manage your Point of Sale (POS), inventory, promotions, staff sub-accounts, and sales settlements.")
    
    # ටැබ් 5 නිර්මාණය කිරීම
    tab_names = [
        "🛒 POS Billing", 
        "📦 Inventory", 
        "🏷️ Promotion", 
        "👤 Profile & Staff", 
        "💰 Sales & Settlement"
    ]
    
    tabs = st.tabs(tab_names)
    
    # 1. POS Billing Tab
    with tabs[0]:
        path = os.path.join("shop_tabs", "tab1_pos_billing.py")
        mod = load_tab_module(path, "tab1_pos_billing")
        if mod and hasattr(mod, "render"):
            mod.render()
        else:
            st.warning("Please ensure 'shop_tabs/tab1_pos_billing.py' exists.")

    # 2. Inventory Tab (Stock In & QR)
    with tabs[1]:
        path = os.path.join("shop_tabs", "tab3_inventory.py")
        mod = load_tab_module(path, "tab3_inventory")
        if mod and hasattr(mod, "render"):
            mod.render()
        else:
            st.warning("Please ensure 'shop_tabs/tab3_inventory.py' exists.")

    # 3. Promotion Tab
    with tabs[2]:
        path = os.path.join("shop_tabs", "tab2_promotion.py")
        mod = load_tab_module(path, "tab2_promotion")
        if mod and hasattr(mod, "render"):
            mod.render()
        else:
            st.warning("Please ensure 'shop_tabs/tab2_promotion.py' exists.")

    # 4. Profile & Staff Tab
    with tabs[3]:
        path = os.path.join("shop_tabs", "tab5_profile_wallet.py")
        mod = load_tab_module(path, "tab5_profile_wallet")
        if mod and hasattr(mod, "render"):
            mod.render()
        else:
            st.warning("Please ensure 'shop_tabs/tab5_profile_wallet.py' exists.")

    # 5. Sales & Settlement Tab
    with tabs[4]:
        path = os.path.join("shop_tabs", "tab4_sales_settlement.py")
        mod = load_tab_module(path, "tab4_sales_settlement")
        if mod and hasattr(mod, "render"):
            mod.render()
        else:
            st.warning("Please ensure 'shop_tabs/tab4_sales_settlement.py' exists.")
