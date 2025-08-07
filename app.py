import os
import json
from datetime import date, datetime
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

st.set_page_config(page_title="Tracker", page_icon="💰", layout="wide")
CSV_FILE = "tracker.csv"
SETTINGS_FILE = "settings.json"
ACCOUNTS = ["Account A", "Account B"]

# ─── Reset Handling ────────────────────────────────────
if st.session_state.get("reset_triggered"):
    st.cache_data.clear()
    st.session_state.clear()
    st.session_state["just_reset"] = True
    st.experimental_rerun()

if st.session_state.get("just_reset"):
    st.info("✅ App reset successfully.")
    del st.session_state["just_reset"]

# ─── Settings Storage ───────────────────────────
def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}

def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

settings = load_settings()

# ─── Ensure Defaults ──────────────────────────
for acct in ACCOUNTS:
    settings.setdefault(f"start_balance_{acct}", 1000.0)
    settings.setdefault(f"profit_target_{acct}", 2000.0)
    settings.setdefault(f"last_date_{acct}", str(date.today()))
    settings.setdefault(f"daily_pl_{acct}", 0.0)
    st.session_state.setdefault(f"daily_pl_{acct}", settings[f"daily_pl_{acct}"])
    st.session_state.setdefault(f"last_date_{acct}", settings[f"last_date_{acct}"])

save_settings(settings)

# ─── Data Loading ───────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    if os.path.exists(CSV_FILE):
        return (
            pd.read_csv(CSV_FILE, parse_dates=["Date"], dtype={"Daily P/L": float})
              .dropna(subset=["Date"])
        )
    return pd.DataFrame(columns=["Account", "Date", "Daily P/L"])

df_all = load_data()
df_all["Date"] = pd.to_datetime(df_all["Date"])

# ─── Sidebar Inputs ───────────────────────────
with st.sidebar:
    st.header("📋 Account Entry")
    account = st.selectbox(
        "Account",
        ACCOUNTS,
        index=ACCOUNTS.index(settings.get("last_account", ACCOUNTS[0]))
    )
    settings["last_account"] = account

    entry_date = st.date_input(
        "Date",
        value=pd.to_datetime(settings[f"last_date_{account}"])
    )
    daily_pl = st.number_input(
        "Today's P/L",
        step=0.01,
        format="%.2f",
        key=f"daily_pl_{account}"
    )
    settings[f"last_date_{account}"] = str(entry_date)
    settings[f"daily_pl_{account}"] = daily_pl

    sb = st.number_input(
        "Starting Balance",
        value=settings[f"start_balance_{account}"],
        step=100.0,
        format="%.2f"
    )
    pt = st.number_input(
        "Profit Target",
        value=settings[f"profit_target_{account}"],
        step=100.0,
        format="%.2f"
    )
    settings[f"start_balance_{account}"], settings[f"profit_target_{account}"] = sb, pt

    save_settings(settings)

    if st.button("➕ Add Entry"):
        new_row = pd.DataFrame([{
            "Account": account,
            "Date": pd.to_datetime(entry_date),
            "Daily P/L": daily_pl
        }])
        df_all = pd.concat([df_all, new_row], ignore_index=True)
        df_all.sort_values(["Account", "Date"], inplace=True)
        df_all.to_csv(CSV_FILE, index=False)

    if st.button("↩️ Undo Last"):
        df_acc = df_all[df_all["Account"] == account]
        if not df_acc.empty:
            last_idx = df_acc.index[-1]
            df_all.drop(last_idx, inplace=True)
            df_all.to_csv(CSV_FILE, index=False)
        else:
            st.warning("No entries to undo")

    if st.checkbox("⚠️ Reset All Data", key="reset_confirm"):
        if st.button("Confirm Reset"):
            for file in (CSV_FILE, SETTINGS_FILE):
                if os.path.exists(file):
                    os.remove(file)
            st.session_state["reset_triggered"] = True
            st.success("✅ Files removed. Reloading app...")

    # Calculate & display today’s true P/L
    today = date.today()
    mask_today = (
        (df_all["Account"] == account)
        & (df_all["Date"].dt.date == today)
    )
    today_pl = df_all.loc[mask_today, "Daily P/L"].sum()
    settings[f"daily_pl_{account}"] = today_pl
    save_settings(settings)
    st.metric("🗖️ Today's P/L", f"{today_pl:+.2f}")

