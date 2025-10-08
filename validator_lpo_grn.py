import streamlit as st
import pandas as pd

st.title("📦 LPO vs GRN Validation Tool")

# ---------- Upload Excel ----------
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # ---------- Clean Columns ----------
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # ---------- Supplier Filter ----------
    if "supplier" in df.columns:
        suppliers = df["supplier"].dropna().unique()
        selected_suppliers = st.multiselect(
            "Select Supplier(s)", options=suppliers, default=list(suppliers)
        )
        df = df[df["supplier"].isin(selected_suppliers)]

    # ---------- Convert to Dates ----------
    df["lpo_date"] = pd.to_datetime(df["lpo_date"], errors="coerce")
    df["grn_date"] = pd.to_datetime(df["grn_date"], errors="coerce")

    # ---------- Validation Checks ----------
    df["date_check"] = df.apply(
        lambda x: "✅ OK" if x["grn_date"] > x["lpo_date"] else "❌ Invalid (Delivered before order)",
        axis=1
    )

    df["qty_difference"] = df["received_qty"] - df["ordered_qty"]
    df["qty_status"] = df.apply(
        lambda x: "✅ Same"
        if x["qty_difference"] == 0
        else ("📈 More Received" if x["qty_difference"] > 0 else "📉 Less Received"),
        axis=1
    )

    # ---------- Display Results ----------
    st.subheader("📊 Validation Results")
    st.dataframe(df[[
        "supplier", "lpo_number", "lpo_date", "grn_number", "grn_date",
        "ordered_qty", "received_qty", "date_check", "qty_status"
    ]])

    # ---------- Summary ----------
    st.subheader("📋 Summary Insights")
    st.write(f"✅ Correct delivery dates: {(df['date_check'] == '✅ OK').sum()}")
    st.write(f"❌ Invalid date orders: {(df['date_check'] != '✅ OK').sum()}")
    st.write(f"📈 Over-received items: {(df['qty_difference'] > 0).sum()}")
    st.write(f"📉 Under-received items: {(df['qty_difference'] < 0).sum()}")
