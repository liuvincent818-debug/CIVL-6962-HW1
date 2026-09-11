import streamlit as st
import pandas as pd

st.title("CIVL 6962 Dashboard")
st.write("11:35 Test")

df = pd.read_parquet("C:\\Users\\liuvi\\Downloads\\Machine Learning\\HW1 Database\\yellow_2024-03.parquet")
