from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ============================================================
# DATABASE LOCATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "clauseai_backend.sqlite3"

SESSION_TTL_HOURS = 72


# ============================================================
# DB CONNECTION
# ============================================================

def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                avatar TEXT,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_verified INTEGER DEFAULT 0,
                otp_code TEXT,
                otp_expires_at TEXT,
                reset_token TEXT
            )
        """)

        # Handle existing database migrations manually if users table was already created
        cursor = con.execute("PRAGMA table_info(users)")
        columns = [info["name"] for info in cursor.fetchall()]
        if "is_verified" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
        if "otp_code" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN otp_code TEXT")
        if "otp_expires_at" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN otp_expires_at TEXT")
        if "reset_token" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")

        con.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_email) REFERENCES users(email)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                contract_name TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_email) REFERENCES users(email)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS guest_usage (
                device_id TEXT PRIMARY KEY,
                ip_address TEXT,
                report_count INTEGER DEFAULT 0,
                last_used TEXT NOT NULL
            )
        """)

        con.commit()


# ============================================================
# HELPERS
# ============================================================

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _new_salt() -> bytes:
    return secrets.token_bytes(16)


def _encode_salt(salt: bytes) -> str:
    return base64.b64encode(salt).decode("ascii")


def _decode_salt(salt_b64: str) -> bytes:
    return base64.b64decode(salt_b64.encode("ascii"))


def _pbkdf2_hash(password: str, *, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120_000
    )
    return base64.b64encode(dk).decode("ascii")


def _verify_password(password: str, *, salt_b64: str, expected_hash: str) -> bool:
    salt = _decode_salt(salt_b64)
    got = _pbkdf2_hash(password, salt=salt)
    return hmac.compare_digest(expected_hash, got)


# ============================================================
# USER MANAGEMENT
# ============================================================

from email_utils import send_otp_email

def generate_otp() -> str:
    import random
    return f"{random.randint(100000, 999999)}"

