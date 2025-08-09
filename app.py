# app.py
import os, json, time
from datetime import datetime, date
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ----------------------------
# Basic setup
# ----------------------------
st.set_page_config(page_title="Forex P/L Tracker", page_icon="💹", layout="wide")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
CSV_FILE = os.path.join(DATA_DIR, "tracker.csv")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

DEFAULT_ACCOUNTS = ["Account A", "Account B"]

# ----------------------------
# Backup + Persistence Helpers
# ----------------------------
def backup_file(path: str):
    if os.path.exists(path):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base = os.path.basename(path)
        bpath = os.path.join(BACKUP_DIR, f"{base}.{ts}.bak")
        with open(path, "rb") as src, open(bpath, "wb") as dst:
            dst.write(src.read())

def _restore_json_from_backups(prefix: str) -> dict:
    for name in sorted([n for n in os.listdir(BACKUP_DIR) if n.startswith(prefix)], reverse=True):
        try:
            return json.load(open(os.path.join(BACKUP_DIR, name), "r"))
        except Exception:
            continue
    return {}

def _restore_csv_from_backups(prefix: str) -> pd.DataFrame:
    for name in sorted([n for n in os.listdir(BACKUP_DIR) if n.startswith(prefix)], reverse=True):
        try:
            return pd.read_csv(os.path.join(BACKUP_DIR, name))
        except Exception:
            continue
    return pd.DataFrame(columns=["Date", "Account", "PL"])

def load_settings() -> dict:
    try:
        if os.path.exists(SETTINGS_FILE):
            return json.load(open(SETTINGS_FILE, "r"))
    except Exception:
        st.warning("Settings corrupted; restoring backup…")
        return _restore_json_from_backups("settings.json")
    return {}

def save_settings(settings: dict):
    backup_file(SETTINGS_FILE)
    json.dump(settings, open(SETTINGS_FILE, "w"), indent=2)

def load_df() -> pd.DataFrame:
    try:
        if os.path.exists(CSV_FILE):
            return pd.read_csv(CSV_FILE)
    except Exception:
        st.warning("Data corrupted; restoring backup…")
        return _restore_csv_from_backups("tracker.csv")
    return pd.DataFrame(columns=["Date", "Account", "PL"])

def save_df(df: pd.DataFrame):
    backup_file(CSV_FILE)
    df.to_csv(CSV_FILE, index=False)

# ----------------------------
# Init Data
# ----------------------------
df_all = load_df()
if df_all.empty:
    df_all = pd.DataFrame(columns=["Date", "Account", "PL"])

settings = load_settings()
if "accounts" not in settings:
    settings["accounts"] = DEFAULT_ACCOUNTS

if "account_cfg" not in settings:
    settings["account_cfg"] = {
        acc: {"starting_balance": 1000.0, "target_balance": 2000.0}
        for acc in settings["accounts"]
    }
    save_settings(settings)

# ----------------------------
# Sidebar
# ----------------------------
st.sidebar.title("⚙️ Settings")

# Account management
with st.sidebar.expander("Accounts", expanded=True):
    selected_account = st.selectbox("Select account", settings["accounts"])
    new_acc = st.text_input("Add account")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("➕ Add", use_container_width=True) and new_acc.strip():
            if new_acc not in settings["accounts"]:
                settings["accounts"].append(new_acc)
                settings["account_cfg"][new_acc] = {"starting_balance": 1000.0, "target_balance": 2000.0}
                save_settings(settings)
                st.success(f"Added account '{new_acc}'")
                st.rerun()
    with c2:
        if st.button("Remove", use_container_width=True, help="Remove current account"):
            if selected_account in settings["accounts"]:
                settings["accounts"].remove(selected_account)
                settings["account_cfg"].pop(selected_account, None)
                save_settings(settings)
                st.warning(f"Removed account '{selected_account}' from list (data rows remain).")
                st.rerun()

# Account targets
cfg = settings["account_cfg"].get(selected_account, {"starting_balance": 1000.0, "target_balance": 2000.0})
sb = float(st.sidebar.number_input("Starting Balance ($)", value=float(cfg["starting_balance"]), step=100.0))
tb = float(st.sidebar.number_input("Target Balance ($)", value=float(cfg["target_balance"]), step=100.0))
if tb <= sb:
    st.sidebar.error("Target Balance must be greater than Starting Balance.")

# Save emoji-only
if st.sidebar.button("💾", use_container_width=True):
    settings["account_cfg"][selected_account] = {"starting_balance": sb, "target_balance": tb}
    save_settings(settings)
    st.sidebar.success("Saved")

# Add entry in sidebar
st.sidebar.subheader("🧾 Add Entry")
entry_date = st.sidebar.date_input("Date", value=date.today(), key="sidebar_date")
pl_value = st.sidebar.number_input("P/L Amount ($)", value=0.00, step=10.0, format="%.2f", key="sidebar_pl")

if st.sidebar.button("Add", use_container_width=True):
    df_all = pd.concat([df_all, pd.DataFrame({
        "Date": [pd.to_datetime(entry_date).strftime("%Y-%m-%d")],
        "Account": [selected_account],
        "PL": [float(pl_value)]
    })], ignore_index=True)
    save_df(df_all)
    st.sidebar.success(f"Added {pl_value:+,.0f} for {selected_account}")
    st.rerun()

