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

# ─── Load Data ──────────────────────────────────────────────────────────────
def load_data(file_path: str) -> pd.DataFrame:
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, parse_dates=["Date"], infer_datetime_format=True)
        df = df.dropna(subset=["Date"])
    else:
        df = pd.DataFrame(columns=["Account", "Date", "Daily P/L"])
    return df

df_all = load_data(CSV_FILE)

# ─── Sidebar Controls ───────────────────────────────────────────────────────
st.sidebar.header("👤 Account")
account = st.sidebar.selectbox(
    "Select Account", ["Account A", "Account B"]
)

st.sidebar.header("🗒️ Data Entry")
entry_date = st.sidebar.date_input(
    "Date", value=date.today()
)
daily_pl = st.sidebar.number_input(
    "Today's P/L",
    value=0.0,
    step=0.01,
    format="%.2f",
    key='daily_pl'
)

st.sidebar.header("⚙️ Settings")
# Use session_state.get to allow persistent, editable defaults
start_balance = st.sidebar.number_input(
    "Starting Balance",
    value=st.session_state.get('start_balance', 1000.0),
    step=100.0,
    format="%.2f",
    key='start_balance'
)
profit_target = st.sidebar.number_input(
    "Profit Target",
    value=st.session_state.get('profit_target', 2000.0),
    step=100.0,
    format="%.2f",
    key='profit_target'
)

# ─── Add Entry ─────────────────────────────────────────────────────────────
if st.sidebar.button("➕ Add Entry"):
    df_acc = df_all[df_all["Account"] == account]
    if df_acc["Date"].eq(pd.to_datetime(entry_date)).any():
        st.sidebar.warning("An entry for that date already exists.")
    else:
        new_row = {"Account": account, "Date": pd.to_datetime(entry_date), "Daily P/L": daily_pl}
        df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True)
        df_all = df_all.sort_values(["Account", "Date"])
        df_all.to_csv(CSV_FILE, index=False)
        st.session_state['notification'] = f"✅ Logged {daily_pl:+.2f} for {account}"

# ─── Undo Last Entry ───────────────────────────────────────────────────────
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

# ─── Dashboard & Notification ──────────────────────────────────────────────
if 'notification' not in st.session_state:
    st.session_state['notification'] = None
if st.session_state['notification']:
    st.info(st.session_state.pop('notification'), icon="🔔")

st.markdown(
    f"<h2 style='font-size:1.5rem; margin-bottom:0.5rem;'>🧮 Tracker: {account}</h2>",
    unsafe_allow_html=True
)

# ─── Prepare Data & Compute Balances ────────────────────────────────────────
df_acc = df_all[df_all["Account"] == account].copy()
if df_acc.empty:
    df_acc = pd.DataFrame([
        {"Account": account, "Date": pd.to_datetime(date.today()), "Daily P/L": 0.0}
    ])
df_acc = df_acc.sort_values("Date")

# Compute running balance from editable start_balance
start_bal = st.session_state['start_balance']
df_acc['Balance'] = df_acc['Daily P/L'].cumsum() + start_bal

# Compute metrics
today_delta = df_acc.iloc[-1]['Daily P/L']
current_balance = df_acc.iloc[-1]['Balance']
progress_pct = min(
    current_balance / st.session_state['profit_target'] if st.session_state['profit_target'] else 0,
    1.0
)

# ─── Metrics & Progress ─────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 2])
col1.metric("🏁 Start", f"${start_bal:,.2f}")
col2.metric("💹 Current", f"${current_balance:,.2f}", delta=f"{today_delta:+.2f}")
col3.metric("📊 Progress", f"{progress_pct*100:.1f}%", delta=f"{current_balance-start_bal:+.2f}")
st.progress(progress_pct)

# ─── Plot ───────────────────────────────────────────────────────────────────
st.subheader("Balance Over Time")
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor("#222222")
ax.set_facecolor("#333333")
ax.plot(
    df_acc['Date'], df_acc['Balance'],
    marker='o', linewidth=2.5, color="#00FF00"
)
ax.axhline(
    st.session_state['profit_target'],
    linestyle='--', linewidth=2, color="#555555"
)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
fig.autofmt_xdate()
ax.set_title("Balance Progress", color="#DDDDDD")
ax.set_xlabel("Date", color="#DDDDDD")
ax.set_ylabel("Balance ($)", color="#DDDDDD")
ax.tick_params(colors="#DDDDDD")
ax.grid(False)
for spine in ax.spines.values():
    spine.set_color('#DDDDDD')
st.pyplot(fig, use_container_width=True)

# ─── Entries Table ─────────────────────────────────────────────────────────
st.subheader("Entries")
st.dataframe(df_acc[["Date", "Daily P/L", "Balance"]], use_container_width=True)
