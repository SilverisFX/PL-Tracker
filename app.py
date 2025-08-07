import os
import json
from datetime import date, datetime
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

st.set_page_config(page_title="Tracker", page_icon="💰", layout="wide")
CSV_FILE = "tracker.csv"
SETTINGS_FILE = "settings.json"
ACCOUNTS = ["Account A", "Account B"]

# ─── Reset Handling ────────────────────────────────────
if st.session_state.get("reset_triggered"):
    st.cache_data.clear()
    st.session_state.clear()
    st.session_state["just_reset"] = True
    st.experimental_rerun()
if st.session_state.get("just_reset"):
    st.info("✅ App reset successfully.")
    del st.session_state["just_reset"]

# ─── Settings Storage ───────────────────────────
def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}
def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
settings = load_settings()

# ─── Ensure Defaults ──────────────────────────
for acct in ACCOUNTS:
    settings.setdefault(f"start_balance_{acct}", 1000.0)
    settings.setdefault(f"profit_target_{acct}", 2000.0)
    settings.setdefault(f"last_date_{acct}", str(date.today()))
    settings.setdefault(f"daily_pl_{acct}", 0.0)
    st.session_state.setdefault(f"daily_pl_{acct}", settings[f"daily_pl_{acct}"])
    st.session_state.setdefault(f"last_date_{acct}", settings[f"last_date_{acct}"])
save_settings(settings)

# ─── Data Loading ───────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    if os.path.exists(CSV_FILE):
        return (pd.read_csv(CSV_FILE, parse_dates=["Date"], dtype={"Daily P/L": float})
                  .dropna(subset=["Date"]))
    return pd.DataFrame(columns=["Account", "Date", "Daily P/L"])

df_all = load_data()
df_all["Date"] = pd.to_datetime(df_all["Date"])

# ─── Sidebar Inputs ───────────────────────────
with st.sidebar:
    st.header("📋 Account Entry")

    account = st.selectbox(
        "Account",
        ACCOUNTS,
        index=ACCOUNTS.index(settings.get("last_account", ACCOUNTS[0]))
    )
    settings["last_account"] = account

    entry_date = st.date_input(
        "Date",
        value=pd.to_datetime(settings[f"last_date_{account}"])
    )
    daily_pl = st.number_input(
        "Today's P/L",
        step=0.01,
        format="%.2f",
        key=f"daily_pl_{account}"
    )
    settings[f"last_date_{account}"] = str(entry_date)
    settings[f"daily_pl_{account}"] = daily_pl

    sb = st.number_input(
        "Starting Balance",
        value=settings[f"start_balance_{account}"],
        step=100.0,
        format="%.2f"
    )
    pt = st.number_input(
        "Profit Target",
        value=settings[f"profit_target_{account}"],
        step=100.0,
        format="%.2f"
    )
    settings[f"start_balance_{account}"], settings[f"profit_target_{account}"] = sb, pt

    save_settings(settings)

    # — Define callback to add an entry and reset P/L —
    def add_entry_cb(account, entry_date, daily_p_l):
        global df_all
        new_row = pd.DataFrame([{
            "Account": account,
            "Date": pd.to_datetime(entry_date),
            "Daily P/L": daily_p_l
        }])
        df_all = pd.concat([df_all, new_row], ignore_index=True)
        df_all.sort_values(["Account", "Date"], inplace=True)
        df_all.to_csv(CSV_FILE, index=False)

        st.success(f"✅ Logged {daily_p_l:+.2f} for {account}")

        # Reset the input widget back to zero
        st.session_state[f"daily_pl_{account}"] = 0.0
        settings[f"daily_pl_{account}"] = 0.0
        save_settings(settings)

        # Rerun to refresh all panels
        st.experimental_rerun()

    # — Use button with on_click callback —
    st.button(
        "➕ Add Entry",
        on_click=add_entry_cb,
        args=(account, entry_date, daily_pl)
    )

    if st.button("↩️ Undo Last"):
        df_acc = df_all[df_all["Account"] == account]
        if not df_acc.empty:
            last_idx = df_acc.index[-1]
            df_all.drop(last_idx, inplace=True)
            df_all.to_csv(CSV_FILE, index=False)
        else:
            st.warning("No entries to undo")

    if st.checkbox("⚠️ Reset All Data", key="reset_confirm"):
        if st.button("Confirm Reset"):
            for file in (CSV_FILE, SETTINGS_FILE):
                if os.path.exists(file):
                    os.remove(file)
            st.session_state["reset_triggered"] = True
            st.success("✅ Files removed. Reloading app...")

    # Calculate & display today’s true P/L in the sidebar
    today = date.today()
    mask_today = (
        (df_all["Account"] == account)
        & (df_all["Date"].dt.date == today)
    )
    today_pl = df_all.loc[mask_today, "Daily P/L"].sum()
    settings[f"daily_pl_{account}"] = today_pl
    save_settings(settings)
    st.metric("🗖️ Today's P/L", f"{today_pl:+.2f}")

# ─── Tabs for Account Comparison ──────────────────────────
tabs = st.tabs([f"📊 {acct}" for acct in ACCOUNTS])
for i, acct in enumerate(ACCOUNTS):
    with tabs[i]:
        # ... your existing tab code (Start/Current/Today P/L metrics, neon bar, chart, entries) ...
        pass
