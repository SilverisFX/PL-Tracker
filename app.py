import os
import json
from datetime import date

import pandas as pd
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
def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

settings = load_settings()

# ─── Data Loading ──────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    if os.path.exists(CSV_FILE):
        return pd.read_csv(
            CSV_FILE,
            parse_dates=["Date"],
            dtype={"Daily P/L": float}
        ).dropna(subset=["Date"])
    return pd.DataFrame(columns=["Account", "Date", "Daily P/L"])

# initialize
if "df_all" not in st.session_state:
    st.session_state.df_all = load_data()

df_all = st.session_state.df_all

# ─── Sidebar Inputs ────────────────────────────────────────────
st.sidebar.header("Account & Entry")

account = st.sidebar.selectbox(
    "Account",
    ACCOUNTS,
    index=ACCOUNTS.index(settings.get("last_account", ACCOUNTS[0]))
)
settings["last_account"] = account

entry_date = st.sidebar.date_input(
    "Date",
    value=pd.to_datetime(settings.get(f"last_date_{account}", date.today()))
)

daily_pl = st.sidebar.number_input(
    "Today's P/L",
    step=0.01,
    format="%.2f",
    key=f"daily_pl_{account}"
)
settings[f"last_date_{account}"] = str(entry_date)
settings[f"daily_pl_{account}"] = daily_pl

sb = st.sidebar.number_input(
    "Starting Balance",
    value=settings.get(f"start_balance_{account}", 1000.0),
    step=100.0,
    format="%.2f"
)
pt = st.sidebar.number_input(
    "Profit Target",
    value=settings.get(f"profit_target_{account}", 2000.0),
    step=100.0,
    format="%.2f"
)
settings[f"start_balance_{account}"], settings[f"profit_target_{account}"] = sb, pt

save_settings(settings)

# Add Entry
def add_entry():
    new_row = pd.DataFrame([
        {"Account": account, "Date": pd.to_datetime(entry_date), "Daily P/L": daily_pl}
    ])
    st.session_state.df_all = pd.concat([st.session_state.df_all, new_row], ignore_index=True)
    st.session_state.df_all.sort_values(["Account", "Date"], inplace=True)
    st.session_state.df_all.to_csv(CSV_FILE, index=False)
    st.experimental_rerun()

if st.sidebar.button("Add Entry"):
    add_entry()

# Undo Last
def undo_last():
    df_acc = st.session_state.df_all[st.session_state.df_all["Account"] == account]
    if not df_acc.empty:
        last_idx = df_acc.index[-1]
        st.session_state.df_all = st.session_state.df_all.drop(last_idx)
        st.session_state.df_all.to_csv(CSV_FILE, index=False)
        st.experimental_rerun()
    else:
        st.warning("No entries to undo")

if st.sidebar.button("Undo Last"):
    undo_last()

# Reset All Data
def reset_all():
    for file in (CSV_FILE, SETTINGS_FILE):
        if os.path.exists(file):
            os.remove(file)
    settings.clear()
    st.session_state.df_all = pd.DataFrame(columns=["Account", "Date", "Daily P/L"])
    save_settings(settings)
    st.experimental_rerun()

confirm = st.sidebar.checkbox("I understand this will delete ALL data permanently")
if confirm and st.sidebar.button("Reset All Data"):
    reset_all()

# ─── Main Display ──────────────────────────────────────────────
st.markdown(f"## Tracker: {account}")

df_acc = st.session_state.df_all[st.session_state.df_all["Account"] == account].copy()
if df_acc.empty:
    df_acc = pd.DataFrame([{"Account": account, "Date": date.today(), "Daily P/L": 0.0}])
df_acc.sort_values("Date", inplace=True)

sb = settings.get(f"start_balance_{account}", 1000.0)
pt = settings.get(f"profit_target_{account}", 2000.0)

# Calculate balance
=df_acc["Balance"] = df_acc["Daily P/L"].cumsum() + sb
curr = df_acc.iloc[-1]["Balance"]
pct_gain = (curr - sb) / sb * 100
prog = min(curr / pt if pt else 0, 1.0)

# Metrics
cols = st.columns(2)
cols[0].metric("Start", f"${sb:,.2f}")
cols[1].metric("Current", f"${curr:,.2f}", delta=f"{pct_gain:+.2f}%")

# Progress Bar
st.subheader("Progress to Target")
st.markdown(f"""
<style>
@keyframes neon {{
  0% {{box-shadow: 0 0 5px #87CEFA;}}
  50% {{box-shadow: 0 0 20px #87CEFA;}}
  100% {{box-shadow: 0 0 5px #87CEFA;}}
}}
.neon-bar {{
  background: #87CEFA;
  height: 25px;
  width: {prog*100:.1f}%;
  border-radius: 12px;
  animation: neon 2s infinite;
}}
.bar-container {{
  background: #222;
  border-radius: 12px;
  overflow: hidden;
}}
</style>
<div class="bar-container">
  <div class="neon-bar"></div>
</div>
""", unsafe_allow_html=True)
st.write(f"{prog*100:.1f}% to target")

# Balance Chart
st.subheader("Balance Over Time")
fig, ax = plt.subplots(figsize=(8,4), facecolor='#222')
ax.set_facecolor('#333')
ax.plot(df_acc['Date'], df_acc['Balance'], linewidth=2.5)
ax.fill_between(df_acc['Date'], df_acc['Balance'], alpha=0.2)
ax.set(title='Balance Progress', xlabel='Date', ylabel='Balance ($)')
ax.tick_params(colors='#39FF14')
for spine in ax.spines.values():
    spine.set_color('#39FF14')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
fig.autofmt_xdate()
ax.grid(False)
st.pyplot(fig, use_container_width=True)

# Entries Table
st.subheader('Entries')
st.dataframe(
    df_acc.style
        .format({'Date':'{:%Y-%m-%d}', 'Daily P/L':'{:+.2f}', 'Balance':'{:,.2f}'})
        .applymap(
            lambda v: 'color:#39FF14' if isinstance(v, (int, float)) and v >= 0 else 'color:#FF0055',
            subset=['Daily P/L']
        ),
    use_container_width=True
)
