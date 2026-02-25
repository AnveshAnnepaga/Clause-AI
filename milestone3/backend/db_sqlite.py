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
                created_at TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_email) REFERENCES users(email)
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

def create_user(*, email: str, password: str, name: str, role: str = "User") -> Tuple[bool, str]:
    init_db()
    email_n = _norm_email(email)

    if not email_n or "@" not in email_n:
        return False, "Invalid email"

    if len(password or "") < 4:
        return False, "Password too short"

    salt = _new_salt()

    with _connect() as con:
        exists = con.execute(
            "SELECT 1 FROM users WHERE email = ?",
            (email_n,)
        ).fetchone()

        if exists:
            return False, "User already exists"

        avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={name}"

        con.execute("""
            INSERT INTO users(
                email, name, role, avatar,
                password_salt, password_hash, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            email_n,
            name,
            role,
            avatar,
            _encode_salt(salt),
            _pbkdf2_hash(password, salt=salt),
            _utc_now_iso()
        ))

        con.commit()

    return True, "Account created"


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