# ─── Tabs for Account Comparison ──────────────────────────
tabs = st.tabs([f"📊 {acct}" for acct in ACCOUNTS])
for i, acct in enumerate(ACCOUNTS):
    with tabs[i]:
        st.markdown(f"## Tracker: {acct}")
        df_acc = df_all[df_all["Account"] == acct].copy().sort_values("Date")
        sb = settings[f"start_balance_{acct}"]
        pt = settings[f"profit_target_{acct}"]

        if df_acc.empty:
            df_acc = pd.DataFrame([{
                "Account": acct,
                "Date": pd.to_datetime(date.today()),
                "Daily P/L": 0.0
            }])

        df_acc["Balance"] = df_acc["Daily P/L"].cumsum() + sb
        curr = df_acc.iloc[-1]["Balance"]
        gain = df_acc.iloc[-1]["Daily P/L"]
        pct_gain = (curr - sb) / sb * 100

        # --- PATCH: Show Today's P/L beside Current, no HTML ---
        today = date.today()
        mask_today = (df_acc["Date"].dt.date == today)
        today_pl_tab = df_acc.loc[mask_today, "Daily P/L"].sum()

        cols = st.columns(2)
        cols[0].metric("Start", f"${sb:,.2f}")
        cols[1].metric(
            "Current",
            f"${curr:,.2f}  Today P/L {today_pl_tab:+.2f}",
            delta=f"{pct_gain:+.2f}%",
            help="Current balance and today's P/L"
        )
        # --- END PATCH ---

        # --- Neon Progress Bar ---
        prog = min(curr / pt if pt else 0, 1.0)
        st.markdown(f"""
            <style>
            @keyframes neon {{
                0% {{ box-shadow: 0 0 10px #00eaff; }}
                50% {{ box-shadow: 0 0 35px #00eaff; }}
                100% {{ box-shadow: 0 0 10px #00eaff; }}
            }}
            .neon-bar {{
                background: linear-gradient(90deg, #00eaff, #0af);
                height: 25px;
                width: {prog*100:.1f}%;
                border-radius: 12px;
                animation: neon 1.4s infinite;
                transition: width 0.6s;
            }}
            .bar-container {{
                background: #181c24;
                border-radius: 12px;
                overflow: hidden;
                margin-bottom: 12px;
                border: 2px solid #00eaff22;
            }}
            </style>
            <div class="bar-container"><div class="neon-bar"></div></div>
        """, unsafe_allow_html=True)
        st.write(f"<b>{prog*100:.1f}% to target</b>", unsafe_allow_html=True)

        if gain > 0:
            st.success("📈 Great! You're in profit today. Keep up the momentum!")
        elif gain < 0:
            st.warning("📉 Loss today. Review what went wrong.")
        else:
            st.info("🧘‍♂️ Neutral day. Stay consistent.")

        if len(df_acc) >= 3:
            last_3 = df_acc.tail(3)["Daily P/L"].values
            if last_3[-1] < 0 and last_3[-2] > 0 and last_3[-3] > 0:
                st.info("🤖 Tip: Two wins followed by a loss — consider taking partial profits next time.")

        if len(df_acc) > 1:
            start, end = st.date_input(
                "Date Range",
                [df_acc["Date"].min(), df_acc["Date"].max()],
                key=f"range_{acct}"
            )
            df_acc = df_acc[
                (df_acc['Date'] >= pd.to_datetime(start))
                & (df_acc['Date'] <= pd.to_datetime(end))
            ]

        st.subheader("Balance Over Time")
        fig, ax = plt.subplots(figsize=(8, 4), facecolor='#222')
        ax.set_facecolor('#333')
        ax.plot(df_acc['Date'], df_acc['Balance'], color='#00FFFF', linewidth=2.5)
        ax.fill_between(df_acc['Date'], df_acc['Balance'], color='#00FFFF', alpha=0.2)
        ax.set(title='Balance Progress', xlabel='Date', ylabel='Balance ($)')
        ax.tick_params(colors='#39FF14')
        for spine in ax.spines.values():
            spine.set_color('#39FF14')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        fig.autofmt_xdate()
        ax.grid(False)
        st.pyplot(fig, use_container_width=True)

        st.subheader("Entries")
        st.dataframe(
            df_acc.style
                .format({
                    'Date': '{:%Y-%m-%d}',
                    'Daily P/L': '{:+.2f}',
                    'Balance': '{:,.2f}'
                })
                .applymap(
                    lambda v: 'color:#39FF14' if isinstance(v, (int, float)) and v >= 0 else 'color:#FF0055',
                    subset=['Daily P/L']
                ),
            use_container_width=True
        )
