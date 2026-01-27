import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Scanner Minières", layout="wide")

# ======================
# FONCTIONS
# ======================

def yahoo_ticker(ticker, exchange):
    if exchange in ["TSX", "TSXV"]:
        return f"{ticker}.TO"
    elif exchange == "CSE":
        return f"{ticker}.CN"
    return ticker


def compute_returns(ticker):
    try:
        data = yf.download(ticker, period="1y", progress=False)

        if data.empty or "Close" not in data:
            return None

        close = data["Close"]
        last = close.iloc[-1]

        def ret(days):
            if len(close) > days:
                return (last / close.iloc[-days - 1] - 1) * 100
            return None

        return {
            "Price": round(float(last), 2),
            "1D %": round(ret(1), 2),
            "1W %": round(ret(5), 2),
            "1M %": round(ret(21), 2),
            "3M %": round(ret(63), 2),
            "6M %": round(ret(126), 2),
            "1Y %": round(ret(252), 2),
        }

    except Exception:
        return None


# ======================
# INTERFACE
# ======================

st.title("⛏️ Scanner des minières canadiennes")

file = "Stock Minier.xlsx"

secteur = st.selectbox(
    "Secteur",
    ["Gold", "Silver", "Copper", "Lithium"]
)

exchange_filter = st.multiselect(
    "Exchange",
    ["TSX", "TSXV", "CSE"],
    default=["TSX", "TSXV", "CSE"]
)

price_max = st.number_input(
    "Prix maximum ($)",
    min_value=0.0,
    value=10.0,
    step=0.5
)

run = st.button("🚀 Lancer le scan")

# ======================
# SCAN
# ======================

if run:
    with st.spinner("Téléchargement des données Yahoo Finance..."):

        df = pd.read_excel(file, sheet_name=secteur)
        df = df[df["Exchange"].isin(exchange_filter)]

        results = []

        for _, row in df.iterrows():
            yticker = yahoo_ticker(row["Ticker"], row["Exchange"])
            metrics = compute_returns(yticker)

            if metrics and metrics["Price"] <= price_max:
                results.append({
                    "Ticker": row["Ticker"],
                    "Company": row["Company"],
                    "Exchange": row["Exchange"],
                    "Secteur": row["Secteur"],
                    **metrics
                })

        if results:
            res_df = pd.DataFrame(results)
            res_df = res_df.sort_values("1Y %", ascending=False)

            st.success(f"{len(res_df)} actions trouvées")
            st.dataframe(res_df, use_container_width=True)
        else:
            st.warning("Aucun stock ne respecte les critères")
