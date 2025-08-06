import os
from datetime import date

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ─── Page Configuration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="📊 Daily P/L Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_FILE = "tracker.csv"

# ─── Load or Initialize Data ─────────────────────────────────────────────────
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE, parse_dates=["Date"])
else:
    initial_balance = 1000.0
    df = pd.DataFrame([
        {"Date": date.today(), "Daily P/L": 0.0, "Balance": initial_balance}
    ])
    df.to_csv(CSV_FILE, index=False)

initial_balance = df.iloc[0]["Balance"]
last_balance = df.iloc[-1]["Balance"]

# ─── Sidebar: Data & Settings ────────────────────────────────────────────────
st.sidebar.header("📂 Data")
entry_date = st.sidebar.date_input(
    "Date", value=date.today(), help="Select entry date"
)
daily_pl = st.sidebar.number_input(
    "Today's P/L",
    min_value=-float(last_balance),
    value=0.0,
    step=0.01,
    format="%.2f",
    help="Enter profit (positive) or loss (negative)",
)

st.sidebar.header("⚙️ Settings")
target_balance = st.sidebar.number_input(
    "Target Balance",
    min_value=0.0,
    value=initial_balance * 2,
    step=100.0,
    format="%.2f",
    help="Set goal balance",
)

if st.sidebar.button("➕ Add Entry"):
    new_balance = last_balance + daily_pl
    new_row = pd.DataFrame([
        {"Date": entry_date, "Daily P/L": daily_pl, "Balance": new_balance}
    ])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    st.sidebar.success(
        f"✅ Logged {daily_pl:+.2f} on {entry_date}, new balance: ${new_balance:.2f}"
    )

# ─── Main Dashboard ──────────────────────────────────────────────────────────
st.title("📈 Daily Profit/Loss Tracker")

# Metrics Row
col1, col2, col3 = st.columns([2, 1, 2])
col1.metric("🏁 Starting Balance", f"${initial_balance:,.2f}")
col2.metric(
    "💹 Current Balance", f"${last_balance:,.2f}",
    delta=f"{daily_pl:+.2f}"
)
progress_pct = min(last_balance / target_balance if target_balance else 0, 1.0)
col3.metric(
    "🎯 Progress", f"{progress_pct * 100:.1f}%", delta=f"{last_balance - initial_balance:+.2f}"
)

# Progress Bar
st.progress(progress_pct)

# ─── Balance Chart ──────────────────────────────────────────────────────────
st.subheader("Balance Over Time")
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor("#eff2f7")  # bluish-grey background
ax.set_facecolor("#ffffff")         # white plot background

ax.plot(
    df["Date"],
    df["Balance"],
    color="#0072B2",
    linewidth=2.5,
    marker="o",
    markersize=8,
    markerfacecolor="#ffffff",
    markeredgecolor="#0072B2"
)
ax.axhline(
    target_balance,
    linestyle="--",
    linewidth=2,
    color="#D55E00",
    label="Target"
)

# Format dates
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
fig.autofmt_xdate()

# Title & Labels
ax.set_title("Account Balance Progress", fontsize=16, pad=15)
ax.set_xlabel("Date", fontsize=12)
ax.set_ylabel("Balance ($)", fontsize=12)

# Subtle grid
ax.grid(True, linestyle="--", linewidth=0.5, color="#d3d3d3")

# Clean spines
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

st.pyplot(fig, use_container_width=True)

# ─── Data Table ─────────────────────────────────────────────────────────────
st.subheader("Logged Entries")
st.dataframe(df, use_container_width=True)
