import os
import json
from datetime import date

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ─── Config ─────────────────────────────────────────────────────
st.set_page_config(page_title="Tracker", page_icon="💰", layout="wide")
CSV_FILE = "tracker.csv"
SETTINGS_FILE = "settings.json"
ACCOUNTS = ["Account A", "Account B"]

# ─── CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
 @media (max-width: 768px) {
   .css-1d391kg, .css-18e3th9 { width:100vw!important; left:0!important; padding:1rem!important; }
 }
 .metric-container, .progress-container { position: sticky; top:0; background:#222; z-index:10; padding:1rem 0; }
</style>
""", unsafe_allow_html=True)

# ─── Settings Storage ─────────────────────────────────────────
def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

settings = load_settings()

# ─── Data Loading ──────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE, parse_dates=["Date"], dtype={"Daily P/L": float}).dropna(subset=["Date"])
    return pd.DataFrame(columns=["Account", "Date", "Daily P/L"])

if "df_all" not in st.session_state:
    st.session_state.df_all = load_data()

df_all = st.session_state.df_all

# ─── Sidebar ───────────────────────────────────────────────────
st.sidebar.header("Account & Entry")

account = st.sidebar.selectbox("Account", ACCOUNTS, index=ACCOUNTS.index(settings.get("last_account", ACCOUNTS[0])))
settings["last_account"] = account

entry_date = st.sidebar.date_input("Date", value=pd.to_datetime(settings.get(f"last_date_{account}", date.today())))
daily_pl = st.sidebar.number_input("Today's P/L", step=0.01, format="%.2f", key=f"daily_pl_{account}")

sb = st.sidebar.number
