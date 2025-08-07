import os
import sqlite3
import json
from datetime import date
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ---------------------
# Constants & Files   
# ---------------------
DB_FILE = 'trading_tracker.db'
SETTINGS_FILE = 'settings.json'
DEFAULT_ACCOUNTS = ['Account A', 'Account B']

# ---------------------
# Database Utilities  
# ---------------------
def initialize_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            account TEXT NOT NULL,
            pl REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def load_entries() -> pd.DataFrame:
    conn = get_db_connection()
    df = pd.read_sql('SELECT * FROM entries', conn, parse_dates=['entry_date'])
    conn.close()
    return df

def add_entry(entry_date: str, account: str, pl: float):
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO entries (entry_date, account, pl) VALUES (?, ?, ?)',
            (entry_date, account, pl)
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        st.sidebar.error(f"Database error: {e}")
    finally:
        conn.close()

# ---------------------
# Settings Utilities  
# ---------------------

def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}


def save_settings(settings: dict):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

# ---------------------
# App Initialization  
# ---------------------
initialize_db()
st.set_page_config(page_title='Tracker', page_icon='💰', layout='wide')
settings = load_settings()
accounts = settings.get('accounts', DEFAULT_ACCOUNTS)

# Ensure session_state has profit_target defaults
for acct in accounts:
    settings.setdefault(f'profit_target_{acct}', 2000.0)
    # initialize session state for profit targets
    st.session_state.setdefault(f'profit_target_{acct}', settings[f'profit_target_{acct}'])
save_settings(settings)

df_all = load_entries()

# ---------------------
# Sidebar             
# ---------------------
with st.sidebar:
    st.header('📋 Account Entry')
    selected_account = st.selectbox('Account', accounts, index=0)

    # Date and P/L inputs
    entry_date = st.date_input('Date', value=date.today())
    daily_pl = st.number_input("Today's P/L", format='%.2f', step=0.01)

    # Balance & Profit Target inputs
    start_bal = st.number_input('Starting Balance', value=settings.get(f'start_balance_{selected_account}', 1000.0), step=100.0, format='%.2f')
    profit_tgt = st.number_input('Profit Target', value=st.session_state[f'profit_target_{selected_account}'], step=100.0, format='%.2f')
    # Update both session_state and settings for live tracking
    st.session_state[f'profit_target_{selected_account}'] = profit_tgt
    settings[f'start_balance_{selected_account}'] = start_bal
    settings[f'profit_target_{selected_account}'] = profit_tgt
    save_settings(settings)

    if st.button('➕ Add Entry'):
        add_entry(entry_date.isoformat(), selected_account, daily_pl)
                st.success(f"✅ Account '{selected_account}' data reset to zero.")
