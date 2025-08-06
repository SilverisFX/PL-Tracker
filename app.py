import os
import json
from datetime import date, datetime
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import time
import altair as alt

# ─── Config ─────────────────────────────────────────────────────
st.set_page_config(page_title="Tracker", layout="wide")
CSV_FILE = "tracker.csv"
SETTINGS_FILE = "settings.json"
ACCOUNTS = ["Account A", "Account B"]

# ─── Responsive CSS ─────────────────────────────────────────────
st.markdown("""
<style>
@media (max-width: 768px) {
  .css-1d391kg { width:100vw!important; left:0!important; }
  .css-18e3th9 { padding:1rem!important; width:100vw!important; margin:0 auto!important; }
}
@media (max-width: 600px) {
  .metric-container > div { width:100% !important; margin-bottom:0.75rem; }
}
.css-18e3th9 {
  background-image: linear-gradient(135deg, rgba(0,0,0,0.1) 25%, transparent 25%, transparent 50%, rgba(0,0,0,0.1) 50%, rgba(0,0,0,0.1) 75%, transparent 75%, transparent);
  background-size: 20px 20px;
}
.metric-container, .progress-container {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: #222222;
  padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ─── Settings Storage ──────────────────────────────────────────
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

# ─── Load Data ─────────────────────────────────────────────────
@st.cache_data
def load_data(fp: str) -> pd.DataFrame:
    if os.path.exists(fp):
        df = pd.read_csv(fp, parse_dates=["Date"])
        return df.dropna(subset=["Date"])
    return pd.DataFrame(columns=["Account","Date","Daily P/L"])

df_all = load_data(CSV_FILE)

# ─── Session State Init ────────────────────────────────────────
for acct in ACCOUNTS:
    st.session_state.setdefault(f"start_balance_{acct}", settings.get(f"start_balance_{acct}", 1000.0))
    st.session_state.setdefault(f"profit_target_{acct}", settings.get(f"profit_target_{acct}", 2000.0))

# ─── Sidebar: Account & Entry ──────────────────────────────────
with st.sidebar.expander("Account & Entry", expanded=True):
    last_ac = settings.get("last_account", ACCOUNTS[0])
    account = st.selectbox("Select Account", ACCOUNTS, index=ACCOUNTS.index(last_ac))
    settings["last_account"] = account

    entry_date = st.date_input("Date", value=pd.to_datetime(settings.get(f"last_date_{account}", str(date.today()))))
    key_pl = f"daily_pl_{account}"
    st.session_state.setdefault(key_pl, float(settings.get(key_pl, 0.0)))
    daily_pl = st.number_input("Today's P/L", step=0.01, format="%.2f", value=st.session_state[key_pl], key=key_pl)
    settings[f"last_date_{account}"] = str(entry_date)
    settings[key_pl] = daily_pl

# ─── Sidebar: Settings ─────────────────────────────────────────
with st.sidebar.expander("Settings", expanded=False):
    sb_val = st.number_input("Starting Balance", value=st.session_state[f"start_balance_{account}"], step=100.0, format="%.2f")
    pt_val = st.number_input("Profit Target", value=st.session_state[f"profit_target_{account}"], step=100.0, format="%.2f")
    st.session_state[f"start_balance_{account}"] = sb_val
    st.session_state[f"profit_target_{account}"] = pt_val
    settings[f"start_balance_{account}"] = sb_val
    settings[f"profit_target_{account}"] = pt_val

save_settings(settings)

# ─── Entry Controls ─────────────────────────────────────────────
if st.sidebar.button("Add Entry"):
    new = {"Account": account, "Date": pd.to_datetime(entry_date), "Daily P/L": daily_pl}
    df_all = pd.concat([df_all, pd.DataFrame([new])], ignore_index=True).sort_values(["Account","Date"])
    df_all.to_csv(CSV_FILE, index=False)
    st.session_state["notification"] = f"Logged {daily_pl:+.2f} for {account}."
    save_settings(settings)

if st.sidebar.button("Undo"):
    df_acc = df_all[df_all["Account"] == account]
    if not df_acc.empty:
        df_all = pd.concat([df_all[df_all["Account"] != account], df_acc.iloc[:-1]])
        df_all.to_csv(CSV_FILE, index=False)
        st.sidebar.success("Last entry removed.")
    else:
        st.sidebar.warning("Nothing to undo.")
    save_settings(settings)

# ─── Notifications ─────────────────────────────────────────────
if notif := st.session_state.pop("notification", None):
    st.info(notif)

# ─── Header ────────────────────────────────────────────────────
st.markdown(f"## Tracker: {account}")
st.markdown(f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" )

# ─── Download CSV ───────────────────────────────────────────────
st.download_button(label="Download CSV", data=df_all.to_csv(index=False), file_name="tracker_export.csv")

# ─── Prepare Data ──────────────────────────────────────────────
sb = st.session_state[f"start_balance_{account}"]
pt = st.session_state[f"profit_target_{account}"]
df_acc = df_all[df_all["Account"] == account].copy()
if df_acc.empty:
    df_acc = pd.DataFrame([{"Account": account, "Date": pd.to_datetime(date.today()), "Daily P/L": 0.0}])
df_acc.sort_values("Date", inplace=True)
df_acc["Balance"] = df_acc["Daily P/L"].cumsum() + sb

curr_bal = df_acc.iloc[-1]["Balance"]
pct_gain = (curr_bal - sb) / sb * 100
prog_pct = min(curr_bal / pt if pt else 0, 1.0)

# ─── Animated Counter ──────────────────────────────────────────
counter = st.empty()
for val in np.linspace(sb, curr_bal, 30):
    counter.metric("Balance", f"${val:,.2f}")
    time.sleep(0.05)
counter.empty()

# ─── Metrics & Progress ────────────────────────────────────────
st.markdown('<div class="metric-container" style="display:flex;gap:1rem;flex-wrap:wrap;">', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.metric("Start", f"${sb:,.2f}")
c2.metric("Current", f"${curr_bal:,.2f}", delta=f"{pct_gain:+.2f}%")
c3.metric("Progress", f"{prog_pct*100:.1f}%", delta=f"${curr_bal - sb:+.2f}")
st.markdown('</div>', unsafe_allow_html=True)

# ─── Balance Chart ─────────────────────────────────────────────
st.subheader("Balance Over Time")
fig, ax = plt.subplots(figsize=(10,5), facecolor='#222222')
ax.set_facecolor('#333333')
neon_text = '#39FF14'
neon_blue = '#00FFFF'
ax.plot(df_acc['Date'], df_acc['Balance'], linewidth=2.5, color=neon_blue)
ax.fill_between(df_acc['Date'], df_acc['Balance'], color=neon_blue, alpha=0.2)
ax.set_title('Balance Progress', color=neon_text)
ax.set_xlabel('Date', color=neon_text)
ax.set_ylabel('Balance ($)', color=neon_text)
ax.tick_params(colors=neon_text)
for spine in ax.spines.values(): spine.set_color(neon_text)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax.grid(False)
st.pyplot(fig, use_container_width=True)

if prog_pct >= 1.0:
    st.balloons()

# ─── Interactive Chart ─────────────────────────────────────────
chart = alt.Chart(df_acc).mark_line(strokeWidth=3).encode(
    x='Date:T', y='Balance:Q', tooltip=['Date', 'Balance']
).interactive()
st.altair_chart(chart, use_container_width=True)

# ─── Entries Table ─────────────────────────────────────────────
st.subheader('Entries')
def color_pl(val): return 'color: #39FF14' if val >= 0 else 'color: #FF0055'
st.dataframe(
    df_acc[['Date','Daily P/L','Balance']]
    .style.applymap(color_pl, subset=['Daily P/L'])
    .format({'Date': lambda v: v.strftime('%Y-%m-%d'),'Daily P/L': '{:+.2f}','Balance': '{:,.2f}'})
, use_container_width=True)
