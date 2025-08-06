import os
from datetime import date

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ─── Page Configuration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="🧮 Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_FILE = "tracker.csv"

# ─── Load or Initialize All Data ─────────────────────────────────────────────
if os.path.exists(CSV_FILE):
    df_all = pd.read_csv(
        CSV_FILE,
        parse_dates=["Date"],
        infer_datetime_format=True,
    )
    df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")
    df_all = df_all.dropna(subset=["Date"])
else:
    df_all = pd.DataFrame(columns=["Account", "Date", "Daily P/L", "Balance"])

# ─── Sidebar: Inputs & Actions ───────────────────────────────────────────────
st.sidebar.header("👤 Account")
account = st.sidebar.selectbox(
    "Select Account",
    options=["Account A", "Account B"],
)

st.sidebar.header("✏️ Data Entry")
entry_date = st.sidebar.date_input("Date", value=date.today())
daily_pl = st.sidebar.number_input(
    "Today's P/L", value=0.0, step=0.01, format="%.2f"
)

# Balance settings
start_balance = st.sidebar.number_input("Starting Balance", value=1000.0, step=100.0, format="%.2f")
target_balance = st.sidebar.number_input("Target Balance", value=2000.0, step=100.0, format="%.2f")

# Add Entry button first
if st.sidebar.button("➕ Add Entry"):
    df_acc = df_all[df_all["Account"] == account].sort_values("Date")
    initial_balance = df_acc.iloc[0]["Balance"] if not df_acc.empty else start_balance
    last_balance = df_acc.iloc[-1]["Balance"] if not df_acc.empty else initial_balance
    new_balance = last_balance + daily_pl
    new_row = {"Account": account, "Date": entry_date, "Daily P/L": daily_pl, "Balance": new_balance}
    df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True)
    df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")
    df_all.to_csv(CSV_FILE, index=False)
    st.session_state['notification'] = f"{daily_pl:+.2f} for {account}"
    st.sidebar.success(f"✅ Logged {daily_pl:+.2f} for {account}.")

# Undo button below
if st.sidebar.button("Undo"):
    df_acc = df_all[df_all["Account"] == account]
    if len(df_acc) > 1:
        df_acc = df_acc.iloc[:-1]
        df_all = pd.concat([df_all[df_all["Account"] != account], df_acc])
        df_all.to_csv(CSV_FILE, index=False)
        st.sidebar.success(f"🔄 Last entry removed for {account}.")
    else:
        st.sidebar.warning("Nothing to undo for this account.")

# ─── Main Dashboard & Notification ─────────────────────────────────────────
if 'notification' not in st.session_state:
    st.session_state['notification'] = None
if st.session_state['notification']:
    st.info(st.session_state.pop('notification'), icon="🔔")

st.markdown(
    f"<h2 style='font-size:1.5rem;'>🧮 Tracker: {account}</h2>",
    unsafe_allow_html=True
)

# prepare account data
df = df_all[df_all["Account"] == account].copy()
if df.empty:
    df = pd.DataFrame([{"Account": account, "Date": date.today(), "Daily P/L": 0.0, "Balance": start_balance}])
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"]).sort_values("Date")
initial_balance = df.iloc[0]["Balance"]
last_balance = df.iloc[-1]["Balance"]
daily_delta = df.iloc[-1]["Daily P/L"]
progress_pct = min(last_balance / target_balance if target_balance else 0, 1.0)

# metrics
col1, col2, col3 = st.columns([2, 2, 2])
col1.metric("🏁 Start", f"${initial_balance:,.2f}")
col2.metric("💹 Current", f"${last_balance:,.2f}", delta=f"{daily_delta:+.2f}")
col3.metric("📊 Progress", f"{progress_pct*100:.1f}%", delta=f"{last_balance-initial_balance:+.2f}")

# progress bar
st.progress(progress_pct)

# chart
st.subheader("Balance Over Time")
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor("#e0e0e0")  # grey background
ax.set_facecolor("#f2f2f2")          # lighter grey plot area
ax.plot(df["Date"], df["Balance"], color="#2ca02c", linewidth=2.5, marker="o", markersize=6)
ax.axhline(target_balance, linestyle="--", color="#7f7f7f", linewidth=2, label="Target")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
fig.autofmt_xdate()
ax.set_title("Balance Progress", fontsize=14)
ax.grid(True, linestyle="--", color="#b0b0b0")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
st.pyplot(fig, use_container_width=True)

# table
st.subheader("Entries")
st.dataframe(df[["Date", "Daily P/L", "Balance"]], use_container_width=True)
