import streamlit as st
import pandas as pd

st.title("CIVL 6962 Dashboard")
st.write("11:35 Test")

@st.cache_data
def load_data(url):
    return pd.read_parquet(url)
RAW = "https://github.com/liuvincent818-debug/CIVL-6962-HW1/raw/refs/heads/main/yellow_2024-03.parquet"


df = load_data(RAW)
st.dataframe(df)