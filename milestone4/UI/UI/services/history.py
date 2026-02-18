import streamlit as st
import requests
import os

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://clause-ai-53gp.onrender.com"
)


def history_page():
    st.title("History")

    if not st.session_state.get("authenticated"):
        st.warning("Please login to view your history.")
        return

    token = st.session_state.get("token")

    if not token:
        st.error("Session expired. Please login again.")
        return

    try:
        r = requests.get(
            f"{BACKEND_URL}/history",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20
        )

        if r.status_code != 200:
            st.error("Failed to load history.")
            return

        data = r.json()

        if not data.get("ok"):
            st.error("Invalid response from backend.")
            return

        runs = data.get("runs", [])

        if not runs:
            st.info("No saved analyses found.")
            return

        for run in runs:
            with st.expander(f"Run #{run['id']} — {run['question']}"):
                st.write("Tone:", run["tone"])
                st.write("Mode:", run["mode"])
                st.write("Created At:", run["created_at"])

    except Exception as e:
        st.error(f"Error loading history: {e}")
