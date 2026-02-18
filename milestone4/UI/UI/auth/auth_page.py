from __future__ import annotations

import os
import requests
import streamlit as st


# ---------------- BACKEND CONFIG ----------------

BACKEND_URL = (
    os.getenv("BACKEND_URL")
    or "https://clause-ai-53gp.onrender.com"
).rstrip("/")


# ---------------- AUTH PAGE ----------------

def render_auth_page():

    # Handle redirect from registration
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


# ---------------- LOGIN ----------------

def show_login():
    st.subheader("Welcome Back")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary"):

        if not email or not password:
            st.error("Email and Password are required.")
            return

        try:
            r = requests.post(
                f"{BACKEND_URL}/auth/login",
                json={
                    "email": email.strip(),
                    "password": password,
                },
                timeout=60,
            )

            if r.status_code == 200:
                data = r.json()

                backend_user = data.get("user") or {}
                token = data.get("token") or data.get("access_token")

                if not token:
                    st.error("Login failed: No token received.")
                    return

                # 🔥 STORE TOKEN INSIDE USER OBJECT (CRITICAL FIX)
                st.session_state["authenticated"] = True
                st.session_state["user"] = {
                    "email": backend_user.get("email") or email.strip(),
                    "name": backend_user.get("name"),
                    "role": backend_user.get("role"),
                    "token": token,  # ← THIS FIXES HISTORY
                }

                st.session_state["page"] = "dashboard"

                st.success("Login successful!")
                st.rerun()

            else:
                try:
                    detail = r.json().get("detail", "Login failed.")
                except Exception:
                    detail = "Login failed."
                st.error(detail)

        except requests.exceptions.Timeout:
            st.error("Backend timeout. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend server.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")


# ---------------- REGISTER ----------------

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

        if not email or not password:
            st.error("Email and Password are required.")
            return

        full_name = " ".join([p for p in [first.strip(), last.strip()] if p])

        try:
            r = requests.post(
                f"{BACKEND_URL}/auth/register",
                json={
                    "email": email.strip(),
                    "password": password,
                    "name": full_name or email,
                    "role": "User"
                },
                timeout=30,
            )

            if r.status_code == 200:
                st.success("Account created successfully!")
                st.session_state["auth_nav_redirect"] = "Login"
                st.rerun()

            else:
                try:
                    detail = r.json().get("detail", "Registration failed.")
                except Exception:
                    detail = "Registration failed."
                st.error(detail)

        except requests.exceptions.Timeout:
            st.error("Backend timeout. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend server.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")


# ---------------- FORGOT PASSWORD ----------------

def show_forgot():
    st.subheader("Reset Password")

    email = st.text_input("Enter your email")

    if st.button("Send Reset Link"):
        st.info("Password reset is not implemented yet.")
