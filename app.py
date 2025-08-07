import os, sqlite3, json
from datetime import date
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DB_FILE = 'trading_tracker.db'
SETTINGS_FILE = 'settings.json'
DEFAULT_ACCOUNTS = ['Account A', 'Account B']

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        'CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_date TEXT NOT NULL, account TEXT NOT NULL, pl REAL NOT NULL)'
    )
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def load_entries():
    conn = get_conn()
    df = pd.read_sql('SELECT * FROM entries', conn, parse_dates=['entry_date'])
    conn.close()
    return df

def add_entry(entry_date, account, pl):
    conn = get_conn()
    conn.execute(
        'INSERT INTO entries (entry_date, account, pl) VALUES (?, ?, ?)',
        (entry_date, account, pl)
    )
    conn.commit()
    conn.close()

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

init_db()
settings = load_settings()
accounts = settings.get('accounts', DEFAULT_ACCOUNTS)
for acct in accounts:
    settings.setdefault(f'start_balance_{acct}', 1000.0)
    settings.setdefault(f'profit_target_{acct}', 2000.0)
save_settings(settings)
df_all = load_entries()

st.sidebar.header('Account Entry')
acct = st.sidebar.selectbox('Account', accounts)
entry_date = st.sidebar.date_input('Date', value=date.today())
daily_pl = st.sidebar.number_input("Today's P/L", format='%.2f', step=0.01)
start_bal = st.sidebar.number_input('Starting Balance', value=settings[f'start_balance_{acct}'], step=100.0, format='%.2f')
profit_tgt = st.sidebar.number_input('Profit Target', value=settings[f'profit_target_{acct}'], step=100.0, format='%.2f')
if st.sidebar.button('Add Entry'):
    add_entry(entry_date.isoformat(), acct, daily_pl)
    df_all = load_entries()
    settings[f'start_balance_{acct}'] = start_bal
    settings[f'profit_target_{acct}'] = profit_tgt
    save_settings(settings)
    st.sidebar.success(f'Logged {daily_pl:+.2f}')

today = date.today()
df_today = df_all[(df_all['account']==acct) & (df_all['entry_date'].dt.date==today)]
st.sidebar.metric("Today's P/L", f"{df_today['pl'].sum():+.2f}")

st.header('Trading Tracker')
tabs = st.tabs(accounts)
for a in accounts:
    with tabs[accounts.index(a)]:
        df_acc = df_all[df_all['account']==a].copy()
        df_acc['entry_date'] = pd.to_datetime(df_acc['entry_date'])
        df_acc.sort_values('entry_date', inplace=True)
        sb = settings[f'start_balance_{a}']
        pt = settings[f'profit_target_{a}']
        df_acc['Balance'] = df_acc['pl'].cumsum() + sb
        curr = df_acc['Balance'].iloc[-1] if not df_acc.empty else sb
        pct = curr/pt*100 if pt else 0
        col1, col2 = st.columns(2)
        col1.metric('Start Balance', f'${sb:,.2f}')
        col2.metric('Current Balance', f'${curr:,.2f}', delta=f'{pct:.1f}%')
        progress = min(pct, 100)
        st.markdown(f"""
<style>
@keyframes neonPulse {{
    0% {{ box-shadow: 0 0 5px #0ff; }}
    50% {{ box-shadow: 0 0 20px #0ff; }}
    100% {{ box-shadow: 0 0 5px #0ff; }}
}}
.bar {{
    width: {progress:.1f}%;
    height: 20px;
    background: linear-gradient(90deg, #39FF14, #0ff);
    border-radius: 10px;
    animation: neonPulse 1.2s infinite ease-in-out;
    transition: width 0.5s ease;
}}
.container {{
    width: 100%;
    background: #111;
    border: 2px solid #39FF1422;
    border-radius: 10px;
    overflow: hidden;
    margin: 10px 0;
}}
.label {{
    color: #0ff;
    text-shadow: 0 0 5px #0ff, 0 0 10px #0ff, 0 0 20px #0ff;
    font-weight: bold;
    font-size: 1.1em;
    margin-top: 5px;
}}
</style>
<div class='container'><div class='bar'></div></div>
<div class='label'>{progress:.1f}%</div>
""", unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(8,4), facecolor='#222')
        ax.set_facecolor('#333')
        if not df_acc.empty:
            ax.plot(df_acc['entry_date'], df_acc['Balance'], linewidth=2)
            ax.fill_between(df_acc['entry_date'], df_acc['Balance'], alpha=0.2)
        ax.tick_params(colors='#0ff')
        for spine in ax.spines.values():
            spine.set_color('#0ff')
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
