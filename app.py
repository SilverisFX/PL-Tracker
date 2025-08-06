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

if st.session_state.get("reset_triggered"):
    st.session_state.clear()
    st.session_state["just_reset"] = True
    st.rerun()

if st.session_state.get("just_reset"):
    st.info("✅ App reset successfully.")
    del st.session_state["just_reset"]

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

for acct in ACCOUNTS:
    settings.setdefault(f"start_balance_{acct}", 1000.0)
    settings.setdefault(f"profit_target_{acct}", 2000.0)
    settings.setdefault(f"last_date_{acct}", str(date.today()))
    settings.setdefault(f"daily_pl_{acct}", 0.0)
    st.session_state.setdefault(f"daily_pl_{acct}", settings[f"daily_pl_{acct}"])
    st.session_state.setdefault(f"last_date_{acct}", settings[f"last_date_{acct}"])

@st.cache_data
def load_data() -> pd.DataFrame:
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE, parse_dates=["Date"], dtype={"Daily P/L": float}).dropna(subset=["Date"])
    return pd.DataFrame(columns=["Account", "Date", "Daily P/L"])

df_all = load_data()

# Preprocess balances and daily P/L before rendering
for acct in ACCOUNTS:
    today = pd.to_datetime(datetime.now().date())
    mask = df_all["Account"] == acct
    df_acc = df_all[mask].copy().sort_values("Date")

    if df_acc.empty:
        df_acc = pd.DataFrame([{"Account": acct, "Date": pd.to_datetime(date.today()), "Daily P/L": 0.0}])

    df_acc["Balance"] = df_acc["Daily P/L"].cumsum() + settings[f"start_balance_{acct}"]
    daily_df = df_acc[pd.to_datetime(df_acc["Date"]).dt.date == today.date()]
    daily_pl = daily_df["Daily P/L"].sum()

    session_key = f"daily_pl_{acct}"
    if session_key not in st.session_state:
        st.session_state[session_key] = daily_pl
    settings[session_key] = daily_pl

save_settings(settings)

with st.sidebar:
    st.header("📜 Account Entry")
    account = st.selectbox("Account", ACCOUNTS, index=ACCOUNTS.index(settings.get("last_account", ACCOUNTS[0])))

    if st.session_state.get("reset_input") == f"daily_pl_{account}":
        if f"daily_pl_{account}" in st.session_state:
            st.session_state[f"daily_pl_{account}"] = 0.0
        del st.session_state["reset_input"]
        st.rerun()

    settings["last_account"] = account

    entry_date = st.date_input("Date", value=pd.to_datetime(settings[f"last_date_{account}"]))
    st.number_input("Today's P/L", step=0.01, format="%.2f", key=f"daily_pl_{account}")
    daily_pl = st.session_state[f"daily_pl_{account}"]
    settings[f"last_date_{account}"] = str(entry_date)
    settings[f"daily_pl_{account}"] = daily_pl

    sb = st.number_input("Starting Balance", value=settings[f"start_balance_{account}"], step=100.0, format="%.2f")
    pt = st.number_input("Profit Target", value=settings[f"profit_target_{account}"], step=100.0, format="%.2f")
    settings[f"start_balance_{account}"], settings[f"profit_target_{account}"] = sb, pt

    save_settings(settings)

    # — Replaced block: sum all today's entries —
    today = date.today()
    mask_today = (
        (df_all["Account"] == account)
        & (df_all["Date"].dt.date == today)
    )
    today_pl = df_all.loc[mask_today, "Daily P/L"].sum()

    st.session_state[f"daily_pl_{account}"] = today_pl
    settings[f"daily_pl_{account}"] = today_pl
    save_settings(settings)

    st.metric("🗖️ Today's P/L", f"{today_pl:+.2f}")
    # — End replacement —

    with st.form(key=f"form_{account}"):
        submitted = st.form_submit_button("➕ Add Entry")
        if submitted:
            new_row = pd.DataFrame([{
                "Account": account,
                "Date": pd.to_datetime(entry_date),
                "Daily P/L": today_pl
            }])
            df_all = pd.concat([df_all, new_row], ignore_index=True)
            df_all.sort_values(["Account", "Date"], inplace=True)
            df_all.to_csv(CSV_FILE, index=False)
            st.success(f"✅ Logged {today_pl:+.2f} for {account}")
            st.session_state["reset_input"] = f"daily_pl_{account}"
            st.rerun()

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

tabs = st.tabs([f"📊 {acct}" for acct in ACCOUNTS])
for i, acct in enumerate(ACCOUNTS):
    with tabs[i]:
        st.markdown(f"## Tracker: {acct}")
        mask = df_all["Account"] == acct
        df_acc = df_all[mask].copy().sort_values("Date")
        sb = settings[f"start_balance_{acct}"]
        pt = settings[f"profit_target_{acct}"]

        if df_acc.empty:
            df_acc = pd.DataFrame([{"Account": acct, "Date": pd.to_datetime(date.today()), "Daily P/L": 0.0}])

        df_acc["Balance"] = df_acc["Daily P/L"].cumsum() + sb
        curr = df_acc.iloc[-1]["Balance"]

        # Calculate today's P/L for messaging
        today = date.today()
        gain_df = df_acc[df_acc["Date"].dt.date == today]
        gain = gain_df["Daily P/L"].sum()

        cols = st.columns(2)
        cols[0].metric("Start", f"${sb:,.2f}")
        cols[1].metric("Current", f"${curr:,.2f}", delta=f"{(curr - sb)/sb*100:+.2f}%")

        if gain > 0:
            st.success("📈 Great! You're in profit today. Keep up the momentum!")
        elif gain < 0:
            st.warning("📉 Loss today. Review what went wrong.")
        else:
            st.info("🧘‍♂️ Neutral day. Stay consistent.")

        st.subheader("Balance Over Time")
        fig, ax = plt.subplots(figsize=(8, 4), facecolor='#222')
        fig.patch.set_facecolor('#222')
        ax.plot(df_acc["Date"], df_acc["Balance"], color='lime', linewidth=2)
        ax.set_facecolor('#111')
        ax.grid(False)
        ax.tick_params(colors='lightgrey')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        fig.autofmt_xdate()
        ax.set_ylabel("Balance", color='lightgrey')
        ax.set_title("Balance Over Time", color='lightgrey')
        st.pyplot(fig)
