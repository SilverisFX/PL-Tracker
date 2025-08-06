import os
import json
from datetime import date
import pandas as pd
import streamlit as st
import matplotlib.dates as mdates
import plotly.graph_objects as go

# ─── Page Config ───────────────────────────────────────────────
st.set_page_config(page_title="Tracker", page_icon="💰", layout="wide", initial_sidebar_state="expanded")
CSV_FILE = "tracker.csv"
SETTINGS_FILE = "settings.json"
ACCOUNTS = ["Account A", "Account B"]

# ─── Responsive CSS ────────────────────────────────────────────
st.markdown("""
<style>
@media (max-width: 768px) {
  .css-1d391kg { width:100vw!important; position:relative!important; left:0!important; }
  .css-18e3th9 { padding:1rem!important; width:100vw!important; margin:0 auto!important; }
}
@media (max-width: 600px) {
  .metric-container > div { width:100% !important; margin-bottom:0.75rem; }
}
</style>
""", unsafe_allow_html=True)

# ─── Settings Storage ──────────────────────────────────────────
def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
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
    return pd.DataFrame(columns=["Account", "Date", "Daily P/L"])

df_all = load_data(CSV_FILE)

# ─── Session State Initialization ──────────────────────────────
for acct in ACCOUNTS:
    st.session_state.setdefault(f"start_balance_{acct}", settings.get(f"start_balance_{acct}", 1000.0))
    st.session_state.setdefault(f"profit_target_{acct}", settings.get(f"profit_target_{acct}", 2000.0))

# ─── Sidebar Controls in Expanders ─────────────────────────────
with st.sidebar.expander("🔄 Account & Entry", expanded=True):
    last_account = settings.get("last_account", ACCOUNTS[0])
    account = st.selectbox("Select Account", ACCOUNTS, index=ACCOUNTS.index(last_account))
    settings["last_account"] = account

    entry_date = st.date_input(
        "Date",
        value=pd.to_datetime(settings.get(f"last_date_{account}", str(date.today())))
    )
    daily_pl = st.number_input(
        "Today's P/L",
        step=0.01, format="%.2f",
        value=float(settings.get(f"last_pl_{account}", 0.0)),
        key=f"daily_pl_{account}"
    )
    settings[f"last_date_{account}"] = str(entry_date)
    settings[f"last_pl_{account}"] = daily_pl

with st.sidebar.expander("⚙️ Settings", expanded=False):
    sb_in = st.number_input(
        "Starting Balance",
        value=st.session_state[f"start_balance_{account}"],
        step=100.0, format="%.2f"
    )
    pt_in = st.number_input(
        "Profit Target",
        value=st.session_state[f"profit_target_{account}"],
        step=100.0, format="%.2f"
    )
    st.session_state[f"start_balance_{account}"] = sb_in
    st.session_state[f"profit_target_{account}"] = pt_in
    settings[f"start_balance_{account}"] = sb_in
    settings[f"profit_target_{account}"] = pt_in

# Persist any changes to settings
save_settings(settings)

# ─── Add / Undo / Reset Controls ──────────────────────────────
if st.sidebar.button("Add Entry"):
    new_row = {"Account": account, "Date": pd.to_datetime(entry_date), "Daily P/L": daily_pl}
    df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True).sort_values(["Account", "Date"])
    df_all.to_csv(CSV_FILE, index=False)
    st.session_state["notification"] = f"✅ Logged {daily_pl:+.2f} for {account}"
    save_settings(settings)

if st.sidebar.button("Undo"):
    df_acc = df_all[df_all["Account"] == account]
    if not df_acc.empty:
        df_all = pd.concat([df_all[df_all["Account"] != account], df_acc.iloc[:-1]])
        df_all.to_csv(CSV_FILE, index=False)
        st.sidebar.success(f"Last entry removed for {account}.")
    else:
        st.sidebar.warning("Nothing to undo.")
    save_settings(settings)

