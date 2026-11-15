import streamlit as st
import database
import pandas as pd

def render_transaction_history_tab():
    st.markdown("### 📜 Transaction History")
    st.info("ℹ️ View your past purchase and payment history across retail shops.")

    current_customer_user = st.session_state.get("username")
    if not current_customer_user:
        st.error("❌ Please log in as a customer to view your history.")
        return

    try:
        if hasattr(database, 'supabase'):
            # Fetching sales data from 'shop_sales' table
            res = database.supabase.table("shop_sales").select("*").order("created_at", desc=True).execute()
            sales_data = res.data if res.data else []

            if not sales_data:
                st.warning("ℹ️ No transaction history found.")
                return

            df_sales = pd.DataFrame(sales_data)

            # --- CSS Styling for Clean Table / Cards ---
            st.markdown("""
                <style>
                .history-card {
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 12px 16px;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.02);
                }
                .history-header {
                    font-size: 13px;
                    font-weight: 700;
                    color: #4a5568;
                    margin-bottom: 4px;
                }
                .history-title {
                    font-size: 16px;
                    font-weight: 700;
                    color: #1a202c;
                }
                .history-amount {
                    font-size: 16px;
                    font-weight: 800;
                    color: #0d9488;
                    text-align: right;
                }
                </style>
            """, unsafe_allow_html=True)

            # Displaying summary metrics or total transactions
            st.metric(total_transactions := "Total Records", value=len(df_sales))
            st.markdown("---")

            # Listing transactions in a sleek card format
            for idx, row in df_sales.iterrows():
                item_name = row.get("item_name", "Item")
                shop_name = row.get("shop_name", "Retail Shop")
                qty = row.get("sold_qty", 1)
                unit_price = float(row.get("unit_price", 0))
                total_amount = float(row.get("total_amount", 0))
                payment_method = row.get("payment_method", "Pi Wallet")
                created_at = row.get("created_at", "")

                # Format timestamp nicely if available
                date_str = created_at.split("T")[0] if created_at else "Recent"

                st.markdown(f"""
                <div class="history-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div class="history-header">🏪 {shop_name} &nbsp;|&nbsp; 📅 {date_str}</div>
                            <div class="history-title">{item_name} (Qty: {qty})</div>
                            <div style="font-size: 12px; color: #718096; margin-top: 2px;">Payment Method: <b>{payment_method}</b></div>
                        </div>
                        <div class="history-amount">
                            Rs. {total_amount:,.2f}<br>
                            <span style="font-size: 11px; font-weight: normal; color: #a0aec0;">@ Rs. {unit_price:,.2f} each</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Error loading transaction history: {e}")