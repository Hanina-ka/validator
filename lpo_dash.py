import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import operator as op

st.set_page_config(page_title="Enhanced LPO-GRN Dashboard", layout="wide")
st.title("📊 Enhanced LPO-GRN Dashboard")

# ---------- Upload Excel ----------
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls", "csv"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Convert date-like columns
    for col in df.columns:
        try:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        except:
            pass

    # Display version of dataframe
    df_display = df.copy()
    for col in df_display.select_dtypes(include='datetime64[ns]').columns:
        df_display[col] = df_display[col].dt.strftime('%Y-%m-%d')

    st.subheader("Data Preview")
    st.dataframe(df_display.head(20))

    # ---------- Detect categorical columns ----------
    categorical_cols = [col for col in df.columns if df[col].nunique() < 20]

    # ---------- Sidebar Filters ----------
    st.sidebar.header("Filter Options")

    # Categorical Filters
    selected_values = {}
    for i, col in enumerate(categorical_cols):
        options = ["All"] + sorted(df[col].dropna().unique())
        selected_values[col] = st.sidebar.selectbox(f"{col}:", options, key=f"cat_{i}_{col}")

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
    date_cols = [c for c in df.select_dtypes(include='datetime64[ns]').columns]
    date_ranges = {}
    for i, col in enumerate(date_cols):
        if df[col].dropna().empty:
            continue
        min_date = df[col].min().date()
        max_date = df[col].max().date()
        date_ranges[col] = st.sidebar.date_input(f"{col} Date Range", [min_date, max_date], key=f"range_{i}_{col}")

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
        for col, date_range in date_ranges.items():
            if len(date_range) == 2:
                start_date = pd.to_datetime(date_range[0])
                end_date = pd.to_datetime(date_range[1])
                filtered_df = filtered_df[(filtered_df[col] >= start_date) & (filtered_df[col] <= end_date)]

        # ---------- Display Results ----------
        if filtered_df.empty:
            st.warning("⚠️ No rows matched your filters.")
        else:
            st.subheader("Filtered Data")
            df_display_filtered = filtered_df.copy()
            for col in df_display_filtered.select_dtypes(include='datetime64[ns]').columns:
                df_display_filtered[col] = df_display_filtered[col].dt.strftime('%Y-%m-%d')
            st.dataframe(df_display_filtered.head(50))

            # Dashboard KPIs
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Total Orders", len(filtered_df))
