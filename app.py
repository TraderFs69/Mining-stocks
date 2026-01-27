import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Scanner Minières", layout="wide")

st.title("⛏️ Scanner des minières canadiennes")

file = "Stock Minier.xlsx"

# Lire dynamiquement les onglets
xls = pd.ExcelFile(file)
sheet_names = xls.sheet_names

secteur = st.selectbox(
    "Secteur",
    sheet_names
)

exchange_filter = st.multiselect(
    "Exchange",
    ["TSX", "TSXV", "CSE"],
    default=["TSX", "TSXV", "CSE"]
)

col1, col2 = st.columns(2)

with col1:
    price_min = st.number_input(
        "Prix minimum ($)",
        min_value=0.0,
        value=0.0,
        step=0.1
    )

with col2:
    price_max = st.number_input(
        "Prix maximum ($)",
        min_value=0.0,
        value=10.0,
        step=0.5
    )

run = st.button("🚀 Lancer le scan")
