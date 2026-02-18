import streamlit as st
from services.history import delete_run, get_run, list_runs


def render_sidebar():
    with st.sidebar:

        st.markdown("### 🗂️ Workspace")

        # -----------------------
        # 1️⃣ Navigation Buttons
        # -----------------------

        if st.button("📊 New Analysis", key="sidebar_new_analysis", use_container_width=True):
            st.session_state.pop("answer_results", None)
            st.session_state.pop("report_results", None)
            st.session_state["query_box_input"] = ""
            st.session_state["uploader_key"] = int(
                st.session_state.get("uploader_key") or 0
            ) + 1
            st.session_state.page = "dashboard"
            st.rerun()

        if st.button("🕘 History", key="sidebar_history", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()

        st.divider()

        # -----------------------
        # 2️⃣ Recent History
        # -----------------------

        st.markdown("#### 🕒 Recent Analyses")

        token = (st.session_state.get("token") or "").strip()

        if not token:
            st.caption("Login to see your saved analyses.")
        else:
            try:
                runs = list_runs(token=token, limit=8)
            except Exception:
                runs = []

            if not runs:
                st.caption("No saved analyses yet.")
            else:
                for r in runs:
                    run_id = int(r.get("id"))
                    created_at = (r.get("created_at") or "").replace("T", " ")[:19]
                    mode = (r.get("mode") or "analysis").upper()
                    files = r.get("files") or []
                    label = f"📄 {created_at} — {mode} — {len(files)} file(s)"

                    c1, c2 = st.columns([4, 1])

                    # Load run
                    with c1:
                        if st.button(label, key=f"history_load_{run_id}", use_container_width=True):
                            try:
                                loaded = get_run(token=token, run_id=run_id)
                            except Exception:
                                loaded = None

                            if not loaded:
                                st.warning("Failed to load saved analysis.")
                                return

                            results = loaded.get("results") or []

                            if (loaded.get("mode") or "").lower() == "ask":
                                st.session_state["answer_results"] = results
                                st.session_state.pop("report_results", None)
                            else:
                                st.session_state["report_results"] = results
                                st.session_state.pop("answer_results", None)

                            st.session_state["query_box_input"] = loaded.get("question") or ""
                            st.session_state.page = "dashboard"
                            st.rerun()

                    # Delete run
                    with c2:
                        if st.button("🗑️", key=f"history_del_{run_id}", help="Delete this saved analysis"):
                            delete_run(token=token, run_id=run_id)
                            st.rerun()

        st.divider()

        # -----------------------
        # 3️⃣ Settings
        # -----------------------

        st.markdown("#### ⚙️ Settings")
        st.checkbox("Dark Mode Support", value=True, key="setting_dark_mode")
        st.checkbox("Auto-Escalate Risks", value=False, key="setting_auto_escalate")

        st.markdown("<br>", unsafe_allow_html=True)

        # -----------------------
        # 4️⃣ Logout
        # -----------------------

        if st.button("🚪 Logout", key="sidebar_logout_btn", use_container_width=True):
            st.session_state.clear()
            st.session_state.page = "landing"
            st.rerun()
