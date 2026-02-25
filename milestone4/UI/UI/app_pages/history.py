from __future__ import annotations
import streamlit as st
from services.history_excel import load_history

def history_page():
    st.markdown("<h2>History</h2>", unsafe_allow_html=True)
    st.caption("Your past contract analyses.")

    user = st.session_state.get("user") or {}
    user_email = (user.get("email") or "").strip().lower()

    if not user_email:
        st.warning("Please login to view your history.")
        return

    # Load history from Excel
    try:
        history_df = load_history(user_email)
    except Exception as e:
        st.error("Failed to load history.")
        st.exception(e)
        return

    if history_df.empty:
        st.info("No analysis history yet.")
        return

    # Display history entries
    for idx, row in history_df.iterrows():
        timestamp = str(row.get("timestamp", ""))[:19]
        filename = row.get("filename", "Unknown file")
        question = row.get("question", "")
        risk = row.get("risk_level", "unknown")

        with st.expander(f"{timestamp} — {filename} — Risk: {risk.upper()}"):
            st.write("**Question:**", question)
            st.write("**Risk Level:**", risk)

            if st.button("Delete Entry", key=f"delete_{idx}"):
                history_df = history_df.drop(idx)
                history_df.to_excel("analysis_history.xlsx", index=False)
                st.success("Entry deleted.")
                st.rerun()