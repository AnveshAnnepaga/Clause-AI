import os
import streamlit as st
import requests


# -----------------------------------------
# Backend Config
# -----------------------------------------

BACKEND_URL = (
    os.getenv("BACKEND_URL")
    or "https://clause-ai-53gp.onrender.com"
).rstrip("/")


# -----------------------------------------
# API Helpers
# -----------------------------------------

def backend_register(email: str, password: str, name: str):
    try:
        r = requests.post(
            f"{BACKEND_URL}/auth/register",
            json={
                "email": email,
                "password": password,
                "name": name,
            },
            timeout=30,
        )
    except Exception as e:
        return False, f"Backend not reachable: {e}"

    if r.status_code >= 400:
        try:
            return False, r.json().get("detail", "Registration failed")
        except Exception:
            return False, "Registration failed"

    return True, "Account created successfully"


def backend_login(email: str, password: str):
    try:
        r = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={
                "email": email,
                "password": password,
            },
            timeout=30,
        )
    except Exception as e:
        return None, f"Backend not reachable: {e}"

    if r.status_code >= 400:
        return None, "Invalid email or password"

    data = r.json()
    return data, None


# -----------------------------------------
# AUTH PAGE
# -----------------------------------------

def render_auth_page():

    if st.session_state.get("auth_nav_redirect"):
        st.session_state["auth_nav_selection"] = st.session_state.pop("auth_nav_redirect")

    nav_col, content_col = st.columns([1, 2], gap="small")

    with nav_col:
        st.markdown("### 🔐 Access")
        selection = st.radio(
            "Menu",
            ["Login", "Create Account", "Forgot Password?"],
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
            elif selection == "Forgot Password?":
                show_forgot()

            st.markdown('</div>', unsafe_allow_html=True)


# -----------------------------------------
# LOGIN
# -----------------------------------------

def show_login():
    st.subheader("Welcome Back")

    c_input, c_space = st.columns([3, 1])

    with c_input:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Login", key="auth_page_login_btn", type="primary"):

            data, error = backend_login(email, password)

            if error:
                st.error(error)
                return

            # Save token + user
            st.session_state.authenticated = True
            st.session_state.token = data["token"]
            st.session_state.user = data["user"]
            st.session_state.page = "dashboard"

            st.rerun()


# -----------------------------------------
# REGISTER
# -----------------------------------------

def show_register():
    st.subheader("Create New Account")

    c1, c2 = st.columns(2)
    with c1:
        first = st.text_input("First Name", key="reg_first")
    with c2:
        last = st.text_input("Last Name", key="reg_last")

    c_input, c_space = st.columns([3, 1])

    with c_input:
        email = st.text_input("Work Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pass")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Sign Up", key="auth_page_register_btn", type="primary"):

            full_name = " ".join([p for p in [first.strip(), last.strip()] if p])

            ok, msg = backend_register(
                email=email,
                password=password,
                name=full_name or first or email
            )

            if ok:
                st.success(msg)
                st.session_state["auth_nav_redirect"] = "Login"
                st.rerun()
            else:
                st.error(msg)


# -----------------------------------------
# FORGOT PASSWORD (placeholder)
# -----------------------------------------

def show_forgot():
    st.subheader("Reset Password")

    c_input, c_space = st.columns([3, 1])

    with c_input:
        st.text_input("Enter your email")
        st.button("Send Reset Link")
