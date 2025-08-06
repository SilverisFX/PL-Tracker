import os
import json
from datetime import date, datetime

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ─── Config ─────────────────────────────────────────────────────
st.set_page_config(page_title="Tracker", page_icon="💰", layout="wide")
CSV_FILE = "tracker.csv"
SETTINGS_FILE = "settings.json"
ACCOUNTS = ["Account A", "Account B"]

# ─── CSS ────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  @media (max-width: 768px) {
    .css-1d391kg, .css-18e3th9 { width:100vw!important; padding:1rem!important; }
  }
  .metric-container, .progress-container { position: sticky; top:0; background:#222; z-index:10; padding:1rem 0; }
</style>
""",
    unsafe_allow_html=True
)

# ─── Settings Storage ─────────────────────────────────────────
def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
    except json.JSONDecodeError:
        pass
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

settings = load_settings()

# ─── Data Loading ──────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(
            CSV_FILE,
            parse_dates=["Date"],
            dtype={"Daily P/L": float, "Account": str}
        ).dropna(subset=["Date"])
        return df
    return pd.DataFrame(columns=["Account", "Date", "Daily P/L"])

df_all = load_data()

# ─── Sidebar Inputs ────────────────────────────────────────────
with st.sidebar:
    st.header("Account & Entry")
    account = st.selectbox(
        "Select Account", ACCOUNTS,
        index=ACCOUNTS.index(settings.get("last_account", ACCOUNTS[0]))
    )
    settings["last_account"] = account

    entry_date = st.date_input(
        "Date",
        value=pd.to_datetime(settings.get(f"last_date_{account}", str(date.today())))
    )
    daily_pl = st.number_input(
        "Today's P/L", step=0.01, format="%.2f", key=f"pl_{account}"
    )
    settings[f"last_date_{account}"] = str(entry_date)

    st.header("Settings")
    sb = st.number_input(
        "Starting Balance",
        value=settings.get(f"start_balance_{account}", 1000.0),
        step=100.0, format="%.2f"
    )
    pt = st.number_input(
        "Profit Target",
        value=settings.get(f"profit_target_{account}", 2000.0),
        step=100.0, format="%.2f"
    )
    settings[f"start_balance_{account}"], settings[f"profit_target_{account}"] = sb, pt

    save_settings(settings)

    if st.button("Add Entry"):
        new_row = pd.DataFrame([{"Account": account, "Date": entry_date, "Daily P/L": daily_pl}])
        df_all = pd.concat([df_all, new_row], ignore_index=True)
        # ensure correct dtypes before sorting
        df_all["Account"] = df_all["Account"].astype(str)
        df_all["Date"] = pd.to_datetime(df_all["Date"])
        df_all = df_all.sort_values(["Account", "Date"]).reset_index(drop=True)
        df_all.to_csv(CSV_FILE, index=False)
        st.success(f"Logged {daily_pl:+.2f} for {account}")
