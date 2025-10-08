import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import operator as op
import io

st.set_page_config(page_title="Enhanced LPO-GRN Dashboard", layout="wide")
st.title("📊 Enhanced LPO-GRN Dashboard")

# ---------- Upload Excel ----------
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls", "csv"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]

    st.subheader("Data Preview")
    st.dataframe(df.head(20))

    # ---------- Detect categorical columns ----------
    categorical_cols = [col for col in df.columns if df[col].nunique() < 20]

    # ---------- Sidebar Filters ----------
    st.sidebar.header("Filter Options")

    # Categorical Filters
    selected_values = {}
    for col in categorical_cols:
        options = ["All"] + sorted(df[col].dropna().unique())
        selected_values[col] = st.sidebar.selectbox(f"{col}:", options, key=f"{col}_key")

    # Numeric / Date Filter
    st.sidebar.subheader("Additional Condition Filters")
    num_col = st.sidebar.selectbox("Select Column", df.columns, key="num_col")
    operator_str = st.sidebar.selectbox("Select Operator", [">", "<", "==", ">=", "<=", "!="], key="op")
    compare_type = st.sidebar.radio("Compare With", ["Value", "Another Column"], key="compare_type")
    value_input = None
    col2 = None
    if compare_type == "Value":
        value_input = st.sidebar.text_input("Enter Value", key="val_input")
    else:
        col2 = st.sidebar.selectbox("Select Column to Compare", df.columns, key="col2")

    # Date range filters
    if "lpo_date" in df.columns:
        lpo_min = pd.to_datetime(df["lpo_date"].min())
        lpo_max = pd.to_datetime(df["lpo_date"].max())
        lpo_range = st.sidebar.date_input("LPO Date Range", [lpo_min, lpo_max], key="lpo_range")
    else:
        lpo_range = None

    if "grn_date" in df.columns:
        grn_min = pd.to_datetime(df["grn_date"].min())
        grn_max = pd.to_datetime(df["grn_date"].max())
        grn_range = st.sidebar.date_input("GRN Date Range", [grn_min, grn_max], key="grn_range")
    else:
        grn_range = None

    # ---------- Button to apply filters ----------
    if st.sidebar.button("Enter / Apply Filters"):
        filtered_df = df.copy()

        # Apply categorical filters
        for col, val in selected_values.items():
            if val != "All":
                filtered_df = filtered_df[filtered_df[col] == val]

        # Operator mapping
        ops = {">": op.gt, "<": op.lt, "==": op.eq, ">=": op.ge, "<=": op.le, "!=": op.ne}

        # Apply numeric/date filter
        try:
            if compare_type == "Value" and value_input:
                try:
                    val = float(value_input)
                    mask = ops[operator_str](filtered_df[num_col].astype(float), val)
                    filtered_df = filtered_df[mask]
                except:
                    mask = ops[operator_str](filtered_df[num_col].astype(str), str(value_input))
                    filtered_df = filtered_df[mask]
            elif compare_type == "Another Column" and col2:
                mask = ops[operator_str](filtered_df[num_col], filtered_df[col2])
                filtered_df = filtered_df[mask]
        except Exception as e:
            st.error(f"Error applying numeric filter: {e}")

        # Apply date range filters
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





            # ---------- Download CSV ----------
            csv = filtered_df.to_csv(index=False)
            st.download_button("Download Filtered Data as CSV", csv, "filtered_data.csv", "text/csv")

            # ---------- Download Excel with proper date format ----------
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter', datetime_format='yyyy-mm-dd', date_format='yyyy-mm-dd') as writer:
                filtered_df.to_excel(writer, index=False, sheet_name='Filtered Data')
            st.download_button(
                label="Download Filtered Data as Excel",
                data=output.getvalue(),
                file_name="filtered_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
