import os
import sqlite3
import json
from datetime import date
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DB_FILE = 'trading_tracker.db'
SETTINGS_FILE = 'settings.json'
DEFAULT_ACCOUNTS = ['Account A', 'Account B']

print("Starting Trading Tracker App")

def initialize_db():
    print("Initializing database...")
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
    print("Database initialized")


def get_db_connection():
    print(f"Opening DB connection to {DB_FILE}")
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def load_entries():
    print("Loading entries from DB...")
    conn = get_db_connection()
    df = pd.read_sql('SELECT * FROM entries', conn, parse_dates=['entry_date'])
    conn.close()
    print(f"Loaded {len(df)} entries")
    return df


def add_entry(entry_date, account, pl):
    print(f"Adding entry: date={entry_date}, account={account}, pl={pl}")
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO entries (entry_date, account, pl) VALUES (?, ?, ?)',
        (entry_date, account, pl)
    )
    conn.commit()
    conn.close()
    print("Entry added successfully")


def load_settings():
    print("Loading settings...")
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                print(f"Settings loaded: {settings}")
                return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
            return {}
    print("Settings file not found, using defaults")
    return {}


def save_settings(settings):
    print(f"Saving settings: {settings}")
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
    print("Settings saved")

initialize_db()
settings = load_settings()
accounts = settings.get('accounts', DEFAULT_ACCOUNTS)

for acct in accounts:
    settings.setdefault(f'start_balance_{acct}', 1000.0)
    settings.setdefault(f'profit_target_{acct}', 2000.0)
    settings.setdefault(f'last_date_{acct}', str(date.today()))
    settings.setdefault(f'daily_pl_{acct}', 0.0)
    st.session_state.setdefault(f'profit_target_{acct}', settings[f'profit_target_{acct}'])
save_settings(settings)
print(f"Final accounts list: {accounts}")

df_all = load_entries()
print("Entries dataframe prepared")

with st.sidebar:
    st.header('📋 Account Entry')
    selected_account = st.selectbox('Account', accounts)
    print(f"Selected account: {selected_account}")
    entry_date = st.date_input('Date', value=date.today())
    daily_pl = st.number_input("Today's P/L", format='%.2f', step=0.01)
    start_bal = st.number_input('Starting Balance', value=settings.get(f'start_balance_{selected_account}', 1000.0), step=100.0, format='%.2f')
    profit_tgt = st.number_input('Profit Target', value=st.session_state[f'profit_target_{selected_account}'], step=100.0, format='%.2f')
    st.session_state[f'profit_target_{selected_account}'] = profit_tgt
    settings[f'start_balance_{selected_account}'] = start_bal
    settings[f'profit_target_{selected_account}'] = profit_tgt
    save_settings(settings)
    if st.button('➕ Add Entry'):
        print("Add Entry button clicked")
        add_entry(entry_date.isoformat(), selected_account, daily_pl)
        df_all = load_entries()
        st.success(f'✅ Logged {daily_pl:+.2f} for {selected_account}')
    today = date.today()
    df_today = df_all[(df_all['account']==selected_account) & (df_all['entry_date'].dt.date==today)]
    st.metric("Today's P/L", f"{df_today['pl'].sum():+.2f}")
    if st.button('🔴 RESET'):
        print("RESET button clicked")
        conn = get_db_connection()
        conn.execute('DELETE FROM entries WHERE account = ?', (selected_account,))
        conn.commit()
        conn.close()
        settings[f'start_balance_{selected_account}'] = 0.0
        settings[f'profit_target_{selected_account}'] = 0.0
        st.session_state[f'profit_target_{selected_account}'] = 0.0
        save_settings(settings)
        df_all = load_entries()
        st.success(f"✅ Account '{selected_account}' data reset to zero.")

st.header('📊 Trading Tracker')
tabs = st.tabs(accounts)
for acct in accounts:
    with tabs[accounts.index(acct)]:
        df_acc = df_all[df_all['account']==acct].copy()
        df_acc.sort_values('entry_date', inplace=True)
        if df_acc.empty:
            df_acc = pd.DataFrame([{'entry_date':pd.to_datetime(date.today()), 'account':acct, 'pl':0.0, 'id':0}])
        sb = settings.get(f'start_balance_{acct}', 1000.0)
        pt = st.session_state[f'profit_target_{acct}']
        df_acc['Balance'] = df_acc['pl'].cumsum() + sb
        curr_bal = df_acc.iloc[-1]['Balance']
        pct_to_tgt = (curr_bal / pt) * 100 if pt else 0
        col1, col2 = st.columns(2)
        col1.metric('Start Balance', f'${sb:,.2f}')
        col2.metric('Current Balance', f'${curr_bal:,.2f}', delta=f'{pct_to_tgt:.2f}%')
        progress = min(curr_bal / pt, 1.0) if pt else 0
        st.markdown(f"""
<style>
@keyframes neonPulse {
    0% { box-shadow: 0 0 5px #0ff; }
    50% { box-shadow: 0 0 20px #0ff; }
    100% { box-shadow: 0 0 5px #0ff; }
}
@keyframes growBar {
    0% { width: 0%; }
    100% { width: " + "{progress*100:.1f}%" + "; }
}
.bar {
    width: 0%;
    height: 20px;
    background: linear-gradient(90deg, #39FF14, #0ff);
    border-radius: 10px;
    animation: growBar 1s forwards ease-out, neonPulse 1.2s infinite ease-in-out;
}
.container {
    width: 100%;
    background: #111;
    border: 2px solid #39FF1422;
    border-radius: 10px;
    overflow: hidden;
    margin: 10px 0;
}
.label {
    color: #0ff;
    text-shadow: 0 0 5px #0ff, 0 0 10px #0ff, 0 0 20px #0ff;
    font-weight: bold;
    font-size: 1.1em;
    margin-top: 5px;
}
</style>
<div class='container'><div class='bar'></div></div>
<div class='label'>{progress*100:.1f}%</div>
""", unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(8,4), facecolor='#222')
        ax.set_facecolor('#333')
        ax.plot(df_acc['entry_date'], df_acc['Balance'], linewidth=2)
        ax.fill_between(df_acc['entry_date'], df_acc['Balance'], alpha=0.2)
        ax.tick_params(colors='#0ff')
        for spine in ax.spines.values(): spine.set_color('#0ff')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.grid(False)
        st.pyplot(fig, use_container_width=True)
        styled = (
            df_acc[['entry_date','pl','Balance']]
            .rename(columns={'entry_date':'Date','pl':'P/L'})
            .style
            .format({'P/L': '{:+.2f}','Balance':'{:.2f}'})
            .applymap(lambda v: 'color:#39FF14' if isinstance(v, (int,float)) and v>0 else ('color:#FF0055' if isinstance(v,(int,float)) and v<0 else ''), subset=['P/L'])
        )
        st.dataframe(styled, use_container_width=True)
