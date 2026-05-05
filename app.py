import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Order Risk Dashboard", layout="wide")

st.title("📦 Order Risk Dashboard")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

def clean_phone(x):
    digits = re.sub(r'\D', '', str(x))
    return digits[-10:] if len(digits) >= 10 else digits

def address_quality(addr):
    if pd.isna(addr):
        return 'LOW'
    l = len(str(addr))
    if l < 20:
        return 'LOW'
    elif l < 40:
        return 'MEDIUM'
    return 'HIGH'

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    cols = df.columns

    order_col = [c for c in cols if 'order' in c.lower()][0]
    qty_col = [c for c in cols if 'quantity' in c.lower()][0]
    phone_col = [c for c in cols if 'phone' in c.lower() or 'mobile' in c.lower()][0]
    address_col = [c for c in cols if 'address' in c.lower()][0]
    cust_count_col = [c for c in cols if 'customer' in c.lower() and 'count' in c.lower()][0]

    # Clean phone
    df['Clean_Phone'] = df[phone_col].apply(clean_phone)

    # Total quantity per order
    order_qty = df.groupby(order_col)[qty_col].sum().reset_index()
    order_qty.columns = [order_col, 'Total_Quantity']
    df = df.merge(order_qty, on=order_col, how='left')

    df['Flag_Multi_Qty'] = df['Total_Quantity'] > 1

    # Repeat in sheet
    phone_orders = df.groupby('Clean_Phone')[order_col].nunique().reset_index()
    phone_orders.columns = ['Clean_Phone', 'Order_Count_In_Sheet']
    df = df.merge(phone_orders, on='Clean_Phone', how='left')

    df['Flag_Repeat_In_Sheet'] = df['Order_Count_In_Sheet'] > 1

    # Past customer
    df['Flag_Past_Customer'] = df[cust_count_col] > 1

    # Address quality
    df['Address_Quality'] = df[address_col].apply(address_quality)

def build_remark(row):
    reasons = []

    # Address-based
    if row['Address_Quality'] == 'LOW':
        reasons.append("Short Address")
    elif row['Address_Quality'] == 'MEDIUM':
        reasons.append("Moderate Address")

    # Quantity
    if row['Flag_Multi_Qty']:
        reasons.append("Multi Quantity")

    # Repeat
    if row['Flag_Repeat_In_Sheet']:
        reasons.append("Repeat Phone")

    # Past customer
    if row['Flag_Past_Customer']:
        reasons.append("Past Customer")

    return ", ".join(reasons)

df['Remark'] = df.apply(build_remark, axis=1)
    
    # Final decision logic
    def decide(row):
        if row['Address_Quality'] == 'LOW':
            return 'CALL'
        if row['Flag_Repeat_In_Sheet'] and row['Flag_Multi_Qty']:
            return 'CALL'
        if row['Flag_Past_Customer'] or row['Flag_Repeat_In_Sheet'] or row['Address_Quality'] == 'MEDIUM' or row['Flag_Multi_Qty']:
            return 'WHATSAPP_CONFIRM'
        return 'AUTO_SHIP'

    df['Final_Action'] = df.apply(decide, axis=1)

    # 📊 SUMMARY
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Orders", len(df))
    col2.metric("CALL", (df['Final_Action'] == 'CALL').sum())
    col3.metric("WHATSAPP", (df['Final_Action'] == 'WHATSAPP_CONFIRM').sum())
    col4.metric("AUTO SHIP", (df['Final_Action'] == 'AUTO_SHIP').sum())

    st.divider()

    # 🎯 FILTER
    action_filter = st.selectbox("Filter by Action", ["ALL", "CALL", "WHATSAPP_CONFIRM", "AUTO_SHIP"])

    if action_filter != "ALL":
        df_display = df[df['Final_Action'] == action_filter]
    else:
        df_display = df

    st.dataframe(df_display, use_container_width=True)

    # 📥 DOWNLOAD
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Processed File", csv, "processed_orders.csv", "text/csv")
