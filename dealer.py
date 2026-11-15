import streamlit as st
from dealer_tabs import tab1_handoff_qr, tab2_catalog, tab3_live_stock, tab4_delivery, tab5_profile_wallet

def render_page():
    st.title("📦 B2B Dealer Portal & Master Dashboard")
    
    t1, t2, t3, t4, t5 = st.tabs([
        "🔗 Stock Handoff (QR)", 
        "📋 Dealer Catalog", 
        "📊 Live Stock & Ledger", 
        "🚚 Delivery Progress", 
        "👤 Dealer Profile & Wallet"
    ])
    
    with t1:
        tab1_handoff_qr.render()
        
    with t2:
        tab2_catalog.render()
        
    with t3:
        tab3_live_stock.render()
        
    with t4:
        tab4_delivery.render()
        
    with t5:
        tab5_profile_wallet.render()