st.sidebar.subheader("Danger Zone")
if st.sidebar.checkbox("Confirm reset all data"):
    if st.sidebar.button("Reset All Data"):
        if os.path.exists(CSV_FILE): os.remove(CSV_FILE)
        if os.path.exists(SETTINGS_FILE): os.remove(SETTINGS_FILE)
        df_all = pd.DataFrame(columns=["Account", "Date", "Daily P/L"])
        for a in ACCOUNTS:
            for k in (f"start_balance_{a}", f"profit_target_{a}"):
                st.session_state.pop(k, None)
        st.session_state["notification"] = "All data reset!"
        save_settings(settings)
        st.rerun()

# ─── Notification ─────────────────────────────────────────────
if st.session_state.get("notification"):
    st.info(st.session_state.pop("notification"), icon="🔔")

# ─── Header ───────────────────────────────────────────────────
st.markdown(f"<h2 style='font-size:1.5rem; margin-bottom:0.5rem;'>Tracker: {account}</h2>", unsafe_allow_html=True)

# ─── Prepare Data & Metrics ────────────────────────────────────
sb = st.session_state[f"start_balance_{account}"]
pt = st.session_state[f"profit_target_{account}"]
df_acc = df_all[df_all["Account"] == account].copy()
if df_acc.empty:
    df_acc = pd.DataFrame([{"Account": account, "Date": pd.to_datetime(date.today()), "Daily P/L": 0.0}])
df_acc = df_acc.sort_values("Date")
df_acc["Balance"] = df_acc["Daily P/L"].cumsum() + sb

today_delta = df_acc.iloc[-1]["Daily P/L"]
curr_bal = df_acc.iloc[-1]["Balance"]
progress_pct = min(curr_bal / pt if pt else 0, 1.0)
pct_gain = (curr_bal - sb) / sb * 100

# ─── Metrics (responsive) ───────────────────────────────────────
st.markdown('<div class="metric-container" style="display:flex; gap:1rem; flex-wrap:wrap;">', unsafe_allow_html=True)
c1, c2, c3 = st.columns([1, 1, 1])
c1.metric("Start", f"${sb:,.2f}")
c2.metric("Current", f"${curr_bal:,.2f}", delta=f"{pct_gain:+.2f}%")
c3.metric("Progress", f"{progress_pct*100:.1f}%", delta=f"${curr_bal-sb:+.2f}")
st.markdown("</div>", unsafe_allow_html=True)

# ─── Heartbeat Animated Balance Chart ────────────────────────────
st.subheader("Balance Over Time (Heartbeat)")
x = df_acc["Date"]
y = df_acc["Balance"]
last_idx = len(x) - 1

fig = go.Figure(
    data=[go.Scatter(
        x=x, y=y,
        mode="lines+markers",
        line=dict(color="#00FF00", width=3),
        marker=dict(size=8, color="#39FF14")
    )],
    layout=go.Layout(
        xaxis=dict(title="Date", tickformat="%b %d", color="#39FF14"),
        yaxis=dict(title="Balance ($)", color="#39FF14"),
        paper_bgcolor="#222222",
        plot_bgcolor="#333333",
        font=dict(color="#39FF14"),
        showlegend=False,
        updatemenus=[dict(
            type="buttons", showactive=False,
            buttons=[dict(label="▶️ Play",
                          method="animate",
                          args=[None, {"frame": {"duration": 800, "redraw": False},
                                       "fromcurrent": True, "transition": {"duration": 0}}])]
        )]
    ),
    frames=[
        go.Frame(data=[go.Scatter(
            x=[x.iat[last_idx]], y=[y.iat[last_idx]],
            mode="markers",
            marker=dict(size=16, color="#FF0055", symbol="heart")
        )]),
        go.Frame(data=[go.Scatter(
            x=[x.iat[last_idx]], y=[y.iat[last_idx]],
            mode="markers",
            marker=dict(size=8, color="#39FF14", symbol="circle")
        )])
    ]
)

st.plotly_chart(fig, use_container_width=True)

# ─── Entries Table ─────────────────────────────────────────────
st.subheader("Entries")
st.dataframe(df_acc[["Date", "Daily P/L", "Balance"]], use_container_width=True)
