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
        dayfirst=False,
        keep_default_na=True,
    )
else:
    df_all = pd.DataFrame(columns=["Account", "Date", "Daily P/L", "Balance"])
    df_all.to_csv(CSV_FILE, index=False)
# Ensure Date is datetime (coerce errors to NaT)
if not pd.api.types.is_datetime64_any_dtype(df_all["Date"]):
    df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")

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
    df_temp = pd.read_csv(
        CSV_FILE,
        parse_dates=["Date"],
        infer_datetime_format=True,
        keep_default_na=True,
    )
    # Coerce Date
    df_temp["Date"] = pd.to_datetime(df_temp["Date"], errors="coerce")
    idxs = df_temp[df_temp["Account"] == account].index
    if len(idxs) <= 1:
        st.sidebar.warning("Nothing to undo for this account.")
    else:
        last_idx = idxs.max()
        df_temp = df_temp.drop(last_idx).reset_index(drop=True)
        df_temp.to_csv(CSV_FILE, index=False)
        st.sidebar.success(f"🔄 Removed last entry for {account}.")
        # Update in-memory df_all
        df_all = df_temp.copy()

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
    # Append and save
    df_all = pd.concat([df_all, new_entry], ignore_index=True)
    df = pd.concat([df, new_entry], ignore_index=True)
    df_all.to_csv(CSV_FILE, index=False)
    # Set notification for top banner
    st.session_state['notification'] = f"{daily_pl:+.2f} for {account}"
    st.sidebar.success(
        f"✅ Logged {daily_pl:+.2f} for {account} on {entry_date}, balance → ${new_balance:.2f}"
    )

# ─── Main Dashboard & Notification ────────────────────────────────────────
# Show banner notification if set
if st.session_state.get('notification'):
    st.info(st.session_state['notification'], icon="🔔")
    st.session_state['notification'] = None

# Compact title for mobile
st.markdown(
    f"<h2 style='font-size:1.5rem; margin-bottom:0.5rem;'>🧮 Tracker: {account}</h2>",
    unsafe_allow_html=True
)

# ─── Metrics Row ────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 2])
col1.metric("🏁 Starting Balance", f"${initial_balance:,.2f}")
col2.metric("💹 Current Balance", f"${last_balance:,.2f}", delta=f"{daily_pl:+.2f}")
progress_pct = min(last_balance / target_balance if target_balance else 0, 1.0)
col3.metric("📊 Progress", f"{progress_pct * 100:.1f}%", delta=f"{last_balance - initial_balance:+.2f}")

# ─── Progress Bar ────────────────────────────────────────────────────────────
st.progress(progress_pct)

# ─── Balance Chart with New Color Theme ──────────────────────────────────────
st.subheader("Balance Over Time")
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor("#fafafa")  # very light grey background
ax.set_facecolor("#f5f5f5")         # light grey plot background
ax.plot(
    df["Date"], df["Balance"],
    color="#2ca02c", linewidth=2.5,
    marker="o", markersize=8,
    markerfacecolor="#ffffff", markeredgecolor="#2ca02c"
)
ax.axhline(
    target_balance, linestyle="--", linewidth=2,
    color="#d62728", label="Target"
)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
fig.autofmt_xdate()
ax.set_title("Account Balance Progress", fontsize=16, pad=15)
ax.set_xlabel("Date", fontsize=12)
ax.set_ylabel("Balance ($)", fontsize=12)
ax.grid(True, linestyle="--", linewidth=0.5, color="#e0e0e0")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
st.pyplot(fig, use_container_width=True)

# ─── Data Table ─────────────────────────────────────────────────────────────
st.subheader("Logged Entries")
st.dataframe(df.drop(columns=["Account"]), use_container_width=True)
