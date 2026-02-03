import streamlit as st
import pandas as pd
import yfinance as yf
import time
from yfinance.exceptions import YFRateLimitError

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


def format_pct(x):
    if pd.isna(x):
        return ""
    return f"{x:.2f} %"


def color_pct(x):
    if pd.isna(x):
        return "color: #999999"
    if x > 0:
        return "color: #1a7f37; font-weight: 600"
    if x < 0:
        return "color: #b42318; font-weight: 600"
    return "color: #999999"


def format_price(x):
    if pd.isna(x):
        return ""
    return f"{x:.2f}"


# ======================
# YAHOO HELPERS (SAFE)
# ======================

@st.cache_data(show_spinner=False, ttl=6 * 3600)
def try_yahoo_variants(base_ticker):
    variants = [
        f"{base_ticker}.TO",
        f"{base_ticker}.V",
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

            if data is not None and not data.empty:
                return t, data

        except YFRateLimitError:
            time.sleep(15)
            return None, None

        except Exception:
            continue

    return None, None


# ======================
# CALCUL DES RENDEMENTS (ULTRA ROBUSTE)
# ======================

def compute_returns(base_ticker):
    yticker, data = try_yahoo_variants(base_ticker)

    if yticker is None or data is None or data.empty:
        return None, None

    if "Close" not in data.columns:
        return None, None

    close = data["Close"].dropna()
    if close.empty or len(close) < 2:
        return None, None

    # ✅ EXTRACTION SCALAIRE BÉTON
    try:
        last = float(close.to_numpy().ravel()[-1])
    except Exception:
        return None, None

    def ret(days):
        if len(close) > days:
            try:
                prev = float(close.to_numpy().ravel()[-days - 1])
                return (last / prev - 1) * 100
            except Exception:
                return None
        return None

    if len(close) >= 252:
        y_ret = ret(252)
    else:
        try:
            first = float(close.to_numpy().ravel()[0])
            y_ret = (last / first - 1) * 100
        except Exception:
            y_ret = None

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
    with st.spinner("Scan Yahoo Finance (mode SAFE)..."):

        df = pd.read_excel(file, sheet_name=secteur)
        df["Ticker"] = df["Ticker"].astype(str)

        results = []
        ignored = 0

        progress = st.progress(0)
        total = len(df)

        for i, (_, row) in enumerate(df.iterrows(), start=1):
            base = clean_ticker(row["Ticker"])
            yticker, metrics = compute_returns(base)

            if yticker is not None:
                time.sleep(1.2)

            if metrics is None:
                ignored += 1
            else:
                if price_min <= metrics["Price"] <= price_max:
                    results.append({
                        "Ticker": yticker,
                        "Company": row["Company"],
                        "Secteur": secteur,
                        **metrics
                    })

            progress.progress(i / total)

        progress.empty()

        if results:
            res_df = pd.DataFrame(results)

            res_df["Y"] = pd.to_numeric(res_df["Y"], errors="coerce")

            res_df = res_df.sort_values(
                "Y", ascending=False, na_position="last"
            )

            st.success(f"✅ {len(res_df)} actions trouvées")
            st.caption(f"ℹ️ {ignored} titres ignorés (non disponibles ou bloqués par Yahoo)")

            pct_cols = ["D", "W", "M", "3M", "6M", "Y"]

            styled_df = (
                res_df.style
                .format(
                    {"Price": format_price, **{c: format_pct for c in pct_cols}}
                )
                .map(color_pct, subset=pct_cols)
            )

            st.dataframe(styled_df, width="stretch")

        else:
            st.warning(
                f"Aucun stock ne respecte les critères "
                f"({ignored} titres ignorés)"
            )
