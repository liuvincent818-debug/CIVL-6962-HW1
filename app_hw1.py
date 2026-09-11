import streamlit as st
import pandas as pd

st.title("CIVL 6962 Dashboard")
st.write("11:35 Test")

@st.cache_data
def load_data():
    return pd.read_parquet(url)
url = "https://github.com/liuvincent818-debug/CIVL-6962-HW1/blob/main/yellow_2024-03.parquet"


df = load_data(url)
st.dataframe(df)