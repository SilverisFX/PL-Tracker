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

# ─── Responsive CSS & Patterns ──────────────────────────────────
st.markdown("""
<style>
@media (max-width: 768px) {
  .css-1d391kg { width:100vw!important; left:0!important; }
  .css-18e3th9 { padding:1rem!important; width:100vw!important; margin:0 auto!important; }
}
@media (max-width: 600px) {
  .metric-container > div { width:100% !important; margin-bottom:0.75rem; }
}
/* Subtle diagonal background pattern */
.css-18e3th9 {
  background-image: linear-gradient(135deg, rgba(0,0,0,0.1) 25%, transparent 25%, transparent 50%, rgba(0,0,0,0.1) 50%, rgba(0,0,0,0.1) 75%, transparent 75%, transparent);
  background-size: 20px 20px;
}
/* Sticky header for metrics and progress bar */
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

# ─── Session State Init ────────────────────────────────────────
for acct in ACCOUNTS:
    st.session_state.setdefault(f"start_balance_{acct}", settings.get(f"start_balance_{acct}", 1000.0))
    st.session_state.setdefault(f"profit_target_{acct}", settings.get(f"profit_target_{acct}", 2000.0))

# ─── Sidebar: Account & Entry ──────────────────────────────────
with st.sidebar.expander("🔄 Account & Entry", expanded=True):
    last_ac = settings.get("last_account", ACCOUNTS[0])
    account = st.selectbox("Select Account", ACCOUNTS, index=ACCOUNTS.index(last_ac))
    settings["last_account"] = account

    entry_date = st.date_input(
        "Date",
        value=pd.to_datetime(settings.get(f"last_date_{account}", str(date.today())))
    )

    key_pl = f"daily_pl_{account}"
    default_pl = float(settings.get(key_pl, 0.0))
    st.session_state.setdefault(key_pl, default_pl)
    daily_pl = st.number_input(
        "Today's P/L",
        step=0.01,
        format="%.2f",
        value=st.session_state[key_pl],
        key=key_pl
    )

    settings[f"last_date_{account}"] = str(entry_date)
    settings[key_pl] = daily_pl

# ─── Sidebar: Settings ─────────────────────────────────────────
with st.sidebar.expander("⚙️ Settings", expanded=False):
    sb_val = st.number_input(
        "Starting Balance",
        value=st.session_state[f"start_balance_{account}"],
        step=100.0,
        format="%.2f"
    )
    pt_val = st.number_input(
        "Profit Target",
        value=st.session_state[f"profit_target_{account}"],
        step=100.0,
        format="%.2f"
    )
    st.session_state[f"start_balance_{account}"] = sb_val
    st.session_state[f"profit_target_{account}"] = pt_val
    settings[f"start_balance_{account}"] = sb_val
    settings[f"profit_target_{account}"] = pt_val

# Save any changed settings
save_settings(settings)

# ─── Entry Controls ─────────────────────────────────────────────
if st.sidebar.button("Add Entry"):
    new = {"Account": account, "Date": pd.to_datetime(entry_date), "Daily P/L": daily_pl}
    df_all = pd.concat([df_all, pd.DataFrame([new])], ignore_index=True).sort_values(["Account", "Date"])
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

# ─── Notifications ─────────────────────────────────────────────
if st.session_state.get("notification"):
    st.info(st.session_state.pop("notification"), icon="🔔")

# ─── Header with Clock ─────────────────────────────────────────
st.markdown(
    f"<h2 style='font-size:1.5rem; margin-bottom:0.2rem;'>Tracker: {account}</h2>",
    unsafe_allow_html=True
)
# Live clock and last updated stamp
from datetime import datetime
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"**Last updated:** {now}")

# ─── Data Export Button ─────────────────────────────────────────
csv_data = df_all.to_csv(index=False)
st.download_button(
    label="Download CSV",
    data=csv_data,
    file_name="tracker_export.csv",
    mime="text/csv"
)

# ─── Animated Y-Axis Counter ──────────────────────────────────
import time
import numpy as np
counter_placeholder = st.empty()
steps = 30
for val in np.linspace(sb, curr_bal, steps):
    counter_placeholder.metric("Balance", f"${val:,.2f}")
    time.sleep(0.05)
counter_placeholder.empty()

# ─── Metrics (responsive) ───────────────────────────────────────
st.markdown(
    '<div class="metric-container" style="display:flex; gap:1rem; flex-wrap:wrap;">', unsafe_allow_html=True
)
c1, c2, c3 = st.columns([1, 1, 1])
c1.metric("Start", f"${sb:,.2f}")
c2.metric("Current", f"${curr_bal:,.2f}", delta=f"{pct_gain:+.2f}%")
c3.metric("Progress", f"{prog_pct*100:.1f}%", delta=f"${curr_bal-sb:+.2f}")
st.markdown("</div>", unsafe_allow_html=True)

# ─── View Range Zoom Buttons ───────────────────────────────────
st.subheader("View Range")
col_w, col_m, col_a = st.columns(3)
view = st.session_state.get('view','All')
if col_w.button("1W"): view='1W'
elif col_m.button("1M"): view='1M'
elif col_a.button("All"): view='All'
st.session_state['view']=view

if view == '1W':
    start_date = date.today() - pd.Timedelta(days=7)
    df_plot = df_acc[df_acc['Date'] >= pd.to_datetime(start_date)]
elif view == '1M':
    start_date = date.today() - pd.Timedelta(days=30)
    df_plot = df_acc[df_acc['Date'] >= pd.to_datetime(start_date)]
else:
    df_plot = df_acc.copy()

# ─── Balance Chart with Gradient ────────────────────────────────
st.subheader("Balance Over Time")
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor("#222222")
ax.set_facecolor("#333333")

neon_blue = "#00FFFF"
ax.plot(df_plot["Date"], df_plot["Balance"], linewidth=2.5, color=neon_blue)
ax.fill_between(df_plot["Date"], df_plot["Balance"], color=neon_blue, alpha=0.2)

neon_text = "#39FF14"
ax.set_title("Balance Progress", color=neon_text)
ax.set_xlabel("Date", color=neon_text)
ax.set_ylabel("Balance ($)", color=neon_text)
ax.tick_params(colors=neon_text)
for spine in ax.spines.values(): spine.set_color(neon_text)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
fig.autofmt_xdate()
ax.grid(False)
st.pyplot(fig, use_container_width=True)

if prog_pct >= 1.0:
    st.balloons()

# ─── Interactive Balance Chart (Hover Tooltips) ───────────────
st.subheader("Balance Over Time (Interactive)")
import altair as alt
chart = alt.Chart(df_plot).mark_line(color=neon_blue, strokeWidth=3).encode(
    x=alt.X('Date:T', title='Date'),
    y=alt.Y('Balance:Q', title='Balance ($)'),
    tooltip=[alt.Tooltip('Date:T', title='Date'), alt.Tooltip('Balance:Q', title='Balance')]
).properties(
    width='container', height=300
).configure_axis(
    labelColor=neon_text,
    titleColor=neon_text
).configure_title(
    color=neon_text
).interactive()
st.altair_chart(chart, use_container_width=True)

# ─── Animate Build on Demand ───────────────────────────────────
st.subheader("Animate Balance Build")
if st.button("Replay Build"):
    placeholder = st.empty()
    for i in range(1, len(df_plot)+1):
        fig, ax = plt.subplots(figsize=(10, 3))
        fig.patch.set_facecolor("#222222")
        ax.set_facecolor("#333333")
        ax.plot(df_plot['Date'][:i], df_plot['Balance'][:i], color=neon_blue, linewidth=2.5)
        ax.set_title("Building Balance...", color=neon_text)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.tick_params(colors=neon_text)
        for spine in ax.spines.values(): spine.set_color(neon_text)
        ax.grid(False)
        placeholder.pyplot(fig, use_container_width=True)
        time.sleep(0.05)
    placeholder.empty()

# ─── Balance Sparkline ─────────────────────────────────────────
st.subheader("Balance Sparkline")
st.line_chart(df_acc.set_index('Date')['Balance'], use_container_width=True)

# ─── Entries Table ─────────────────────────────────────────────
st.subheader("Entries")
# Conditional formatting: positive P/L green, negative red
def color_pl(val):
    color = '#39FF14' if val >= 0 else '#FF0055'
    return f'color: {color}'
styled_df = df_acc[["Date", "Daily P/L", "Balance"]] \
    .style \
    .applymap(color_pl, subset=["Daily P/L"]) \
    .format({"Date": lambda v: v.strftime('%Y-%m-%d'), "Daily P/L": '{:+.2f}', "Balance": '{:,.2f}'})
st.dataframe(styled_df, use_container_width=True)
