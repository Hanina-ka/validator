import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

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
        selected_values[col] = st.sidebar.selectbox(f"{col}:", options)

    # Numeric / Date Filter
    st.sidebar.subheader("Additional Condition Filters")
    num_col = st.sidebar.selectbox("Select Column", df.columns)
    operator = st.sidebar.selectbox("Select Operator", [">", "<", "==", ">=", "<=", "!="])
    compare_type = st.sidebar.radio("Compare With", ["Value", "Another Column"])
    value_input = None
    col2 = None
    if compare_type == "Value":
        value_input = st.sidebar.text_input("Enter Value")
    else:
        col2 = st.sidebar.selectbox("Select Column to Compare", df.columns)

    # Date range filter (for LPO / GRN dates if present)
    if "lpo_date" in df.columns:
        lpo_min = pd.to_datetime(df["lpo_date"].min())
        lpo_max = pd.to_datetime(df["lpo_date"].max())
        lpo_range = st.sidebar.date_input("LPO Date Range", [lpo_min, lpo_max])
    else:
        lpo_range = None

    if "grn_date" in df.columns:
        grn_min = pd.to_datetime(df["grn_date"].min())
        grn_max = pd.to_datetime(df["grn_date"].max())
        grn_range = st.sidebar.date_input("GRN Date Range", [grn_min, grn_max])
    else:
        grn_range = None

    # ---------- Apply Filters ----------
    filtered_df = df.copy()

    # Apply categorical filters
    for col, val in selected_values.items():
        if val != "All":
            filtered_df = filtered_df[filtered_df[col] == val]

    # Apply numeric/date filter
    try:
        if compare_type == "Value" and value_input:
            try:
                val = float(value_input)
                filtered_df = filtered_df[filtered_df[num_col].astype(float).eval(f"{operator}{val}")]
            except:
                filtered_df = filtered_df[filtered_df[num_col].astype(str).eval(f"{operator}'{value_input}'")]
        elif compare_type == "Another Column" and col2:
            filtered_df = filtered_df[filtered_df[num_col].eval(f"{operator}{col2}")]
    except Exception as e:
        st.error(f"Error applying numeric filter: {e}")

    # Apply date range filter
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

    if filtered_df.empty:
        st.warning("⚠️ No rows matched your filters.")
    else:
        # ---------- Color-coded table ----------
        def color_row(row):
            color = []
            for col in filtered_df.columns:
                if col.lower() in ["grn_date", "lpo_date"]:
                    if "grn_date" in filtered_df.columns and "lpo_date" in filtered_df.columns:
                        if row["grn_date"] < row["lpo_date"]:
                            color.append("background-color: #ff9999")  # red
                        else:
                            color.append("")
                    else:
                        color.append("")
                elif col.lower() in ["ordered_qty", "received_qty"]:
                    if row["received_qty"] > row["ordered_qty"]:
                        color.append("background-color: #99ff99")  # green
                    elif row["received_qty"] < row["ordered_qty"]:
                        color.append("background-color: #ffcc99")  # orange
                    else:
                        color.append("")
                else:
                    color.append("")
            return color

        st.subheader("Filtered Data (Color-coded)")
        st.dataframe(filtered_df.style.apply(color_row, axis=1))

        # ---------- Dashboard / KPIs ----------
        st.subheader("📈 Dashboard Insights")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Total Orders", len(filtered_df))
        if "lpo_date" in filtered_df.columns and "grn_date" in filtered_df.columns:
            valid_dates = (filtered_df["grn_date"] >= filtered_df["lpo_date"]).sum()
            col_b.metric("Valid Deliveries", valid_dates)
        if "ordered_qty" in filtered_df.columns and "received_qty" in filtered_df.columns:
            over_received = (filtered_df["received_qty"] > filtered_df["ordered_qty"]).sum()
            under_received = (filtered_df["received_qty"] < filtered_df["ordered_qty"]).sum()
            col_c.metric("Over Received", over_received)
            col_d.metric("Under Received", under_received)

        # ---------- Bar charts for categorical columns ----------
        for cat_col in categorical_cols:
            fig = px.bar(filtered_df[cat_col].value_counts().reset_index(),
                         x='index', y=cat_col, title=f"Distribution of {cat_col}")
            st.plotly_chart(fig, use_container_width=True)

        # ---------- Histograms for numeric columns ----------
        numeric_cols = filtered_df.select_dtypes(include=np.number).columns
        for num_col in numeric_cols:
            fig = px.histogram(filtered_df, x=num_col, nbins=20, title=f"{num_col} Distribution")
            st.plotly_chart(fig, use_container_width=True)

        # ---------- Download Filtered Results ----------
        csv = filtered_df.to_csv(index=False)
        st.download_button("Download Filtered Data as CSV", csv, "filtered_data.csv", "text/csv")
