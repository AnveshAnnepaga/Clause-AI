from __future__ import annotations

import io
import os
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, List, Any
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from contract_pipeline import run_full_pipeline, stable_contract_id
from db_sqlite import (
    init_db,
    create_user,
    login,
    user_from_token,
    verify_otp,
    resend_otp,
    check_and_increment_guest_usage,
    save_report,
    get_user_reports,
    get_report,
    delete_report
)


# -------------------------------------------------------------------
# Lifespan (startup init)
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # ensure all tables exist
    yield


app = FastAPI(title="ClauseAI API", version="3.0", lifespan=lifespan)


# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------
origins_env = os.getenv("FRONTEND_ORIGINS", "").strip()
allowed_origins = (
    [o.strip() for o in origins_env.split(",") if o.strip()] if origins_env else ["*"]
)

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


def _get_user_or_none(authorization: str | None) -> dict | None:
    token = _bearer_token(authorization)
    if not token:
        return None
    return user_from_token(token)


def _require_user(authorization: str | None) -> dict:
    user = _get_user_or_none(authorization)
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

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class ResendOTPRequest(BaseModel):
    email: str

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
# Health
# -------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "ts": _utc_now_iso()}


# -------------------------------------------------------------------
# Auth APIs
# -------------------------------------------------------------------
@app.post("/auth/register")
def register(req: RegisterRequest):
    ok, msg, otp = create_user(
        email=req.email, password=req.password, name=req.name, role=req.role
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

@app.post("/auth/verify-otp")
def verify_otp_endpoint(req: VerifyOTPRequest):
    ok, msg = verify_otp(email=req.email, otp=req.otp)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

@app.post("/auth/resend-otp")
def resend_otp_endpoint(req: ResendOTPRequest):
    ok, msg, otp = resend_otp(email=req.email)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

@app.post("/auth/login")
def auth_login(req: LoginRequest):
    res = login(email=req.email, password=req.password)
    if not res:
        raise HTTPException(status_code=401, detail="Invalid email, password, or unverified OTP")
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


@app.post("/parse_file")
async def parse_uploaded_file(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None)
):
    # Endpoint to extract and return raw text for frontend display/verification
    _ = _require_user(authorization) if authorization else None
    text = await _read_upload_text(file)
    return {"ok": True, "text": text, "filename": file.filename}

# -------------------------------------------------------------------
# Analysis APIs (With Guest & Save Logic)
# -------------------------------------------------------------------
async def _handle_analysis(
    request: Request,
    authorization: str | None,
    device_id: str | None,
    contract_text: str,
    question: str,
    tone: str,
    no_evidence_threshold: float,
    contract_id: Optional[str],
    intent_override: Optional[str],
    run_all_agents: bool,
    filename: str = "Pasted Text"
):
    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="Empty document")

    # Check Authorization / Guest Usage
    user = _get_user_or_none(authorization)
    
    if not user:
        if not device_id:
            raise HTTPException(status_code=400, detail="Missing X-Device-Id header for guest usage.")
        
        client_ip = request.client.host if request.client else "unknown"
        allowed = check_and_increment_guest_usage(device_id, client_ip)
        if not allowed:
            raise HTTPException(status_code=403, detail="GUEST_LIMIT_REACHED")
            
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

    if isinstance(final_json, dict):
        final_json["contract_id"] = cid
        final_json["report"] = report
        out_json = final_json
    else:
        out_json = {"contract_id": cid, "report": report, "data": final_json}

    # Save report if user is logged in
    if user:
        report_id = str(uuid.uuid4())
        save_report(
            id=report_id,
            user_email=user["email"],
            contract_id=cid,
            contract_name=filename,
            analysis_json=json.dumps(out_json)
        )

    return out_json


@app.post("/analyze")
async def analyze_contract(
    request: Request,
    file: UploadFile = File(...),
    question: str = Form(...),
    tone: str = Form("executive"),
    no_evidence_threshold: float = Form(0.25),
    contract_id: Optional[str] = Form(None),
    intent_override: Optional[str] = Form(None),
    run_all_agents: bool = Form(False),
    authorization: str | None = Header(default=None),
    x_device_id: str | None = Header(default=None)
):
    contract_text = await _read_upload_text(file)
    return await _handle_analysis(
        request=request,
        authorization=authorization,
        device_id=x_device_id,
        contract_text=contract_text,
        question=question,
        tone=tone,
        no_evidence_threshold=no_evidence_threshold,
        contract_id=contract_id,
        intent_override=intent_override,
        run_all_agents=run_all_agents,
        filename=file.filename or "Uploaded Document"
    )

@app.post("/analyze_text")
async def analyze_contract_text(
    request: Request,
    payload: AnalyzeTextRequest,
    authorization: str | None = Header(default=None),
    x_device_id: str | None = Header(default=None)
):
    return await _handle_analysis(
        request=request,
        authorization=authorization,
        device_id=x_device_id,
        contract_text=payload.contract_text,
        question=payload.question,
        tone=payload.tone,
        no_evidence_threshold=payload.no_evidence_threshold,
        contract_id=payload.contract_id,
        intent_override=payload.intent_override,
        run_all_agents=payload.run_all_agents,
        filename="Pasted Text"
    )

# -------------------------------------------------------------------
# Reports History APIs
# -------------------------------------------------------------------
@app.get("/reports")
def list_reports(authorization: str | None = Header(default=None)):
    user = _require_user(authorization)
    reports = get_user_reports(user["email"])
    # Do not return full analysis_json for list view to save bandwidth
    for r in reports:
        r.pop("analysis_json", None)
    return {"ok": True, "reports": reports}

@app.get("/reports/{report_id}")
def get_single_report(report_id: str, authorization: str | None = Header(default=None)):
    user = _require_user(authorization)
    report = get_report(report_id, user["email"])
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    # Parse json for the client
    report["analysis_json"] = json.loads(report["analysis_json"])
    return {"ok": True, "report": report}

@app.delete("/reports/{report_id}")
def delete_single_report(report_id: str, authorization: str | None = Header(default=None)):
    user = _require_user(authorization)
    success = delete_report(report_id, user["email"])
    if not success:
        raise HTTPException(status_code=404, detail="Report not found or could not delete")
    return {"ok": True}

# -------------------------------------------------------------------
# Analytics
# -------------------------------------------------------------------
@app.get("/analytics")
def get_analytics(authorization: str | None = Header(default=None)):
    user = _require_user(authorization)
    reports = get_user_reports(user["email"])
    
    total_reports = len(reports)
    # Could do deeper analysis, but for now we mock some metrics based on reports
    high_risks = 0
    # In a real scenario we'd parse the JSONs or store risk counts in the DB
    return {
        "ok": True,
        "analytics": {
            "total_reports": total_reports,
            "high_risks_detected": high_risks,
            "last_active": reports[0]["created_at"] if reports else None
        }
    }

# -------------------------------------------------------------------
# Serve React Frontend (Production / Hugging Face Spaces)
# -------------------------------------------------------------------
frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "client", "dist")

if os.path.isdir(frontend_build_path):
    # Mount Vite's static assets folder
    assets_path = os.path.join(frontend_build_path, "assets")
    if os.path.isdir(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # Serve index.html for all unrecognized routes to allow client-side routing
        html_path = os.path.join(frontend_build_path, "index.html")
        if os.path.exists(html_path):
            return FileResponse(html_path)
        raise HTTPException(status_code=404, detail="Frontend build not found")