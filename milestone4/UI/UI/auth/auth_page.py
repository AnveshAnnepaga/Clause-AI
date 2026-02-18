import streamlit as st
import requests
import os

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://clause-ai-53gp.onrender.com"
)


def render_auth_page():
    if st.session_state.get("auth_nav_redirect"):
        st.session_state["auth_nav_selection"] = st.session_state.pop("auth_nav_redirect")

    nav_col, content_col = st.columns([1, 2], gap="small")

    with nav_col:
        st.markdown("### 🔐 Access")
        selection = st.radio(
            "Menu",
            ["Login", "Create Account"],
            key="auth_nav_selection",
            label_visibility="collapsed"
        )

    with content_col:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)

            if selection == "Login":
                show_login()
            elif selection == "Create Account":
                show_register()

            st.markdown('</div>', unsafe_allow_html=True)


def show_login():
    st.subheader("Welcome Back")

    c_input, c_space = st.columns([3, 1])

    with c_input:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Login", type="primary"):
            try:
                r = requests.post(
                    f"{BACKEND_URL}/auth/login",
                    json={"email": email, "password": password},
                    timeout=20
                )

                if r.status_code == 200:
                    data = r.json()

                    st.session_state.authenticated = True
                    st.session_state.user = data["user"]
                    st.session_state.token = data["token"]
                    st.session_state.page = "dashboard"

                    st.rerun()
                else:
                    st.error("Invalid credentials")

            except Exception as e:
                st.error(f"Login failed: {e}")


def show_register():
    st.subheader("Create New Account")

    c1, c2 = st.columns(2)
    with c1:
        first = st.text_input("First Name")
    with c2:
        last = st.text_input("Last Name")

    email = st.text_input("Work Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up", type="primary"):
        full_name = " ".join([p for p in [first.strip(), last.strip()] if p])

        try:
            r = requests.post(
                f"{BACKEND_URL}/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "name": full_name or email,
                    "role": "User"
                },
                timeout=20
            )

            if r.status_code == 200:
                st.success("Account created successfully!")
                st.session_state["auth_nav_redirect"] = "Login"
                st.rerun()
            else:
                st.error("Registration failed")

        except Exception as e:
            st.error(f"Registration failed: {e}")
