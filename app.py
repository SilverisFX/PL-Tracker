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
    df_all = pd.read_csv(CSV_FILE, parse_dates=["Date"])
else:
    df_all = pd.DataFrame(columns=["Account", "Date", "Daily P/L", "Balance"])
    df_all.to_csv(CSV_FILE, index=False)
df_all["Date"] = pd.to_datetime(df_all["Date"])

# ─── Sidebar: Account Selection ───────────────────────────────────────────────
st.sidebar.header("👤 Account")
account = st.sidebar.selectbox(
    "Select Account",
    options=["Account A", "Account B"],
    help="Choose which account's P/L to log/view"
)

# ─── Sidebar: Data Entry ─────────────────────────────────────────────────────
st.sidebar.header("📂 Data Entry")
entry_date = st.sidebar.date_input(
    "Date", value=date.today(), help="Select the date for this entry"
)
daily_pl = st.sidebar.number_input(
    "Today's P/L",
    min_value=-1e6,
    value=0.0,
    step=0.01,
    format="%.2f",
    help="Enter profit (positive) or loss (negative)"
)

# ─── Sidebar: Settings Inputs ─────────────────────────────────────────────────
start_balance = st.sidebar.number_input(
    "Starting Balance",
    min_value=0.0,
    value=1000.0,
    step=100.0,
    format="%.2f",
    help="Initial balance when this account is first used"
)
target_balance = st.sidebar.number_input(
    "Target Balance",
    min_value=0.0,
    value=2000.0,
    step=100.0,
    format="%.2f",
    help="Your goal balance for this account"
)

# ─── Sidebar: Actions ────────────────────────────────────────────────────────
if st.sidebar.button("Undo"):
    df_all = pd.read_csv(CSV_FILE, parse_dates=["Date"])
    df_all["Date"] = pd.to_datetime(df_all["Date"])
    idxs = df_all[df_all["Account"] == account].index
    if len(idxs) <= 1:
        st.sidebar.warning("Nothing to undo for this account.")
    else:
        last_idx = idxs.max()
        df_all = df_all.drop(last_idx).reset_index(drop=True)
        df_all.to_csv(CSV_FILE, index=False)
        st.sidebar.success(f"🔄 Removed last entry for {account}.")

# ─── Filter for Current Account ──────────────────────────────────────────────
df = df_all[df_all["Account"] == account].copy()
if df.empty:
    initial_balance = start_balance
    init_row = pd.DataFrame([{
        "Account": account,
        "Date": entry_date,
        "Daily P/L": 0.0,
        "Balance": initial_balance
    }])
    df_all = pd.concat([df_all, init_row], ignore_index=True)
    df = init_row.copy()
    df_all.to_csv(CSV_FILE, index=False)
else:
    initial_balance = df.iloc[0]["Balance"]
last_balance = df.iloc[-1]["Balance"]

# ─── Add New Entry ──────────────────────────────────────────────────────────
if st.sidebar.button("➕ Add Entry"):
    new_balance = last_balance + daily_pl
    new_entry = pd.DataFrame([{
        "Account": account,
        "Date": entry_date,
        "Daily P/L": daily_pl,
        "Balance": new_balance
    }])
    new_entry["Date"] = pd.to_datetime(new_entry["Date"])
    df_all = pd.concat([df_all, new_entry], ignore_index=True)
    df = pd.concat([df, new_entry], ignore_index=True)
    df_all.to_csv(CSV_FILE, index=False)
    st.sidebar.success(
        f"✅ Logged {daily_pl:+.2f} for {account} on {entry_date}, new balance: ${new_balance:.2f}"
    )

# ─── Main Dashboard & Notification ────────────────────────────────────────
# Show notification if available
if st.session_state.get('notification'):
    # Display a temporary banner at top
    st.info(st.session_state['notification'], icon="🔔")
    # Clear after showing
    st.session_state['notification'] = None

# Compact title for mobile
st.markdown(
    f"<h2 style='font-size:1.5rem; margin-bottom:0.5rem;'>🧮 Tracker: {account}</h2>",
    unsafe_allow_html=True
)

# Metrics Row
col1, col2, col3 = st.columns([2, 2, 2])
col1.metric("🏁 Starting Balance", f"${initial_balance:,.2f}")
col2.metric(
    "💹 Current Balance", f"${last_balance:,.2f}",
    delta=f"{daily_pl:+.2f}"
)
progress_pct = min(last_balance / target_balance if target_balance else 0, 1.0)
col3.metric(
    "📊 Progress", f"{progress_pct * 100:.1f}%", delta=f"{last_balance - initial_balance:+.2f}"
)

# ─── Progress Bar ────────────────────────────────────────────────────────────
st.progress(progress_pct)

# ─── Balance Chart with New Color Theme ──────────────────────────────────────
st.subheader("Balance Over Time")
fig, ax = plt.subplots(figsize=(10, 5))
# Soft pastel theme
fig.patch.set_facecolor("#fafafa")  # very light grey background
ax.set_facecolor("#f5f5f5")          # light grey plot background

# Pastel green line
ax.plot(
    df["Date"],
    df["Balance"],
    color="#2ca02c",
    linewidth=2.5,
    marker="o",
    markersize=8,
    markerfacecolor="#ffffff",
    markeredgecolor="#2ca02c"
)
# Pastel magenta target
ax.axhline(
    target_balance,
    linestyle="--",
    linewidth=2,
    color="#d62728",
    label="Target"
)

# Format dates
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
fig.autofmt_xdate()

# Labels & style
aq = ax.set_title("Account Balance Progress", fontsize=16, pad=15)
ax.set_xlabel("Date", fontsize=12)
ax.set_ylabel("Balance ($)", fontsize=12)

# Soft gridlines
ax.grid(True, linestyle="--", linewidth=0.5, color="#e0e0e0")

# Clean spines
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

st.pyplot(fig, use_container_width=True)

# ─── Data Table ─────────────────────────────────────────────────────────────
st.subheader("Logged Entries")
st.dataframe(df.drop(columns=["Account"]), use_container_width=True)
