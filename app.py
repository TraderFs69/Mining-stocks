import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Scanner Minières", layout="wide")

# ======================
# UTILITAIRES
# ======================

def safe_round(x, n=2):
    return round(x, n) if x is not None else None


def clean_ticker(ticker: str) -> str:
    return (
        str(ticker)
        .upper()
        .strip()
        .replace(" ", "")
        .replace("\u00a0", "")
        .replace("\t", "")
    )


# ======================
# YAHOO HELPERS
# ======================

@st.cache_data(show_spinner=False)
def try_yahoo_variants(base_ticker):
    variants = [
        f"{base_ticker}.TO",
        f"{base_ticker}.V",
        f"{base_ticker}.CN",
        base_ticker
    ]

    for t in variants:
        try:
            data = yf.download(
                t,
                period="1y",
                auto_adjust=True,
                threads=False,
                progress=False
            )
            if not data.empty:
                return t, data
        except Exception:
            continue

    return None, None


def compute_returns(base_ticker):
    yticker, data = try_yahoo_variants(base_ticker)

    if yticker is None or data is None:
        return None, None

    close = data["Close"].dropna()
    if close.empty:
        return None, None

    last = float(close.iloc[-1])

    def ret(days):
        if len(close) > days:
            return (last / close.iloc[-days - 1] - 1) * 100
        return None

    # 🔥 Rendement annuel intelligent
    if len(close) >= 252:
        y_ret = ret(252)
    else:
        y_ret = (last / close.iloc[0] - 1) * 100

    metrics = {
        "Price": safe_round(last),
        "D": safe_round(ret(1)),
        "W": safe_round(ret(5)),
        "M": safe_round(ret(21)),
        "3M": safe_round(ret(63)),
        "6M": safe_round(ret(126)),
        "Y": safe_round(y_ret),
    }

    return yticker, metrics


# ======================
# INTERFACE
# ======================

st.title("⛏️ Scanner des minières canadiennes")

file = "Stock Minier.xlsx"

xls = pd.ExcelFile(file)
secteurs = xls.sheet_names
secteur = st.selectbox("Secteur", secteurs)

col1, col2 = st.columns(2)

with col1:
    price_min = st.number_input("Prix minimum ($)", 0.0, 1000.0, 0.0, 0.1)

with col2:
    price_max = st.number_input("Prix maximum ($)", 0.0, 1000.0, 1000.0, 10.0)

run = st.button("🚀 Lancer le scan")

# ======================
# SCAN
# ======================

if run:
    with st.spinner("Scan Yahoo Finance..."):

        df = pd.read_excel(file, sheet_name=secteur)
        df["Ticker"] = df["Ticker"].astype(str)

        results = []
        ignored = 0

        for _, row in df.iterrows():
            base = clean_ticker(row["Ticker"])
            yticker, metrics = compute_returns(base)

            if metrics is None:
                ignored += 1
                continue

            if price_min <= metrics["Price"] <= price_max:
                results.append({
                    "Ticker": yticker,
                    "Company": row["Company"],
                    "Secteur": secteur,
                    **metrics
                })

        if results:
            res_df = pd.DataFrame(results)

            # 🔥 CORRECTION DÉFINITIVE : forcer Y en numérique avant tri
            res_df["Y"] = pd.to_numeric(res_df["Y"], errors="coerce")

            res_df = res_df.sort_values(
                "Y", ascending=False, na_position="last"
            )

            st.success(f"✅ {len(res_df)} actions trouvées")
            st.caption(f"ℹ️ {ignored} titres ignorés (non disponibles sur Yahoo Finance)")
            st.dataframe(res_df, use_container_width=True)

        else:
            st.warning(
                f"Aucun stock ne respecte les critères "
                f"({ignored} titres ignorés car absents de Yahoo Finance)"
            )
