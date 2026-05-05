import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Order Risk Dashboard", layout="wide")

st.title("📦 Order Risk Dashboard (Advanced)")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

def clean_phone(x):
    digits = re.sub(r'\D', '', str(x))
    return digits[-10:] if len(digits) >= 10 else digits

def word_count(text):
    return len(str(text).split())

def has_number(text):
    return any(char.isdigit() for char in str(text))

def valid_pincode(pin):
    return str(pin).isdigit() and len(str(pin)) == 6

def has_weak_keyword(text):
    text = str(text).lower()
    keywords = ["near", "opp", "behind", "village", "pg", "hostel"]
    return any(k in text for k in keywords)

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    cols = df.columns

    order_col = [c for c in cols if 'order' in c.lower()][0]
    qty_col = [c for c in cols if 'quantity' in c.lower()][0]
    phone_col = [c for c in cols if 'phone' in c.lower() or 'mobile' in c.lower()][0]
    address_col = [c for c in cols if 'address' in c.lower()][0]
    cust_count_col = [c for c in cols if 'customer' in c.lower() and 'count' in c.lower()][0]
    pincode_col = [c for c in cols if 'pin' in c.lower()][0]

    # Clean phone
    df['Clean_Phone'] = df[phone_col].apply(clean_phone)

    # Quantity aggregation
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

    # Address features
    df['Word_Count'] = df[address_col].apply(word_count)
    df['Has_Number'] = df[address_col].apply(has_number)
    df['Valid_Pincode'] = df[pincode_col].apply(valid_pincode)
    df['Weak_Address'] = df[address_col].apply(has_weak_keyword)

    # Address quality
    def address_quality(row):
        if row['Word_Count'] < 4 or not row['Has_Number'] or not row['Valid_Pincode']:
            return "LOW"
        elif row['Word_Count'] < 7 or row['Weak_Address']:
            return "MEDIUM"
        return "HIGH"

    df['Address_Quality'] = df.apply(address_quality, axis=1)

    # Remarks
    def build_remark(row):
        reasons = []
        if row['Word_Count'] < 4:
            reasons.append("Short Address")
        if not row['Has_Number']:
            reasons.append("No House Number")
        if not row['Valid_Pincode']:
            reasons.append("Invalid Pincode")
        if row['Weak_Address']:
            reasons.append("Vague Address")
        if row['Flag_Multi_Qty']:
            reasons.append("Multi Quantity")
        if row['Flag_Repeat_In_Sheet']:
            reasons.append("Repeat Phone")
        if row['Flag_Past_Customer']:
            reasons.append("Past Customer")
        return ", ".join(reasons)

    df['Remark'] = df.apply(build_remark, axis=1)

    # Final decision
    def decide(row):
        if row['Address_Quality'] == 'LOW':
            return 'CALL'
        if row['Flag_Repeat_In_Sheet'] and row['Flag_Multi_Qty']:
            return 'CALL'
        if row['Flag_Past_Customer'] or row['Flag_Repeat_In_Sheet'] or row['Address_Quality'] == 'MEDIUM' or row['Flag_Multi_Qty']:
            return 'WHATSAPP_CONFIRM'
        return 'AUTO_SHIP'

    df['Final_Action'] = df.apply(decide, axis=1)

    # 📊 DASHBOARD
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Orders", len(df))
    col2.metric("CALL", (df['Final_Action'] == 'CALL').sum())
    col3.metric("WHATSAPP", (df['Final_Action'] == 'WHATSAPP_CONFIRM').sum())
    col4.metric("AUTO SHIP", (df['Final_Action'] == 'AUTO_SHIP').sum())

    st.divider()

    # 🔥 Top Risk Orders
    st.subheader("🚨 Top Risk Orders (CALL)")
    st.dataframe(df[df['Final_Action'] == 'CALL'], use_container_width=True)

    st.divider()

    # Filter
    action_filter = st.selectbox("Filter by Action", ["ALL", "CALL", "WHATSAPP_CONFIRM", "AUTO_SHIP"])

    if action_filter != "ALL":
        df_display = df[df['Final_Action'] == action_filter]
    else:
        df_display = df

    st.dataframe(df_display, use_container_width=True)

    # Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Processed File", csv, "processed_orders.csv", "text/csv")
