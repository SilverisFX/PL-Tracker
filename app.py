# ─── Tabs for Account Comparison ──────────────────────────
tabs = st.tabs([f"📊 {acct}" for acct in ACCOUNTS])
for i, acct in enumerate(ACCOUNTS):
    with tabs[i]:
        st.markdown(f"## Tracker: {acct}")
        df_acc = df_all[df_all["Account"] == acct].copy().sort_values("Date")
        sb = settings[f"start_balance_{acct}"]
        pt = settings[f"profit_target_{acct}"]

        if df_acc.empty:
            df_acc = pd.DataFrame([{
                "Account": acct,
                "Date": pd.to_datetime(date.today()),
                "Daily P/L": 0.0
            }])

        df_acc["Balance"] = df_acc["Daily P/L"].cumsum() + sb
        curr = df_acc.iloc[-1]["Balance"]

        # Calculate today's P/L for this account
        today = date.today()
        mask_today = df_acc["Date"].dt.date == today
        today_pl_tab = df_acc.loc[mask_today, "Daily P/L"].sum()

        # Display Start, Current, and Today P/L as three separate metrics
        cols = st.columns(3)
        cols[0].metric("Start", f"${sb:,.2f}")
        cols[1].metric("Current", f"${curr:,.2f}")
        cols[2].metric("Today P/L", f"{today_pl_tab:+.2f}")

        # --- Neon Progress Bar ---
        prog = min(curr / pt if pt else 0, 1.0)
        st.markdown(f"""
            <style>
            @keyframes neon {{
                0% {{ box-shadow: 0 0 10px #00eaff; }}
                50% {{ box-shadow: 0 0 35px #00eaff; }}
                100% {{ box-shadow: 0 0 10px #00eaff; }}
            }}
            .neon-bar {{
                background: linear-gradient(90deg, #00eaff, #0af);
                height: 25px;
                width: {prog*100:.1f}%;
                border-radius: 12px;
                animation: neon 1.4s infinite;
                transition: width 0.6s;
            }}
            .bar-container {{
                background: #181c24;
                border-radius: 12px;
                overflow: hidden;
                margin-bottom: 12px;
                border: 2px solid #00eaff22;
            }}
            </style>
            <div class="bar-container"><div class="neon-bar"></div></div>
        """, unsafe_allow_html=True)
        st.write(f"<b>{prog*100:.1f}% to target</b>", unsafe_allow_html=True)

        # … rest of your tab content (alerts, chart, entries) …
