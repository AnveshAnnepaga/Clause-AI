from __future__ import annotations

import io
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from milestone3.backend.contract_pipeline import run_full_pipeline, stable_contract_id
from milestone3.backend.db_sqlite import (
    init_db,
    create_user,
    login,
    user_from_token
)

# -------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event("startup"))
# -------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()         # create users + sessions tables
     # optional demo accounts
    yield

# -------------------------------------------------------------------
# FastAPI App
# -------------------------------------------------------------------

app = FastAPI(title="Contract Analysis API", version="2.0", lifespan=lifespan)

# -------------------------------------------------------------------
# CORS (Allow Streamlit frontend)
# -------------------------------------------------------------------

_origins_env = os.getenv("FRONTEND_ORIGINS", "").strip()
if _origins_env:
    allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
else:
    allowed_origins = ["*"]  # Allow Streamlit on Render

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return auth_header.strip()


def _require_user(authorization: str | None) -> dict:
    token = _bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization")
    user = user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "User"


class LoginRequest(BaseModel):
    email: str
    password: str


class AnalyzeTextRequest(BaseModel):
    contract_text: str
    question: str
    tone: str = "executive"
    no_evidence_threshold: float = 0.25
    contract_id: Optional[str] = None
    intent_override: Optional[str] = None
    run_all_agents: bool = False

# -------------------------------------------------------------------
# Health Check
# -------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "ts": _utc_now_iso()}

# -------------------------------------------------------------------
# Auth APIs
# -------------------------------------------------------------------

@app.post("/auth/register")
def register(req: RegisterRequest):
    ok, msg = create_user(email=req.email, password=req.password, name=req.name, role=req.role)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.post("/auth/login")
def auth_login(req: LoginRequest):
    res = login(email=req.email, password=req.password)
    if not res:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token, user = res
    return {"ok": True, "token": token, "user": user}


@app.get("/auth/me")
def auth_me(authorization: str | None = Header(default=None)):
    user = _require_user(authorization)
    return {"ok": True, "user": user}

# -------------------------------------------------------------------
# File Reader
# -------------------------------------------------------------------

async def _read_upload_text(upload: UploadFile) -> str:
    data = await upload.read()
    if not data:
        return ""

    name = (upload.filename or "").lower()

    if name.endswith(".pdf"):
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(p.extract_text() or "" for p in reader.pages)

    if name.endswith(".docx"):
        import docx
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text)

    return data.decode("utf-8", errors="ignore")

# -------------------------------------------------------------------
# Analysis APIs
# -------------------------------------------------------------------

@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
    question: str = Form(...),
    tone: str = Form("executive"),
    no_evidence_threshold: float = Form(0.25),
    contract_id: Optional[str] = Form(None),
    intent_override: Optional[str] = Form(None),
    run_all_agents: bool = Form(False),
):
    contract_text = await _read_upload_text(file)
    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="Empty document")

    cid = contract_id or stable_contract_id(contract_text)

    final_json, report = await run_full_pipeline(
        contract_text=contract_text,
        question=question,
        tone=tone,
        contract_id=cid,
        no_evidence_threshold=no_evidence_threshold,
        intent_override=intent_override,
        run_all_agents=run_all_agents,
    )

    return {"contract_id": cid, "analysis": final_json, "report": report}


@app.post("/analyze_text")
async def analyze_contract_text(payload: AnalyzeTextRequest):
    cid = payload.contract_id or stable_contract_id(payload.contract_text)

    final_json, report = await run_full_pipeline(
        contract_text=payload.contract_text,
        question=payload.question,
        tone=payload.tone,
        contract_id=cid,
        no_evidence_threshold=payload.no_evidence_threshold,
        intent_override=payload.intent_override,
        run_all_agents=payload.run_all_agents,
    )

    return {"contract_id": cid, "analysis": final_json, "report": report}