def create_user(*, email: str, password: str, name: str, role: str = "User") -> Tuple[bool, str, Optional[str]]:
    init_db()
    email_n = _norm_email(email)

    if not email_n or "@" not in email_n:
        return False, "Invalid email", None

    if len(password or "") < 4:
        return False, "Password too short", None

    salt = _new_salt()
    otp = generate_otp()
    otp_expires = _utc_now() + timedelta(minutes=5)

    with _connect() as con:
        exists = con.execute(
            "SELECT 1 FROM users WHERE email = ?",
            (email_n,)
        ).fetchone()

        if exists:
            return False, "User already exists", None

        avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={name}"

        con.execute("""
            INSERT INTO users(
                email, name, role, avatar,
                password_salt, password_hash, created_at,
                is_verified, otp_code, otp_expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email_n,
            name,
            role,
            avatar,
            _encode_salt(salt),
            _pbkdf2_hash(password, salt=salt),
            _utc_now_iso(),
            1, # AUTO VERIFIED
            otp,
            otp_expires.isoformat()
        ))

        con.commit()

    return True, "Account created successfully! You can now log in.", otp


def login(*, email: str, password: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    init_db()
    email_n = _norm_email(email)

    with _connect() as con:
        row = con.execute(
            "SELECT * FROM users WHERE email = ?",
            (email_n,)
        ).fetchone()

        if not row:
            return None
            
        if not row["is_verified"]:
            return None # Must verify OTP first

        if not _verify_password(
            password,
            salt_b64=row["password_salt"],
            expected_hash=row["password_hash"]
        ):
            return None

        token = secrets.token_urlsafe(32)
        expires = _utc_now() + timedelta(hours=SESSION_TTL_HOURS)

        con.execute("""
            INSERT INTO sessions(token, user_email, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (
            token,
            email_n,
            _utc_now_iso(),
            expires.isoformat()
        ))

        con.commit()

        user = {
            "email": row["email"],
            "name": row["name"],
            "role": row["role"],
            "avatar": row["avatar"],
        }

        return token, user


def user_from_token(token: str) -> Optional[Dict[str, Any]]:
    init_db()

    with _connect() as con:
        row = con.execute("""
            SELECT u.*
            FROM sessions s
            JOIN users u ON u.email = s.user_email
            WHERE s.token = ?
              AND s.expires_at > ?
        """, (token, _utc_now_iso())).fetchone()

    return dict(row) if row else None


# ============================================================
# OTP MANAGEMENT
# ============================================================

def verify_otp(*, email: str, otp: str) -> Tuple[bool, str]:
    init_db()
    email_n = _norm_email(email)
    
    with _connect() as con:
        row = con.execute("SELECT otp_code, otp_expires_at, is_verified FROM users WHERE email = ?", (email_n,)).fetchone()
        if not row:
            return False, "User not found"
        if row["is_verified"]:
            return True, "User already verified"
        if row["otp_code"] != otp:
            return False, "Invalid OTP"
            
        expires_at = datetime.fromisoformat(row["otp_expires_at"])
        if _utc_now() > expires_at:
            return False, "OTP expired"
            
        con.execute("UPDATE users SET is_verified = 1, otp_code = NULL WHERE email = ?", (email_n,))
        con.commit()
    return True, "OTP verified successfully"

def resend_otp(*, email: str) -> Tuple[bool, str, Optional[str]]:
    init_db()
    email_n = _norm_email(email)
    otp = generate_otp()
    otp_expires = _utc_now() + timedelta(minutes=5)
    
    with _connect() as con:
        row = con.execute("SELECT is_verified FROM users WHERE email = ?", (email_n,)).fetchone()
        if not row:
            return False, "User not found", None
        if row["is_verified"]:
            return False, "User already verified", None
            
        con.execute("UPDATE users SET otp_code = ?, otp_expires_at = ? WHERE email = ?", (otp, otp_expires.isoformat(), email_n))
        con.commit()
        email_sent = send_otp_email(email_n, otp)
        if not email_sent:
            return False, "Failed to send OTP email. Please try again later.", None

    return True, "A new OTP has been sent.", otp


# ============================================================
# GUEST USAGE
# ============================================================

def check_and_increment_guest_usage(device_id: str, ip_address: str) -> bool:
    """Returns True if guest is allowed, False if limit reached (>=2)."""
    init_db()
    with _connect() as con:
        row = con.execute("SELECT report_count FROM guest_usage WHERE device_id = ?", (device_id,)).fetchone()
        
        if row:
            count = row["report_count"]
            if count >= 2:
                return False
            con.execute("UPDATE guest_usage SET report_count = report_count + 1, last_used = ? WHERE device_id = ?", (_utc_now_iso(), device_id))
        else:
            con.execute("INSERT INTO guest_usage (device_id, ip_address, report_count, last_used) VALUES (?, ?, 1, ?)", (device_id, ip_address, _utc_now_iso()))
        
        con.commit()
        return True


# ============================================================
# REPORTS MANAGEMENT
# ============================================================

def save_report(id: str, user_email: str, contract_id: str, contract_name: str, analysis_json: str) -> None:
    init_db()
    with _connect() as con:
        con.execute("""
            INSERT INTO reports (id, user_email, contract_id, contract_name, analysis_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id, user_email, contract_id, contract_name, analysis_json, _utc_now_iso()))
        con.commit()

def get_user_reports(user_email: str):
    init_db()
    with _connect() as con:
        rows = con.execute("SELECT * FROM reports WHERE user_email = ? ORDER BY created_at DESC", (user_email,)).fetchall()
        return [dict(r) for r in rows]

def get_report(report_id: str, user_email: str) -> Optional[Dict[str, Any]]:
    init_db()
    with _connect() as con:
        row = con.execute("SELECT * FROM reports WHERE id = ? AND user_email = ?", (report_id, user_email)).fetchone()
        return dict(row) if row else None

def delete_report(report_id: str, user_email: str) -> bool:
    init_db()
    with _connect() as con:
        con.execute("DELETE FROM reports WHERE id = ? AND user_email = ?", (report_id, user_email))
        con.commit()
        # Verify it was deleted by rows affected
        return con.total_changes > 0