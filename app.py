import streamlit as st
import pandas as pd

st.set_page_config(page_title="Order Address Checker", layout="wide")

st.title("📦 Address Quality Checker (Simple Rule)")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])


# -------------------------
# HELPER FUNCTIONS
# -------------------------

def char_count(text):
    return len(str(text).strip())

def word_count(text):
    return len(str(text).split())


# -------------------------
# MAIN LOGIC
# -------------------------

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    cols = df.columns

    # Auto-detect address column
    address_col = [c for c in cols if 'address' in c.lower()][0]

    # Create metrics
    df['Char_Count'] = df[address_col].apply(char_count)
    df['Word_Count'] = df[address_col].apply(word_count)

    # Address flag
    def address_flag(row):
        if row['Char_Count'] < 30 or row['Word_Count'] < 5:
            return "FLAG"
        return "OK"

    df['Address_Flag'] = df.apply(address_flag, axis=1)

    # Remark column
    def build_remark(row):
        reasons = []

        if row['Char_Count'] < 30:
            reasons.append("Less than 30 characters")

        if row['Word_Count'] < 5:
            reasons.append("Less than 5 words")

        return ", ".join(reasons)

    df['Remark'] = df.apply(build_remark, axis=1)

    # Final action
    def decide(row):
        if row['Address_Flag'] == "FLAG":
            return "CALL"
        return "AUTO_SHIP"

    df['Final_Action'] = df.apply(decide, axis=1)

    # -------------------------
    # DASHBOARD
    # -------------------------

    col1, col2 = st.columns(2)

    col1.metric("Total Orders", len(df))
    col2.metric("CALL Orders", (df['Final_Action'] == 'CALL').sum())

    st.divider()

    # Show CALL first (important for ops)
    st.subheader("🚨 Orders to CALL")
    st.dataframe(df[df['Final_Action'] == 'CALL'], use_container_width=True)

    st.divider()

    # Full data
    st.subheader("📊 All Orders")
    st.dataframe(df, use_container_width=True)

    # Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Processed File",
        csv,
        "processed_orders.csv",
        "text/csv"
    )
