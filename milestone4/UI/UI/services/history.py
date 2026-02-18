from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


# --------------------------------------------------
# Backend Base URL
# --------------------------------------------------

def _base_url() -> str:
    return (os.getenv("BACKEND_URL") or "https://clause-ai-53gp.onrender.com").rstrip("/")


# --------------------------------------------------
# Headers (Bearer Token)
# --------------------------------------------------

def _headers(token: str | None) -> Dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------
# Safe JSON
# --------------------------------------------------

def _safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text


# --------------------------------------------------
# LIST RUNS
# --------------------------------------------------

def list_runs(*, token: str, limit: int = 15) -> List[Dict[str, Any]]:
    try:
        r = requests.get(
            f"{_base_url()}/history",
            params={"limit": int(limit)},
            headers=_headers(token),
            timeout=30,
        )

        if r.status_code >= 400:
            return []

        data = _safe_json(r)

        if isinstance(data, dict) and data.get("ok") and isinstance(data.get("runs"), list):
            return data["runs"]

        return []

    except Exception:
        return []


# --------------------------------------------------
# GET SINGLE RUN
# --------------------------------------------------

def get_run(*, token: str, run_id: int) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(
            f"{_base_url()}/history/{int(run_id)}",
            headers=_headers(token),
            timeout=30,
        )

        if r.status_code >= 400:
            return None

        data = _safe_json(r)

        if isinstance(data, dict) and data.get("ok"):
            run = data.get("run")
            return run if isinstance(run, dict) else None

        return None

    except Exception:
        return None


# --------------------------------------------------
# DELETE RUN
# --------------------------------------------------

def delete_run(*, token: str, run_id: int) -> bool:
    try:
        r = requests.delete(
            f"{_base_url()}/history/{int(run_id)}",
            headers=_headers(token),
            timeout=30,
        )

        return r.status_code < 400

    except Exception:
        return False


# --------------------------------------------------
# SAVE RUN (optional — for dashboard save)
# --------------------------------------------------

def save_run(
    *,
    token: str,
    mode: str,
    question: str,
    tone: str,
    run_all_agents: bool,
    no_evidence_threshold: float,
    filenames: List[str],
    results: List[Dict[str, Any]],
) -> Optional[int]:
    try:
        payload = {
            "mode": mode,
            "question": question,
            "tone": tone,
            "run_all_agents": bool(run_all_agents),
            "no_evidence_threshold": float(no_evidence_threshold),
            "filenames": list(filenames or []),
            "results": list(results or []),
        }

        r = requests.post(
            f"{_base_url()}/history/save",
            json=payload,
            headers=_headers(token),
            timeout=30,
        )

        if r.status_code >= 400:
            return None

        data = _safe_json(r)

        if isinstance(data, dict) and data.get("ok") and data.get("id") is not None:
            return int(data["id"])

        return None

    except Exception:
        return None
