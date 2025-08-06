import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Constants
CSV_FILE = "tracker.csv"
ACCOUNTS = ["Account A", "Account B"]
DATE_FORMAT = "%Y-%m-%d"

# Page configuration
st.set_page_config(page_title="Tracker", layout="wide", initial_sidebar_state="expanded")

@st.cache_data
 def load_data(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["Date"] )
        return df.dropna(subset=["Date"]) 
    return pd.DataFrame(columns=["Date", "Account", "P/L"])

 def save_data(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)

# Load existing data
 df = load_data(CSV_FILE)

# Sidebar: Data entry form
 st.sidebar.header("Add new entry")
 with st.sidebar.form(key="entry_form"):
    date_input = st.date_input("Date", value=datetime.today())
    account = st.selectbox("Account", ACCOUNTS)
    pl_value = st.number_input("Profit/Loss", format="%.2f")
    submitted = st.form_submit_button("Add entry")

    if submitted:
        new_row = {"Date": date_input, "Account": account, "P/L": pl_value}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df, CSV_FILE)
        st.sidebar.success(f"Logged {pl_value:+.2f} for {account}.")

# Sidebar: Undo last entry
 if st.sidebar.button("Undo last entry"):
    if not df.empty:
        df = df.iloc[:-1]
        save_data(df, CSV_FILE)
        st.sidebar.info("Last entry removed.")
    else:
        st.sidebar.warning("No entries to remove.")

# Main view: Data table
 st.header("Profit & Loss Tracker")
 if df.empty:
    st.info("No data available. Add entries from the sidebar.")
 else:
    df_sorted = df.sort_values(["Date", "Account"]) .reset_index(drop=True)
    st.dataframe(df_sorted)

    # Plot cumulative P/L per account
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor('#000000')
    ax.set_facecolor('#000000')
    ax.grid(False)

    for acct in df_sorted['Account'].unique():
        sub = df_sorted[df_sorted['Account'] == acct]
        sub = sub.groupby('Date')['P/L'].sum().cumsum().reset_index()
        ax.plot(sub['Date'], sub['P/L'], label=acct)

    # Styling
    ax.legend(facecolor='#000000', framealpha=0.5, edgecolor='white', labelcolor='white')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    ax.tick_params(colors='lightgrey')
    ax.yaxis.label.set_color('lightgrey')
    ax.xaxis.label.set_color('lightgrey')
    ax.title.set_color('lightgrey')
    ax.spines['bottom'].set_color('lightgrey')
    ax.spines['top'].set_color('lightgrey')
    ax.spines['left'].set_color('lightgrey')
    ax.spines['right'].set_color('lightgrey')

    st.pyplot(fig)
