import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Smart LPO-GRN Filter", layout="wide")
st.title("🔍 Smart Filter Dashboard")

# ---------- Upload Excel ----------
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls", "csv"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    st.subheader("Data Preview")
    st.dataframe(df.head(20))
    
    # ---------- Detect categorical columns ----------
    categorical_cols = [col for col in df.columns if df[col].nunique() < 20]
    
    st.subheader("Filter by Unique Values")
    selected_values = {}
    for col in categorical_cols:
        options = ["All"] + sorted(df[col].dropna().unique())
        selected_values[col] = st.selectbox(f"{col}:", options)
    
    # Apply categorical filters
    filtered_df = df.copy()
    for col, val in selected_values.items():
        if val != "All":
            filtered_df = filtered_df[filtered_df[col] == val]
    
    # ---------- Additional dynamic filter ----------
    st.subheader("Additional Condition Filter")
    col1 = st.selectbox("Select Column", df.columns)
    operator = st.selectbox("Select Operator", [">", "<", "==", ">=", "<=", "!="])
    compare_type = st.radio("Compare With", ["Value", "Another Column"])
    
    value_input = None
    col2 = None
    if compare_type == "Value":
        value_input = st.text_input("Enter Value")
    else:
        col2 = st.selectbox("Select Column to Compare", df.columns)
    
    # Apply condition filter
    if st.button("Apply Filters"):
        temp_df = filtered_df.copy()
        try:
            if compare_type == "Value" and value_input:
                try:
                    val = float(value_input)
                    temp_df = temp_df[temp_df[col1].astype(float).eval(f"{operator}{val}")]
                except:
                    temp_df = temp_df[temp_df[col1].astype(str).eval(f"{operator}'{value_input}'")]
            elif compare_type == "Another Column" and col2:
                temp_df = temp_df[temp_df[col1].eval(f"{operator} {col2}")]
            
            if temp_df.empty:
                st.warning("⚠️ No rows matched your filter.")
            else:
                st.dataframe(temp_df)
                st.success(f"✅ {len(temp_df)} rows matched your criteria.")
                
                # Download filtered results
                csv = temp_df.to_csv(index=False)
                st.download_button("Download Filtered Data as CSV", csv, "filtered_data.csv", "text/csv")
        except Exception as e:
            st.error(f"Error: {e}")
