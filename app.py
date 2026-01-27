import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Scanner Minières", layout="wide")

# ======================
# FONCTIONS
# ======================

def yahoo_ticker(ticker, exchange):
    """
    - Si le ticker contient déjà un suffixe (.TO, .V, .CN), on le garde tel quel
    - Sinon on ajoute le suffixe selon l'exchange
    """
    ticker = str(ticker).upper().strip()
    exchange = str(exchange).upper().strip()

    # 🔥 CORRECTION CLÉ : ticker déjà Yahoo
    if "." in ticker:
        return ticker

    if exchange == "TSX":
        return f"{ticker}.TO"
    elif exchange == "TSX.V":
        return f"{ticker}.V"
    elif exchange == "CSE":
        return f"{ticker}.CN"

    return ticker


def compute_returns(ticker):
    try:
        data = yf.download(
            ticker,
            period="1y",
            auto_adjust=True,
            progress=False,
            threads=False
        )

        if data.empty:
            return None

        close = data["Close"].dropna()
        if close.empty:
            return None

        last = float(close.iloc[-1])

        def ret(days):
            if len(close) > days:
                return (last / close.iloc[-days - 1] - 1) * 100
            return None

        return {
            "Price": round(last, 2),
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

xls = pd.ExcelFile(file)
secteurs = xls.sheet_names
secteur = st.selectbox("Secteur", secteurs)

exchange_filter = st.multiselect(
    "Exchange",
    ["TSX", "TSX.V", "CSE"],
    default=["TSX", "TSX.V", "CSE"]
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
        value=1000.0,
        step=10.0
    )

run = st.button("🚀 Lancer le scan")

# ======================
# SCAN
# ======================

if run:
    with st.spinner("Téléchargement des données Yahoo Finance..."):

        df = pd.read_excel(file, sheet_name=secteur)

        # 🔥 Normalisation critique
        df["Exchange"] = df["Exchange"].astype(str).str.upper().str.strip()
        df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()

        df = df[df["Exchange"].isin(exchange_filter)]

        st.info(f"🔍 {len(df)} tickers analysés")

        results = []

        for _, row in df.iterrows():
            yticker = yahoo_ticker(row["Ticker"], row["Exchange"])
            metrics = compute_returns(yticker)

            if (
                metrics
                and pd.notna(metrics["Price"])
                and price_min <= metrics["Price"] <= price_max
            ):
                results.append({
                    "Ticker": yticker,
                    "Company": row["Company"],
                    "Exchange": row["Exchange"],
                    "Secteur": secteur,
                    **metrics
                })

        if results:
            res_df = pd.DataFrame(results).sort_values("1Y %", ascending=False)
            st.success(f"✅ {len(res_df)} actions trouvées")
            st.dataframe(res_df, use_container_width=True)
        else:
            st.error("❌ Aucun stock valide (Yahoo ne retourne rien)")
