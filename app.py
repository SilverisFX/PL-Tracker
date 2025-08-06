import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from datetime import date

st.set_page_config(page_title="P/L Tracker", layout="wide")

CSV = "tracker.csv"
START_BAL = 1000.0
TARGET   = 2000.0

# Load or initialize
if os.path.exists(CSV):
    df = pd.read_csv(CSV, parse_dates=["date"])
else:
    df = pd.DataFrame([{"date": date.today(), "pl": 0.0, "balance": START_BAL}])
    df.to_csv(CSV, index=False)

st.title("📈 Daily P/L Tracker")
today_pl = st.number_input("Today’s Profit / (Loss)", value=0.0, step=1.0, format="%.2f")
if st.button("Log & Update"):
    last_bal = df.iloc[-1].balance
    new_bal  = last_bal + today_pl
    df       = df.append({"date": date.today(), "pl": today_pl, "balance": new_bal}, ignore_index=True)
    df.to_csv(CSV, index=False)
    st.success(f"Logged {today_pl:+.2f}, balance→ {new_bal:.2f}")

st.subheader("Balance Over Time")
fig, ax = plt.subplots()
ax.plot(df["date"], df["balance"], marker="o")
ax.axhline(TARGET, linestyle="--", label=f"Target ({TARGET})")
ax.set_xlabel("Date"); ax.set_ylabel("Balance"); ax.legend()
st.pyplot(fig)
