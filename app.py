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

# ─── Initialize Persistent Settings ─────────────────────────────────────────
# Use session_state to retain user-configured start balance and profit target across reruns
if 'start_balance' not in st.session_state:
    st.session_state['start_balance'] = 1000.0
if 'profit_target' not in st.session_state:
    st.session_state['profit_target'] = 2000.0

# ─── Data Loading with Caching ───────────────────────────────────────────────
@st.experimental_memo(ttl=600)
def load_data(file_path: str) -> pd.DataFrame:
    if os.path.exists(file_path):
        df = pd.read_csv(
            file_path,
            parse_dates=["Date"],
            infer_datetime_format=True,
        )
        df = df.dropna(subset=["Date"])
    else:
        df = pd.DataFrame(columns=["Account", "Date", "Daily P/L", "Balance"])
    return df

df_all = load_data(CSV_FILE)

# ─── Sidebar: Account & Data Entry ───────────────────────────────────────────
st.sidebar.header("👤 Account")
account = st.sidebar.selectbox(
    "Select Account",
    options=["Account A", "Account B"],
)

st.sidebar.header("🗒️ Data Entry")
entry_date = st.sidebar.date_input("Date", value=date.today())
daily_pl = st.sidebar.number_input(
    "Today's P/L", value=0.0, step=0.01, format="%.2f", key='daily_pl'
)

# ─── Sidebar: Balance Settings ───────────────────────────────────────────────
st.sidebar.header("⚙️ Balance Settings")
start_balance = st.sidebar.number_input(
    "Starting Balance", value=st.session_state['start_balance'], key='start_balance', step=100.0, format="%.2f"
)
profit_target = st.sidebar.number_input(
    "Profit Target", value=st.session_state['profit_target'], key='profit_target', step=100.0, format="%.2f"
)

target_balance = profit_target

# ─── Add Entry with Duplicate Check ──────────────────────────────────────────
if st.sidebar.button("➕ Add Entry"):
    df_acc = df_all[df_all["Account"] == account]
    if df_acc["Date"].eq(pd.to_datetime(entry_date)).any():
        st.sidebar.warning("An entry for that date already exists.")
    else:
        initial_balance = df_acc.iloc[0]["Balance"] if not df_acc.empty else start_balance
        last_balance = df_acc.iloc[-1]["Balance"] if not df_acc.empty else initial_balance
        new_balance = last_balance + daily_pl
        new_row = {
            "Account": account,
            "Date": pd.to_datetime(entry_date),
            "Daily P/L": daily_pl,
            "Balance": new_balance,
        }
        df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True)
        df_all = df_all.sort_values(["Account", "Date"])
        df_all.to_csv(CSV_FILE, index=False)
        st.session_state['notification'] = f"✅ Logged {daily_pl:+.2f} for {account}"

# ─── Undo Last Entry ────────────────────────────────────────────────────────
if st.sidebar.button("🔄 Undo"):
    df_acc = df_all[df_all["Account"] == account]
    if len(df_acc) > 1:
        df_acc = df_acc.iloc[:-1]
        df_all = pd.concat([df_all[df_all["Account"] != account], df_acc])
        df_all = df_all.sort_values(["Account", "Date"])
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
    f"<h2 style='font-size:1.5rem; margin-bottom:0.5rem;'>🧮 Tracker: {account}</h2>",
    unsafe_allow_html=True
)

# ─── Prepare Account Data ───────────────────────────────────────────────────
account_df = df_all[df_all["Account"] == account].copy()
if account_df.empty:
    account_df = pd.DataFrame([
        {"Account": account, "Date": pd.to_datetime(date.today()), "Daily P/L": 0.0, "Balance": start_balance}
    ])
account_df = account_df.sort_values("Date")

initial_balance = account_df.iloc[0]["Balance"]
last_balance = account_df.iloc[-1]["Balance"]
daily_delta = account_df.iloc[-1]["Daily P/L"]
progress_pct = min(last_balance / target_balance if target_balance else 0, 1.0)

# ─── Metrics & Progress ─────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 2])
col1.metric("🏁 Start", f"${initial_balance:,.2f}")
col2.metric("💹 Current", f"${last_balance:,.2f}", delta=f"{daily_delta:+.2f}")
col3.metric("📊 Progress", f"{progress_pct*100:.1f}%", delta=f"{last_balance-initial_balance:+.2f}")
st.progress(progress_pct)

# ─── Plot Function ─────────────────────────────────────────────────────────
def plot_balance(df: pd.DataFrame, target: float):
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#222222")  # dark background
    ax.set_facecolor("#333333")         # darker plot area
    ax.plot(
        df["Date"], df["Balance"],
        color="#00FF00", linewidth=2.5,
        marker="o", markersize=6,
        markerfacecolor="#00FF00", markeredgecolor="#222222"
    )
    ax.axhline(target, linestyle="--", color="#555555", linewidth=2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate()
    ax.set_title("Balance Progress", fontsize=14, color="#DDDDDD")
    ax.set_xlabel("Date", color="#DDDDDD")
    ax.set_ylabel("Balance ($)", color="#DDDDDD")
    ax.tick_params(axis='x', colors='#DDDDDD')
    ax.tick_params(axis='y', colors='#DDDDDD')
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_color('#DDDDDD')
    return fig

# ─── Chart & Table ─────────────────────────────────────────────────────────
st.subheader("Balance Over Time")
st.pyplot(plot_balance(account_df, target_balance), use_container_width=True)

st.subheader("Entries")
st.dataframe(account_df[["Date", "Daily P/L", "Balance"]], use_container_width=True)
