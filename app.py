# (inside the tab loop for each account)
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
    gain = df_acc.iloc[-1]["Daily P/L"]
    prog = min(curr / pt if pt else 0, 1.0)
    pct_gain = (curr - sb) / sb * 100

    # Metrics (streak removed)
    cols = st.columns(2)
    cols[0].metric("Start", f"${sb:,.2f}")
    cols[1].metric("Current", f"${curr:,.2f}", delta=f"{pct_gain:+.2f}%")

    # Smart Suggestions
    if gain > 0:
        st.success("📈 Great! You're in profit today. Keep up the momentum!")
    elif gain < 0:
        st.warning("📉 Loss today. Review what went wrong.")
    else:
        st.info("🧘‍♂️ Neutral day. Stay consistent.")

    # Milestone celebration
    if prog >= 1:
        st.balloons()
        st.success("🎉 Profit target reached!")

    # Progress Bar
    st.subheader("Progress to Target")
    st.markdown(f"""
    <style>
    @keyframes neon {{ 0% {{box-shadow: 0 0 5px #87CEFA;}} 50% {{box-shadow: 0 0 20px #87CEFA;}} 100% {{box-shadow: 0 0 5px #87CEFA;}} }}
    .neon-bar {{ background: #87CEFA; height: 25px; width: {prog * 100:.1f}%; border-radius: 12px; animation: neon 2s infinite; }}
    .bar-container {{ background: #222; border-radius: 12px; overflow: hidden; }}
    </style>
    <div class="bar-container"><div class="neon-bar"></div></div>
    """, unsafe_allow_html=True)
    st.write(f"{prog*100:.1f}% to target")

    # Date range filter
    if len(df_acc) > 1:
        start, end = st.date_input("Date Range", [df_acc["Date"].min(), df_acc["Date"].max()], key=f"range_{acct}")
        df_acc = df_acc[(df_acc['Date'] >= pd.to_datetime(start)) & (df_acc['Date'] <= pd.to_datetime(end))]

    # Plot
    st.subheader("Balance Over Time")
    fig, ax = plt.subplots(figsize=(8, 4), facecolor='#222')
    ax.set_facecolor('#333')
    ax.plot(df_acc['Date'], df_acc['Balance'], color='#00FFFF', linewidth=2.5)
    ax.fill_between(df_acc['Date'], df_acc['Balance'], color='#00FFFF', alpha=0.2)
    ax.set(title='Balance Progress', xlabel='Date', ylabel='Balance ($)')
    ax.tick_params(colors='#39FF14')
    for spine in ax.spines.values():
        spine.set_color('#39FF14')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    fig.autofmt_xdate()
    ax.grid(False)
    st.pyplot(fig, use_container_width=True)

    # Table
    st.subheader("Entries")
    st.dataframe(
        df_acc.style
        .format({'Date': '{:%Y-%m-%d}', 'Daily P/L': '{:+.2f}', 'Balance': '{:,.2f}'})
        .applymap(
            lambda v: 'color:#39FF14' if isinstance(v, (int, float)) and v >= 0 else 'color:#FF0055',
            subset=['Daily P/L']
        ),
        use_container_width=True
    )
