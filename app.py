import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from datetime import date

# ─── Page & File Config ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="📈 P/L Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
)
CSV_FILE = "tracker.csv"

# ─── Sidebar Inputs ──────────────────────────────────────────────────────────
st.sidebar.header("Settings & Entry")

# Allow user to override start/target on the fly
start_balance = st.sidebar.number_input(
    "Starting Balance", min_value=0.0, value=1000.0, step=100.0, format="%.2f"
)
target_balance = st.sidebar.number_input(
    "Target Balance", min_value=0.0, value=2000.0, step=100.0, format="%.2f"
)

# Entry for each day
entry_date = st.sidebar.date_input("Date", value=date.today())
daily_pl = st.sidebar.number_input(
    "Today's Profit / (Loss)", value=0.0, step=1.0, format="%.2f"
)

# ─── Load or Initialize Data ─────────────────────────────────────────────────
@st.cache_data
def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, parse_dates=["Date"])
    else:
        df = pd.DataFrame([{
            "Date": entry_date,
            "Daily P/L": 0.0,
            "Balance": start_balance
        }])
        df.to_csv(CSV_FILE, index=False)
    return df

df = load_data()

# ─── Log Button & Data Update ────────────────────────────────────────────────
if st.sidebar.button("Log Entry"):
    last_bal = df.iloc[-1]["Balance"]
    new_bal = last_bal + daily_pl
    new_row = pd.DataFrame([{
        "Date": entry_date,
        "Daily P/L": daily_pl,
        "Balance": new_bal
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    st.sidebar.success(f"Logged {daily_pl:+.2f} on {entry_date}, balance → {new_bal:.2f}")
    st.experimental_rerun()  # refresh to show updated table/chart

# ─── Main View ────────────────────────────────────────────────────────────────
st.title("📈 Daily P/L Tracker")

# Chart
st.subheader("Balance Over Time")
fig, ax = plt.subplots()
ax.plot(df["Date"], df["Balance"], marker="o")
ax.axhline(
    target_balance,
    linestyle="--",
    label=f"Target ({target_balance:.2f})",
)
ax.set_xlabel("Date")
ax.set_ylabel("Balance")
ax.legend(loc="upper left")
st.pyplot(fig)

# Data table
st.subheader("Logged Data")
st.dataframe(df, use_container_width=True)
