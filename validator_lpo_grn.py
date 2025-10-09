import os
from datetime import datetime
from io import BytesIO

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import operator as op

st.set_page_config(page_title="Enhanced LPO-GRN Dashboard", layout="wide")

# ---------- Auto-refresh hook ----------
# If Power Automate calls your app like: https://your-app/?refresh=true
# the cache will be cleared and data reloaded from disk (data.xlsx).
params = st.experimental_get_query_params()
if "refresh" in params:
    # Clear the cached loader so next load reads fresh file
    try:
        st.cache_data.clear()
    except Exception:
        pass
    st.session_state["last_refresh"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# show last refresh (if any)
if "last_refresh" in st.session_state:
    st.sidebar.info(f"Last refresh: {st.session_state['last_refresh']}")

st.title("📊 Enhanced LPO-GRN")

# ---------- Helper: load dataframe ----------
@st.cache_data
def load_data(uploaded_file=None, local_path="data.xlsx"):
    """
    Load data from uploaded_file (if provided) else from local_path (if exists).
    Returns DataFrame or None.
    """
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    elif os.path.exists(local_path):
        df = pd.read_excel(local_path)
    else:
        return None

    df.columns = [str(c).strip() for c in df.columns]

    # Try to convert any date-like columns to datetime for safer filtering
    for col in df.columns:
        try:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        except Exception:
            pass

    return df

# ---------- Upload Excel (optional) ----------
uploaded_file = st.file_uploader("Upload your Excel file (or place data.xlsx next to the app)", type=["xlsx", "xls", "csv"])

# load df either from upload or from local 'data.xlsx'
df = load_data(uploaded_file, local_path="data.xlsx")

if df is None:
    st.info("No data loaded yet. Upload a file or place `data.xlsx` on the app server and call the app with ?refresh=true after Power Automate updates it.")
    st.stop()

st.subheader("Data Preview")
st.dataframe(df.head(20))

# ---------- Detect categorical columns ----------
categorical_cols = [col for col in df.columns if df[col].nunique() < 20]

# ---------- Sidebar Filters ----------
st.sidebar.header("Filter Options")

selected_values = {}
for col in categorical_cols:
    options = ["All"] + sorted(df[col].dropna().unique())
    selected_values[col] = st.sidebar.selectbox(f"{col}:", options, key=f"{col}_key")

st.sidebar.subheader("Additional Condition Filters")
num_col = st.sidebar.selectbox("Select Column", df.columns)
operator_str = st.sidebar.selectbox("Select Operator", [">", "<", "==", ">=", "<=", "!="])
compare_type = st.sidebar.radio("Compare With", ["Value", "Another Column"])
value_input, col2 = None, None
if compare_type == "Value":
    value_input = st.sidebar.text_input("Enter Value")
else:
    col2 = st.sidebar.selectbox("Select Column to Compare", df.columns)

# Robust date range inputs (only if column has at least one valid date)
def get_date_range_for_widget(df, column):
    if column in df.columns:
        s = pd.to_datetime(df[column], errors="coerce").dropna()
        if not s.empty:
            return s.min().date(), s.max().date()
    return None, None

if "lpo_date" in df.columns:
    lpo_min, lpo_max = get_date_range_for_widget(df, "lpo_date")
    lpo_range = None
    if lpo_min and lpo_max:
        lpo_range = st.sidebar.date_input("LPO Date Range", [lpo_min, lpo_max], key="lpo_range")
else:
    lpo_range = None

if "grn_date" in df.columns:
    grn_min, grn_max = get_date_range_for_widget(df, "grn_date")
    grn_range = None
    if grn_min and grn_max:
        grn_range = st.sidebar.date_input("GRN Date Range", [grn_min, grn_max], key="grn_range")
else:
    grn_range = None

# ---------- Button to apply filters ----------
if st.sidebar.button("Enter / Apply Filters"):
    filtered_df = df.copy()

    # categorical filters
    for col, val in selected_values.items():
        if val != "All":
            filtered_df = filtered_df[filtered_df[col] == val]

    ops = {">": op.gt, "<": op.lt, "==": op.eq, ">=": op.ge, "<=": op.le, "!=": op.ne}
    # numeric / column filter
    try:
        if compare_type == "Value" and value_input:
            try:
                val = float(value_input)
                mask = ops[operator_str](filtered_df[num_col].astype(float), val)
                filtered_df = filtered_df[mask]
            except Exception:
                mask = ops[operator_str](filtered_df[num_col].astype(str), str(value_input))
                filtered_df = filtered_df[mask]
        elif compare_type == "Another Column" and col2:
            mask = ops[operator_str](filtered_df[num_col], filtered_df[col2])
            filtered_df = filtered_df[mask]
    except Exception as e:
        st.error(f"Error applying numeric filter: {e}")

    # date range filters
    if lpo_range:
        filtered_df = filtered_df[
            (pd.to_datetime(filtered_df["lpo_date"]) >= pd.to_datetime(lpo_range[0])) &
            (pd.to_datetime(filtered_df["lpo_date"]) <= pd.to_datetime(lpo_range[1]))
        ]
    if grn_range:
        filtered_df = filtered_df[
            (pd.to_datetime(filtered_df["grn_date"]) >= pd.to_datetime(grn_range[0])) &
            (pd.to_datetime(filtered_df["grn_date"]) <= pd.to_datetime(grn_range[1]))
        ]

    # ---------- Display Results ----------
    if filtered_df.empty:
        st.warning("⚠️ No rows matched your filters.")
    else:
        st.subheader("Filtered Data")
        st.dataframe(filtered_df.head(50))

        # ---------- Filter Summary Pie Chart ----------
        total_records = len(df)
        filtered_records = len(filtered_df)
        remaining_records = total_records - filtered_records

        summary_data = pd.DataFrame({
            "Category": ["Filtered Data", "Remaining Data"],
            "Count": [filtered_records, remaining_records]
        })

        fig_summary = px.pie(
            summary_data,
            values="Count",
            names="Category",
            title=f"📊 Filtered vs Total Records (Total: {total_records})",
            color_discrete_sequence=px.colors.sequential.RdBu,
            hole=0.3
        )
        fig_summary.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_summary, use_container_width=True)

        # ---------- Convert date columns before saving (format as text for Excel preview) ----------
        df_to_save = filtered_df.copy()
        for c in df_to_save.columns:
            if "date" in c.lower():
                # keep underlying values as datetime when saving to real Excel later;
                # here we format to YYYY-MM-DD for the preview/Excel cells that might be text
                df_to_save[c] = pd.to_datetime(df_to_save[c], errors="coerce").dt.strftime("%Y-%m-%d")

        # ---------- Save properly formatted Excel (auto-adjust column widths) ----------
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter", datetime_format="yyyy-mm-dd", date_format="yyyy-mm-dd") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Filtered Data")  # write original datetimes
            worksheet = writer.sheets["Filtered Data"]
            for i, col in enumerate(filtered_df.columns):
                max_len = max(filtered_df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)

        st.download_button(
            label="📥 Download Filtered Data as Excel",
            data=output.getvalue(),
            file_name="filtered_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
