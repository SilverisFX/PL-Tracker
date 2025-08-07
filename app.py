# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px

# ─── Config ────────────────────────────────
st.set_page_config(
    page_title="My Custom Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Sidebar Filters ────────────────────────
st.sidebar.header("Filters")
start_date = st.sidebar.date_input("Start date")
end_date   = st.sidebar.date_input("End date")
symbols    = st.sidebar.multiselect("Symbols", options=["EURUSD","USDJPY","GBPUSD"], default=["EURUSD"])

# ─── Data Loading ───────────────────────────
@st.cache_data
def load_data():
    # replace with your real data source!
    df = pd.read_csv("trades.csv", parse_dates=["date"])
    return df

df = load_data()
df = df[(df.date >= pd.to_datetime(start_date)) & (df.date <= pd.to_datetime(end_date))]
df = df[df.symbol.isin(symbols)]

# ─── Top-Level Metrics ───────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total P/L", f"${df['pl'].sum():.2f}")
col2.metric("Avg. Trade", f"${df['pl'].mean():.2f}")
col3.metric("Win Rate", f"{(df.pl>0).mean()*100:.1f}%")
col4.metric("Trades", len(df))

# ─── Time Series Chart ──────────────────────
st.subheader("P/L Over Time")
ts = df.groupby("date")["pl"].sum().cumsum().reset_index()
fig = px.line(ts, x="date", y="pl", title=None)
fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# ─── Detailed Table ─────────────────────────
st.subheader("Trade Details")
st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)
