import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

# ---------------------
# Database Utilities   
# ---------------------
DB_FILE = 'trading_tracker.db'

@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            account TEXT NOT NULL,
            pl REAL NOT NULL
        )
    ''')
    return conn

@st.cache_data
def load_entries():
    conn = get_db_connection()
    df = pd.read_sql('SELECT * FROM entries', conn, parse_dates=['entry_date'])
    return df

def add_entry(entry_date: str, account: str, pl: float):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO entries (entry_date, account, pl) VALUES (?, ?, ?)',
        (entry_date, account, pl)
    )
    conn.commit()
    # clear cache
    load_entries.clear()

# ---------------------
# Streamlit App       
# ---------------------
st.set_page_config(page_title='Trading Tracker', layout='wide')
st.title('📊 Trading Account Profit & Loss Tracker')

# Sidebar Inputs
accounts = st.sidebar.text_input('Accounts (comma-separated)', value='Account A,Account B')
account_list = [a.strip() for a in accounts.split(',') if a.strip()]
selected_account = st.sidebar.selectbox('Select Account', account_list)

st.sidebar.markdown('---')
st.sidebar.header('Add New Entry')
entry_dt = st.sidebar.date_input('Date', value=date.today())
entry_pl = st.sidebar.number_input('P/L', format='%f', step=0.1)
if st.sidebar.button('Add Entry'):
    try:
        add_entry(entry_dt.isoformat(), selected_account, entry_pl)
        st.sidebar.success(f"✅ Logged {entry_pl:+.2f} for {selected_account}")
        st.experimental_rerun()
    except Exception as e:
        st.sidebar.error(f"Error logging entry: {e}")

# Main Display
st.header('Historical P/L Data')
entries = load_entries()
if not entries.empty:
    # Filter by account
    filtered = entries[entries['account'] == selected_account].copy()
    filtered.sort_values('entry_date', inplace=True)
    filtered.reset_index(drop=True, inplace=True)

    # Metrics
    total_pl = filtered['pl'].sum()
    st.metric('Total P/L', f'{total_pl:+.2f}')

    # Data Table
    st.dataframe(filtered[['entry_date', 'pl']], use_container_width=True)

    # Time Series Chart
    st.line_chart(data=filtered.set_index('entry_date')['pl'].cumsum(), width=0)
else:
    st.info('No entries yet. Add an entry from the sidebar.')
