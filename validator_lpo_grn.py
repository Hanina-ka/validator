import os
from io import BytesIO
from datetime import datetime
import pandas as pd
import streamlit as st
import xlsxwriter

st.set_page_config(page_title="LPO-GRN Auto Check", layout="wide")
st.title("📊 LPO-GRN Date Check Dashboard")

# ---------- Auto-load Excel from repo ----------
DATA_FILE = "data.xlsx"  # Make sure this file exists in your repo

@st.cache_data
def load_data(file_path=DATA_FILE):
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df.columns = [str(c).strip() for c in df.columns]
        for col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except:
                pass
        return df
    else:
        st.warning(f"{file_path} not found in repo!")
        return None

df = load_data()
if df is None:
    st.stop()

st.subheader("Data Preview")
st.dataframe(df.head(20))

# ---------- Check LPO vs GRN ----------
if "lpo_date" in df.columns and "grn_date" in df.columns:
    # Warning conditions
    df["Warning"] = ""
    df.loc[df["grn_date"] > df["lpo_date"], "Warning"] = "GRN after LPO ⚠️"
    df.loc[df["grn_date"] < df["lpo_date"], "Warning"] = "GRN before LPO ⚠️"

    st.subheader("Date Check Results")
    st.dataframe(df[["lpo_date", "grn_date", "Warning"]].head(50))

    # Pie chart summary
    summary = df["Warning"].value_counts().reset_index()
    summary.columns = ["Warning", "Count"]
    import plotly.express as px
    fig = px.pie(summary, values="Count", names="Warning", title="📊 GRN vs LPO Warnings", hole=0.3)
    fig.update_traces(textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

# ---------- Save Excel with Warnings ----------
output = BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter", datetime_format="yyyy-mm-dd", date_format="yyyy-mm-dd") as writer:
    df.to_excel(writer, index=False, sheet_name="LPO-GRN Check")
    worksheet = writer.sheets["LPO-GRN Check"]
    for i, col in enumerate(df.columns):
        max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
        worksheet.set_column(i, i, max_len)

st.download_button(
    label="📥 Download Checked Excel",
    data=output.getvalue(),
    file_name="lpo_grn_checked.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
