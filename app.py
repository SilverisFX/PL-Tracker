import os
import json
from datetime import date, datetime, timedelta

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
st.markdown("""
<style>
  @media (max-width: 768px) {
    .css-1d391kg, .css-18e3th9 { width:100vw!important; left:0!important; padding:1rem!important; }
  }
  .metric-container, .progress-container { position: sticky; top:0; background:#222; z-index:10; padding:1rem 0; }
</style>
""", unsafe_allow_html=True)

# ─── Settings Storage ─────────────────────────────────────────
def load_settings():
    try:
        return json.load(open(SETTINGS_FILE)) if os.path.exists(SETTINGS_FILE) else {}
    except json.JSONDecodeError:
        return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

settings = load_settings()

# ─── Data Loading ──────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    if os.path.exists(CSV_FILE):
        return (
            pd.read_csv(CSV_FILE, parse_dates=["Date"], dtype={"Daily P/L": float})
              .dropna(subset=["Date"]))
    return pd.DataFrame(columns=["Account","Date","Daily P/L"])

df_all = load_data()

# ─── Sidebar: Account & Entry ─────────────────────────────────
with st.sidebar:
    st.header("Account & Entry")
    account = st.selectbox(
        "Select Account", ACCOUNTS,
        index=ACCOUNTS.index(settings.get("last_account", ACCOUNTS[0]))
    )
    settings["last_account"] = account

    entry_date = st.date_input(
        "Date", value=pd.to_datetime(settings.get(f"last_date_{account}", str(date.today())))
    )
    daily_pl = st.number_input(
        "Today's P/L", step=0.01, format="%.2f",
        key=f"daily_pl_{account}"
    )
    settings[f"last_date_{account}"] = str(entry_date)

    st.header("Settings")
    sb = st.number_input(
        "Starting Balance", value=settings.get(f"start_balance_{account}", 1000.0),
        step=100.0, format="%.2f"
    )
    pt = st.number_input(
        "Profit Target", value=settings.get(f"profit_target_{account}", 2000.0),
        step=100.0, format="%.2f"
    )
    settings[f"start_balance_{account}"], settings[f"profit_target_{account}"] = sb, pt

    save_settings(settings)

    if st.button("Add Entry"):
        new_row = pd.DataFrame([{"Account":account, "Date":entry_date, "Daily P/L":daily_pl}])
        df_all = pd.concat([df_all, new_row], ignore_index=True)
        df_all.sort_values(["Account","Date"], inplace=True)
        df_all.to_csv(CSV_FILE, index=False)
        st.success(f"Logged {daily_pl:+.2f} for {account}")

    if st.button("Undo Last"):
        mask = df_all["Account"] == account
        idx = df_all[mask].index
        if idx.any():
            df_all.drop(idx[-1], inplace=True)
            df_all.to_csv(CSV_FILE, index=False)
            st.info("Last entry removed")
        else:
            st.warning("No entries to undo")

    if st.checkbox("Reset All Data") and st.button("Confirm Reset"):
        for f in (CSV_FILE, SETTINGS_FILE):
            if os.path.exists(f): os.remove(f)
        st.experimental_rerun()

# ─── Main Header & Metrics ─────────────────────────────────────
st.markdown(f"## Tracker: {account}")
st.write(f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Prepare and filter account data
mask = df_all["Account"] == account
df_acc = df_all[mask].copy().sort_values("Date")
if df_acc.empty:
    df_acc = pd.DataFrame([{"Account":account, "Date":date.today(), "Daily P/L":0.0}])

sb, pt = settings[f"start_balance_{account}"], settings[f"profit_target_{account}"]
df_acc["Balance"] = df_acc["Daily P/L"].cumsum() + sb

# Metrics
curr = df_acc.iloc[-1]["Balance"]
gain = df_acc.iloc[-1]["Daily P/L"]
pct_gain = (curr - sb) / sb * 100
prog = min(curr / pt if pt else 0, 1.0)
cols = st.columns(3)
cols[0].metric("Start", f"${sb:,.2f}")
cols[1].metric("Current", f"${curr:,.2f}", delta=f"{gain:+.2f}")
cols[2].metric("Progress", f"{prog*100:.1f}%", delta=f"{pct_gain:+.2f}%")

# Animated Neon-Blue Progress Bar
st.markdown(f"""
<div class='progress-container'>
  <div class='progress-bar' style='width:{prog*100:.1f}%;'></div>
</div>
""", unsafe_allow_html=True)

# ─── Balance Chart ─────────────────────────────────────────────
st.subheader("Balance Over Time")
fig, ax = plt.subplots(figsize=(8,4))
fig.patch.set_facecolor('#222')
ax.set_facecolor('#333')
ax.plot(df_acc['Date'], df_acc['Balance'], color='#00FFFF', linewidth=2.5)
ax.fill_between(df_acc['Date'], df_acc['Balance'], color='#00FFFF', alpha=0.2)
ax.set(title='Balance Progress', xlabel='Date', ylabel='Balance ($)')
ax.tick_params(colors='#39FF14')
for spine in ax.spines.values(): spine.set_color('#39FF14')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
fig.autofmt_xdate()
ax.grid(False)
st.pyplot(fig, use_container_width=True)

# ─── Entries Table ─────────────────────────────────────────────
st.subheader('Entries')
st.dataframe(
    df_acc.style
    .format({'Date':'{:%Y-%m-%d}','Daily P/L':'{:+.2f}','Balance':'{:,.2f}'})
    .applymap(lambda v: 'color:#39FF14' if isinstance(v,(int,float)) and v>=0 else 'color:#FF0055', subset=['Daily P/L'])
)