if st.sidebar.button("↩️ Undo Last Entry", use_container_width=True):
    mask = df_all["Account"] == selected_account
    idx = df_all[mask].tail(1).index
    if len(idx):
        df_all = df_all.drop(idx)
        save_df(df_all)
        st.sidebar.info("Last entry removed.")
        st.rerun()
    else:
        st.sidebar.warning("No entries to undo for this account.")

# Export / Import
st.sidebar.markdown("### 🛟 Data Safety")
col_exp, col_imp = st.sidebar.columns(2)
with col_exp:
    if os.path.exists(CSV_FILE):
        st.download_button("Export CSV", data=open(CSV_FILE, "rb").read(),
                           file_name="tracker_export.csv", mime="text/csv")
with col_imp:
    up = st.file_uploader("Import CSV", type=["csv"], label_visibility="collapsed")
    if up is not None:
        try:
            df_new = pd.read_csv(up)
            required = {"Date", "Account", "PL"}
            if not required.issubset(df_new.columns):
                raise ValueError("CSV must have columns: Date, Account, PL")
            save_df(df_new)
            st.sidebar.success("Imported & saved. Reloading…")
            time.sleep(0.6)
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Import failed: {e}")

# Reset account
st.sidebar.divider()
confirm_reset = st.sidebar.checkbox("I understand this deletes this account's rows")
if st.sidebar.button("🧨 RESET", use_container_width=True):
    if confirm_reset:
        before = len(df_all)
        df_all = df_all[df_all["Account"] != selected_account]
        save_df(df_all)
        st.sidebar.success(f"Deleted {before - len(df_all)} rows for {selected_account}.")
        st.rerun()
    else:
        st.sidebar.warning("Check the confirmation box first.")

# ----------------------------
# Compute metrics
# ----------------------------
df_acc = df_all[df_all["Account"] == selected_account].copy()
if not df_acc.empty:
    df_acc["Date"] = pd.to_datetime(df_acc["Date"], errors="coerce")
    df_acc = df_acc.dropna(subset=["Date"]).sort_values("Date")
else:
    df_acc = pd.DataFrame(columns=["Date", "Account", "PL"])

cum_profit = float(df_acc["PL"].sum()) if not df_acc.empty else 0.0
current_balance = sb + cum_profit
target_profit = max(tb - sb, 1e-9)
pct_to_target = float(np.clip((current_balance - sb) / target_profit * 100.0, 0.0, 100.0))

# ----------------------------
# Main Page
# ----------------------------
st.title("💹 Forex Profit & Loss Tracker")

st.subheader("Overview")
m1, m2 = st.columns(2)
m1.metric("Current Balance", f"${current_balance:,.0f}")
m2.metric("To Target", f"{pct_to_target:.2f}%")

# Progress bar (fixed f-string)
st.markdown(
    f"""
    <style>
    .progress-wrap {{
        background: #0b0b0b;
        border: 1px solid #0ff5;
        border-radius: 10px;
        padding: 10px;
        margin-top: 10px;
    }}
    .progress-bar {{
        height: 16px;
        width: {pct_to_target}%;
        max-width: 100%;
        border-radius: 8px;
        box-shadow: 0 0 8px #0ff, inset 0 0 6px #0ff4;
        animation: glow 2s ease-in-out infinite alternate;
        background: linear-gradient(90deg, rgba(0,255,255,0.25), rgba(0,255,255,0.9));
    }}
    @keyframes glow {{
        0% {{ box-shadow: 0 0 4px #0ff, inset 0 0 4px #0ff3; }}
        100% {{ box-shadow: 0 0 12px #0ff, inset 0 0 10px #0ff6; }}
    }}
    .progress-label {{
        color: #8ef;
        font-weight: 600;
        margin-bottom: 6px;
        text-shadow: 0 0 8px #0ff5;
    }}
    </style>
    <div class="progress-wrap">
        <div class="progress-label">Progress to Target: {pct_to_target:.2f}%</div>
        <div class="progress-bar"></div>
    </div>
    """,
    unsafe_allow_html=True
)

# Chart
st.markdown("#### Equity Progress (Cumulative P/L)")
fig, ax = plt.subplots(figsize=(8, 4))
fig.patch.set_facecolor("#111111")
ax.set_facecolor("#111111")
if not df_acc.empty:
    df_acc["CumPL"] = df_acc["PL"].cumsum()
    ax.plot(df_acc["Date"], df_acc["CumPL"])
    ax.axhline(y=target_profit, linestyle="--")
    ax.axhline(y=0, linewidth=0.8)
ax.grid(False)
ax.tick_params(colors="#b0b0b0")
for spine in ax.spines.values():
    spine.set_color("#333333")
ax.set_xlabel("Date", color="#b0b0b0")
ax.set_ylabel("Cumulative P/L ($)", color="#b0b0b0")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
st.pyplot(fig, use_container_width=True)

# Table
st.markdown("#### Entries")
df_display = df_all.copy()
if not df_display.empty:
    df_display["PL"] = df_display["PL"].apply(lambda x: f"{x:,.0f}")
st.dataframe(
    df_display.sort_values(["Account", "Date"]).reset_index(drop=True),
    use_container_width=True
)
