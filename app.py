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
    # Ensure DB and table exist
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

# Initialize per-account defaults
for acct in accounts:
    settings.setdefault(f'start_balance_{acct}', 1000.0)
    settings.setdefault(f'profit_target_{acct}', 2000.0)
    settings.setdefault(f'last_date_{acct}', str(date.today()))
    settings.setdefault(f'daily_pl_{acct}', 0.0)
    st.session_state.setdefault(f'daily_pl_{acct}', settings[f'daily_pl_{acct}'])
    st.session_state.setdefault(f'last_date_{acct}', settings[f'last_date_{acct}'])
save_settings(settings)

# Load data
df_all = load_entries()

# ---------------------
# Sidebar             
# ---------------------
with st.sidebar:
    st.header('📋 Account Entry')
    selected_account = st.selectbox('Account', accounts, index=0)

    entry_date = st.date_input('Date', value=pd.to_datetime(settings.get(f'last_date_{selected_account}', date.today())))
    daily_pl = st.number_input("Today's P/L", key=f'daily_pl_{selected_account}', format='%.2f', step=0.01)

    # Update settings
    settings[f'last_date_{selected_account}'] = str(entry_date)
    settings[f'daily_pl_{selected_account}'] = daily_pl

    start_bal = st.number_input('Starting Balance', value=settings[f'start_balance_{selected_account}'], step=100.0, format='%.2f')
    profit_tgt = st.number_input('Profit Target', value=settings[f'profit_target_{selected_account}'], step=100.0, format='%.2f')
    settings[f'start_balance_{selected_account}'] = start_bal
    settings[f'profit_target_{selected_account}'] = profit_tgt
    save_settings(settings)

    if st.button('➕ Add Entry'):
        add_entry(entry_date.isoformat(), selected_account, daily_pl)
        st.success(f'✅ Logged {daily_pl:+.2f} for {selected_account}')
        df_all = load_entries()

    # Today's metric
    today = date.today()
    df_today = df_all[(df_all['account']==selected_account) & (df_all['entry_date'].dt.date==today)]
    today_sum = df_today['pl'].sum()
    st.metric("🗖 Today's P/L", f"{today_sum:+.2f}")

# ---------------------
# Main: Tabs per Account
# ---------------------
st.header('📊 Trading Tracker')
tabs = st.tabs([f"{acct}" for acct in accounts])
for idx, acct in enumerate(accounts):
    with tabs[idx]:
        df_acc = df_all[df_all['account']==acct].copy()
        df_acc.sort_values('entry_date', inplace=True)
        if df_acc.empty:
            df_acc = pd.DataFrame([{'id':0,'entry_date':pd.to_datetime(date.today()),'account':acct,'pl':0.0}])

        # Compute balances
        sb = settings[f'start_balance_{acct}']
        pt = settings[f'profit_target_{acct}']
        df_acc['Balance'] = df_acc['pl'].cumsum() + sb
        curr_bal = df_acc.iloc[-1]['Balance']
        pct_to_tgt = (curr_bal/sb)*100 if sb else 0

        col1, col2 = st.columns(2)
        col1.metric('Start Balance', f'${sb:,.2f}')
        col2.metric('Current Balance', f'${curr_bal:,.2f}', delta=f'{pct_to_tgt - 100:+.2f}%')

                # Neon Progress Bar
        progress = min(curr_bal/pt if pt else 0, 1.0)
        st.markdown(f"""
        <style>
        @keyframes neonGlow {{
            0% {{ box-shadow: 0 0 5px #39FF14; }}
            100% {{ box-shadow: 0 0 20px #39FF14; }}
        }}
        .neon {{
            background: linear-gradient(90deg, #39FF14, #0ff);
            height: 20px;
            width: {progress*100:.1f}%;
            border-radius: 10px;
            animation: neonGlow 1.4s infinite alternate;
            transition: width 0.6s ease-in-out;
        }}
        .container {{
            background: #111;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
            border: 2px solid #39FF1422;
        }}
        </style>
        <div class='container'><div class='neon'></div></div>
        {progress*100:.1f}% to target
        """, unsafe_allow_html=True)

        # Plot Balance Curve
        fig, ax = plt.subplots(figsize=(8,4), facecolor='#222')
        ax.set_facecolor('#333')
        ax.plot(df_acc['entry_date'], df_acc['Balance'], linewidth=2)
        ax.fill_between(df_acc['entry_date'], df_acc['Balance'], alpha=0.2)
        ax.tick_params(colors='#0ff')
        for spine in ax.spines.values(): spine.set_color('#0ff')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.grid(False)
        st.pyplot(fig, use_container_width=True)

                # Data Table
        st.subheader('Entries')
        styled_df = (
            df_acc[['entry_date','pl','Balance']]
                .rename(columns={'entry_date':'Date','pl':'P/L'})
                .style
                .format({'P/L': '{:+.2f}','Balance':'{:.2f}'})
                .applymap(lambda v: 'color: #39FF14' if isinstance(v, (int, float)) and v > 0 else ('color: #FF0055' if isinstance(v, (int, float)) and v < 0 else ''), subset=['P/L'])
        )
        st.dataframe(styled_df, use_container_width=True)
