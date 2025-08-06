tabs = st.tabs([f"📊 {acct}" for acct in ACCOUNTS])
for i, acct in enumerate(ACCOUNTS):
    with tabs[i]:
        st.markdown(f"## Tracker: {acct}")
        mask = df_all["Account"] == acct
        df_acc = df_all[mask].copy().sort_values("Date")
        sb = settings[f"start_balance_{acct}"]
        pt = settings[f"profit_target_{acct}"]

        if df_acc.empty:
            df_acc = pd.DataFrame([{"Account": acct, "Date": pd.to_datetime(date.today()), "Daily P/L": 0.0}])

        df_acc["Balance"] = df_acc["Daily P/L"].cumsum() + sb
        curr = df_acc.iloc[-1]["Balance"]

        # Recalculate today's P/L directly
        today = date.today()
        daily_df = df_acc[df_acc["Date"].dt.date == today]
        gain = daily_df["Daily P/L"].sum()

        cols = st.columns(2)
        cols[0].metric("Start", f"${sb:,.2f}")
        cols[1].metric("Current", f"${curr:,.2f}")

        if gain > 0:
            st.success("📈 Great! You're in profit today. Keep up the momentum!")
        elif gain < 0:
            st.warning("📉 Loss today. Review what went wrong.")
        else:
            st.info("🧘‍♂️ Neutral day. Stay consistent.")

        # —— Progress-to-Target removed —— #

        st.subheader("Balance Over Time")
        fig, ax = plt.subplots(figsize=(8, 4), facecolor='#222')
        fig.patch.set_facecolor('#222')
        ax.plot(df_acc["Date"], df_acc["Balance"], color='lime', linewidth=2)
        ax.set_facecolor('#111')
        ax.grid(False)
        ax.tick_params(colors='lightgrey')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        fig.autofmt_xdate()
        ax.set_ylabel("Balance", color='lightgrey')
        ax.set_title("Balance Over Time", color='lightgrey')
        st.pyplot(fig)
