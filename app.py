import os
from datetime import date

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ─── Page Configuration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="📊 Daily P/L Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_FILE = "tracker.csv"

# ─── Sidebar: Input Controls ─────────────────────────────────────────────────
st.sidebar.header("📝 New Entry")

entry_date = st.sidebar.date_input(
    "Date", value=date.today(), help="Select the date for this entry"
)
daily_pl = st.sidebar.number_input(
    "Today's P/L", value=0.0, step=0.01, format="%.2f",
    help="Enter profit (positive) or loss (negative)"
)
start_balance = st.sidebar.number_input(
    "Starting Balance", value=1000.0, step=100.0, format="%.2f",
    help="Your account balance at the very beginning"
)
target_balance = st.sidebar.number_input(
    "Target Balance", value=2000.0, step=100.0, format="%.2f",
    help="Your goal balance"
)

if st.sidebar.button("➕ Add Entry"):
    # Load or initialize DataFrame
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, parse_dates=["Date"])
    else:
        df = pd.DataFrame([{
            "Date": entry_date,
            "Daily P/L": 0.0,
            "Balance": start_balance
        }])
    # Compute new balance
    last_balance = df.iloc[-1]["Balance"]
    new_balance = last_balance + daily_pl

    # Append new row
    new_row = pd.DataFrame([{
        "Date": entry_date,
        "Daily P/L": daily_pl,
        "Balance": new_balance
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

    st.sidebar.success(
        f"✅ Logged {daily_pl:+.2f} on {entry_date}, new balance: ${new_balance:.2f}"
    )

# ─── Load Data for Display ────────────────────────────────────────────────────
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE, parse_dates=["Date"])
else:
    df = pd.DataFrame([{
        "Date": date.today(),
        "Daily P/L": 0.0,
        "Balance": start_balance
    }])
    df.to_csv(CSV_FILE, index=False)

# ─── Main Dashboard ──────────────────────────────────────────────────────────
st.title("📈 Daily Profit/Loss Tracker")

# Metrics row
current_balance = df.iloc[-1]["Balance"]
today_pl = df.iloc[-1]["Daily P/L"]
progress_pct = min(current_balance / target_balance, 1.0)

col1, col2, col3 = st.columns([2, 2, 2])
col1.metric("🎯 Target Balance", f"${target_balance:,.2f}")
col2.metric(
    "💹 Current Balance", f"${current_balance:,.2f}",
    delta=f"{today_pl:+.2f}"
)
col3.metric(
    "📊 Progress", f"{progress_pct * 100:.1f}%"
)

# Progress bar
st.progress(progress_pct)

# Balance chart
st.subheader("Balance Over Time")
fig, ax = plt.subplots()
ax.plot(df["Date"], df["Balance"], marker="o")
ax.axhline(target_balance, linestyle="--", label="Target")
ax.set_xlabel("Date")
ax.set_ylabel("Balance")
ax.legend(loc="upper left")
ax.grid(True)
st.pyplot(fig)

# Data table
st.subheader("Logged Entries")
st.dataframe(df, use_container_width=True)
