from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from milestone3.backend.db_postgres import get_conn  # Supabase connection

# ============================================================
# HELPERS
# ============================================================

SESSION_TTL_HOURS = 72

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

def _pbkdf2_hash(password: str, *, salt: bytes, iterations: int = 120_000) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return base64.b64encode(dk).decode("ascii")

def _verify_password(password: str, *, salt_b64: str, expected_hash: str) -> bool:
    salt = _decode_salt(salt_b64)
    got = _pbkdf2_hash(password, salt=salt)
    return hmac.compare_digest(expected_hash, got)

# ============================================================
# USER MANAGEMENT
# ============================================================

def create_user(*, email: str, password: str, name: str, role: str = "User") -> Tuple[bool, str]:
    email_n = _norm_email(email)
    salt = _new_salt()
    from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from milestone3.backend.db_postgres import get_conn  # Supabase connection

# ============================================================
# HELPERS
# ============================================================

SESSION_TTL_HOURS = 72

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

def _pbkdf2_hash(password: str, *, salt: bytes, iterations: int = 120_000) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return base64.b64encode(dk).decode("ascii")

def _verify_password(password: str, *, salt_b64: str, expected_hash: str) -> bool:
    salt = _decode_salt(salt_b64)
    got = _pbkdf2_hash(password, salt=salt)
    return hmac.compare_digest(expected_hash, got)

# ============================================================
# USER MANAGEMENT
# ============================================================

def create_user(*, email: str, password: str, name: str, role: str = "User") -> Tuple[bool, str]:
    email_n = _norm_email(email)
    salt = _new_salt()

    with get_conn() as con:
        with con.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE email = %s", (email_n,))
            if cur.fetchone():
                return False, "User already exists"

            avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={name}"

            cur.execute("""
                INSERT INTO users(email, name, role, avatar, password_salt, password_hash, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                email_n,
                name,
                role,
                avatar,
                _encode_salt(salt),
                _pbkdf2_hash(password, salt=salt),
                _utc_now(),
            ))
            con.commit()

    return True, "Account created"

def login(*, email: str, password: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    email_n = _norm_email(email)
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email_n,))
        row = cur.fetchone()
        if not row:
            return None

        if not _verify_password(password, salt_b64=row["password_salt"], expected_hash=row["password_hash"]):
            return None

        token = secrets.token_urlsafe(32)
        expires = _utc_now() + timedelta(hours=SESSION_TTL_HOURS)

        cur.execute("""
            INSERT INTO sessions(token, user_email, created_at, expires_at)
            VALUES (%s, %s, %s, %s)
            """, (token, email_n, _utc_now(), expires))
        con.commit()

        user = {
                "email": row["email"],
                "name": row["name"],
                "role": row["role"],
                "avatar": row["avatar"],
            }

        return token, user

# ============================================================
# ANALYSIS HISTORY
# ============================================================

def save_analysis_run(
    *,
    user_email: str,
    mode: str,
    question: str,
    tone: str,
    run_all_agents: bool,
    no_evidence_threshold: float,
    filenames: List[str],
    results: List[Dict[str, Any]],
) -> int:
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("""
                INSERT INTO analysis_runs(
                    user_email, created_at, mode, question, tone,
                    run_all_agents, no_evidence_threshold, files_json, results_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_email,
                _utc_now(),
                mode,
                question,
                tone,
                run_all_agents,
                no_evidence_threshold,
                json.dumps(filenames),
                json.dumps(results),
            ))

        run_id = cur.fetchone()["id"]
        con.commit()
        return run_id

def list_analysis_runs(*, user_email: str, limit: int = 10) -> List[Dict[str, Any]]:
    with get_conn() as con:
        with con.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM analysis_runs
                WHERE user_email = %s
                ORDER BY id DESC
                LIMIT %s
            """, (user_email, limit))

            return cur.fetchall()

            cur.execute("SELECT 1 FROM users WHERE email = %s", (email_n,))
            if cur.fetchone():
                return False, "User already exists"

            avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={name}"

            cur.execute("""
                INSERT INTO users(email, name, role, avatar, password_salt, password_hash, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                email_n,
                name,
                role,
                avatar,
                _encode_salt(salt),
                _pbkdf2_hash(password, salt=salt),
                _utc_now(),
            ))
            con.commit()

    return True, "Account created"

def login(*, email: str, password: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    email_n = _norm_email(email)
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email_n,))
        row = cur.fetchone()
        if not row:
            return None

        if not _verify_password(password, salt_b64=row["password_salt"], expected_hash=row["password_hash"]):
            return None

        token = secrets.token_urlsafe(32)
        expires = _utc_now() + timedelta(hours=SESSION_TTL_HOURS)

        cur.execute("""
            INSERT INTO sessions(token, user_email, created_at, expires_at)
            VALUES (%s, %s, %s, %s)
            """, (token, email_n, _utc_now(), expires))
        con.commit()

        user = {
                "email": row["email"],
                "name": row["name"],
                "role": row["role"],
                "avatar": row["avatar"],
            }

        return token, user

# ============================================================
# ANALYSIS HISTORY
# ============================================================

def save_analysis_run(
    *,
    user_email: str,
    mode: str,
    question: str,
    tone: str,
    run_all_agents: bool,
    no_evidence_threshold: float,
    filenames: List[str],
    results: List[Dict[str, Any]],
) -> int:
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("""
                INSERT INTO analysis_runs(
                    user_email, created_at, mode, question, tone,
                    run_all_agents, no_evidence_threshold, files_json, results_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_email,
                _utc_now(),
                mode,
                question,
                tone,
                run_all_agents,
                no_evidence_threshold,
                json.dumps(filenames),
                json.dumps(results),
            ))

        run_id = cur.fetchone()["id"]
        con.commit()
        return run_id

def list_analysis_runs(*, user_email: str, limit: int = 10) -> List[Dict[str, Any]]:
    with get_conn() as con:
        cur = con.cursor()

        cur.execute("""
                SELECT *
                FROM analysis_runs
                WHERE user_email = %s
                ORDER BY id DESC
                LIMIT %s
            """, (user_email, limit))

        return cur.fetchall()
