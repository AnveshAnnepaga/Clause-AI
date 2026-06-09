from __future__ import annotations

import os
import requests
import streamlit as st
import time

# ---------------- BACKEND CONFIG ----------------

BACKEND_URL = (
    os.getenv("BACKEND_URL")
    or "http://localhost:8000"
).rstrip("/")


# ---------------- AUTH PAGE ----------------

def render_auth_page():

    nav_col, content_col = st.columns([1, 2], gap="small")

    with nav_col:
        st.markdown("### 🔐 Access")
        
        # Hide standard nav if OTP is pending
        if st.session_state.get("otp_pending_email"):
            selection = "Verify OTP"
            st.info(f"Verification pending for {st.session_state['otp_pending_email']}")
        else:
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
            elif selection == "Verify OTP":
                show_otp_verification()
            elif selection == "Forgot Password?":
                show_forgot()

            st.markdown('</div>', unsafe_allow_html=True)


# ---------------- LOGIN ----------------

def show_login():
    st.subheader("Welcome Back")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary", use_container_width=True):
        if not email or not password:
            st.error("Email and Password are required.")
            return

        try:
            r = requests.post(
                f"{BACKEND_URL}/auth/login",
                json={"email": email.strip(), "password": password},
                timeout=60,
            )

            if r.status_code == 200:
                data = r.json()
                backend_user = data.get("user") or {}
                token = data.get("token") or data.get("access_token")

                if not token:
                    st.error("Login failed: No token received.")
                    return

                st.session_state["authenticated"] = True
                st.session_state["user"] = {
                    "email": backend_user.get("email") or email.strip(),
                    "name": backend_user.get("name"),
                    "role": backend_user.get("role"),
                    "token": token,
                }
                st.session_state["page"] = "dashboard"
                st.rerun()
            else:
                try:
                    detail = r.json().get("detail", "Login failed.")
                except Exception:
                    detail = "Login failed."
                
                if "unverified" in detail.lower():
                    st.session_state["otp_pending_email"] = email.strip()
                    st.warning("Your account is unverified. Please verify your OTP.")
                    st.rerun()
                else:
                    st.error(detail)

        except requests.exceptions.Timeout:
            st.error("Backend timeout. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend server.")


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

    if st.button("Sign Up", type="primary", use_container_width=True):
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
                st.toast("Account created! Check your email for the OTP.", icon="📧")
                st.session_state["otp_pending_email"] = email.strip()
                st.session_state["otp_expiry_timestamp"] = time.time() + 600 # 10 minutes
                st.rerun()
            else:
                st.error(r.json().get("detail", "Registration failed."))

        except Exception as e:
            st.error(f"Error: {e}")


# ---------------- OTP VERIFICATION ----------------

def show_otp_verification():
    email = st.session_state.get("otp_pending_email")
    st.subheader("Verify Your Email")
    st.write(f"We've sent a 6-digit code to **{email}**")


    # JS Countdown Timer injection
    expiry = st.session_state.get("otp_expiry_timestamp", time.time() + 600)
    remaining = max(0, int(expiry - time.time()))
    
    st.markdown(
        f"""
        <div style="text-align: center; margin: 1rem 0; color: #9ca3af;">
            Code expires in: <strong id="timer">{remaining // 60}:{remaining % 60:02d}</strong>
        </div>
        <script>
            var timeLeft = {remaining};
            var elem = window.parent.document.getElementById('timer');
            var timerId = setInterval(countdown, 1000);
            function countdown() {{
                if (timeLeft == -1) {{
                    clearTimeout(timerId);
                }} else {{
                    if(elem) elem.innerHTML = Math.floor(timeLeft/60) + ':' + ('0' + timeLeft%60).slice(-2);
                    timeLeft--;
                }}
            }}
        </script>
        """,
        unsafe_allow_html=True
    )

    otp_code = st.text_input("Enter 6-digit OTP", max_chars=6)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Verify Code", type="primary", use_container_width=True):
            if not otp_code:
                st.error("Please enter the code")
                return
            
            r = requests.post(
                f"{BACKEND_URL}/auth/verify-otp",
                json={"email": email, "otp": otp_code},
                timeout=30
            )
            if r.status_code == 200:
                st.success("Verified successfully! You can now log in.")
                del st.session_state["otp_pending_email"]
                st.session_state["auth_nav_selection"] = "Login"
                st.rerun()
            else:
                st.error(r.json().get("detail", "Invalid OTP"))

    with c2:
        if st.button("Resend OTP", use_container_width=True):
            r = requests.post(f"{BACKEND_URL}/auth/resend-otp", json={"email": email}, timeout=30)
            if r.status_code == 200:
                st.toast("New OTP sent to your email!", icon="🔄")
                st.session_state["otp_expiry_timestamp"] = time.time() + 600
                st.rerun()
            else:
                st.error(r.json().get("detail", "Failed to resend"))
                
    st.markdown("---")
    if st.button("← Back to Login", use_container_width=True):
        del st.session_state["otp_pending_email"]
        st.session_state["auth_nav_selection"] = "Login"
        st.rerun()


# ---------------- FORGOT PASSWORD ----------------

def show_forgot():
    st.subheader("Reset Password")
    email = st.text_input("Enter your email")
    if st.button("Send Reset Link", use_container_width=True):
        st.info("Password reset is a premium feature currently under construction.")
