import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import operator as op
from io import BytesIO

st.set_page_config(page_title="Enhanced LPO-GRN Dashboard", layout="wide")
st.title("📊 Enhanced LPO-GRN")

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

    if "lpo_date" in df.columns:
        lpo_min, lpo_max = pd.to_datetime(df["lpo_date"].min()), pd.to_datetime(df["lpo_date"].max())
        lpo_range = st.sidebar.date_input("LPO Date Range", [lpo_min, lpo_max])
    else:
        lpo_range = None

    if "grn_date" in df.columns:
        grn_min, grn_max = pd.to_datetime(df["grn_date"].min()), pd.to_datetime(df["grn_date"].max())
        grn_range = st.sidebar.date_input("GRN Date Range", [grn_min, grn_max])
    else:
        grn_range = None

    # ---------- Button to apply filters ----------
    if st.sidebar.button("Enter / Apply Filters"):
        filtered_df = df.copy()

        for col, val in selected_values.items():
            if val != "All":
                filtered_df = filtered_df[filtered_df[col] == val]

        ops = {">": op.gt, "<": op.lt, "==": op.eq, ">=": op.ge, "<=": op.le, "!=": op.ne}

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

            # ---------- Convert date columns before saving ----------
            for col in filtered_df.columns:
                if "date" in col.lower():
                    filtered_df[col] = pd.to_datetime(filtered_df[col], errors='coerce').dt.strftime("%Y-%m-%d")

            # ---------- Save properly formatted Excel ----------
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                filtered_df.to_excel(writer, index=False, sheet_name="Filtered Data")
                worksheet = writer.sheets["Filtered Data"]

                # Auto-adjust column width
                for i, col in enumerate(filtered_df.columns):
                    max_len = max(filtered_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, max_len)

            st.download_button(
                label="📥 Download Filtered Data as Excel",
                data=output.getvalue(),
                file_name="filtered_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
