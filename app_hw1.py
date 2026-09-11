import streamlit as st
import pandas as pd

st.title("CIVL 6962 Dashboard")
st.write("11:35 Test")

@st.cache_data
def load_data(url):
    return pd.read_parquet(url)
RAW = "https://github.com/liuvincent818-debug/CIVL-6962-HW1/raw/refs/heads/main/yellow_2024-03.parquet"

df = load_data(RAW)

filtered_df = df.copy()  # Create a copy to apply filters on

# 1. Check if the column exists in the DataFrame
if "category" in df.columns:
    # 2. Extract a sorted list of unique values, ignoring blank/NaN entries
    categories = sorted(df["category"].dropna().unique())
    
    # 3. Create the sidebar widget
    selected_categories = st.sidebar.multiselect(
        "Select Category",
        options=categories,
        default=categories  # All items selected when the page loads
    )
    
    # 4. Filter the DataFrame if the user hasn't unselected everything
    if selected_categories:
        filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)]

col1 = st.columns(1)
col1.metric("Total Rows", f"{len(filtered_df):,}")

st.dataframe(filtered_df)
